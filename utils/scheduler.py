from datetime import datetime, timedelta
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.executors.asyncio import AsyncIOExecutor

from crud import task as task_crud
from crud.history import update_history_status
from utils.wb_api import WBAPIClient, WBApiResponse
from crud.user import get_all_users, get_decrypted_wb_key
from crud.analytics import parse_shop_feedbacks_crud
from utils.aspect_processor import AspectProcessor
from database import AsyncSessionLocal

scheduler = AsyncIOScheduler(executors={'default': AsyncIOExecutor()})


async def get_db_session() -> AsyncSession:
    """Получение сессии базы данных для планировщика"""
    async with AsyncSessionLocal() as session:
        return session


async def _get_wb_api_key_for_task(db: AsyncSession, task_id: int) -> str:
    task = await task_crud.get_task_by_id(db, task_id)
    if not task or not task.owner:
        raise ValueError("Task or user not found")

    if not task.brand:
        raise ValueError("Brand not specified in task")

    # Используем get_decrypted_wb_key напрямую вместо get_wb_api_key с Depends
    wb_api_key = await get_decrypted_wb_key(db, task.owner, task.brand)
    return wb_api_key


async def process_scheduled_tasks():
    db = await get_db_session()
    try:
        tasks = await task_crud.get_pending_tasks(db)
        for task in tasks:
            try:
                wb_api_key = await _get_wb_api_key_for_task(db, task.id)

                task.status = 'processing'
                await db.commit()
                wb_client = WBAPIClient(api_key=wb_api_key)

                if task.action == 'update_content':
                    result = await wb_client.update_card_content(task.nm_id, task.payload)
                    print()
                    print(result)
                elif task.action == 'update_media':
                    result = await wb_client.upload_meda(task.nm_id, task.payload.get("media"))
                    print()
                    print(result)
                elif task.action == 'upload_media_file':
                    if task.payload.get("immediate"):
                        # Ничего не делаем, задача уже была выполнена сразу
                        result = WBApiResponse(success=True, data={"info": "already uploaded"})
                    else:
                        file_path = task.payload.get("file_path")
                        if not file_path or not os.path.exists(file_path):
                            result = WBApiResponse(success=False, error="Файл для загрузки не найден")
                        else:
                            with open(file_path, "rb") as f:
                                file_data = f.read()
                            result = await wb_client.upload_mediaFile(
                                nm_id=task.nm_id,
                                file_data=file_data,
                                photo_number=task.payload["photo_number"],
                                media_type=task.payload.get("media_type", "image")
                            )
                            if result.success:
                                try:
                                    os.remove(file_path)
                                except Exception as e:
                                    print(f"[Scheduler] Не удалось удалить временный файл: {e}")
                                # Удаляем задачу из базы после успешной отправки и удаления файла
                                await db.delete(task)
                                await db.commit()
                print(result.success)
                if result.success:
                    task.status = 'completed'
                    await update_history_status(db, status='completed', user_id=task.user_id, created_at=task.created_at)
                else:
                    print(f"❌ Ошибка при откате изменений: {result.error}")
                    print(f"🧾 Ответ WB: {result.wb_response}")
                    task.status = 'pending'
                    task.scheduled_at = datetime.now() + timedelta(minutes=5)
                    if hasattr(result, 'error'):
                        task.error = result.error
                    elif isinstance(result.wb_response, dict) and 'error' in result.wb_response:
                        task.error = result.wb_response['error']
                    else:
                        task.error = "Unknown error"

                task.wb_response = result.wb_response

            except Exception as e:
                task.status = 'pending'
                task.scheduled_at = datetime.now() + timedelta(minutes=5)
                task.error = str(e)

        await db.commit()
    finally:
        await db.close()


async def parse_all_shops_feedbacks():
    print(f"[SCHEDULER] >>> Запуск парсера отзывов: {datetime.now().isoformat()}")
    db = await get_db_session()
    try:
        users = await get_all_users(db)
        print(f"[SCHEDULER] Найдено пользователей: {len(users)}")
        for user in users:
            if not user.wb_api_key:
                print(f"[SCHEDULER] Пропущен user_id={user.id} (нет wb_api_key)")
                continue
            for brand in (user.wb_api_key or {}).keys():
                try:
                    print(f"[SCHEDULER] Парсим отзывы для user_id={user.id}, brand={brand}, время: {datetime.now().isoformat()}")
                    await parse_shop_feedbacks_crud(db, user.id, brand, max_count_per_product=1000, save_to_db=True)
                    print(f"[SCHEDULER] Успешно: user_id={user.id}, brand={brand}")
                except Exception as e:
                    print(f"[SCHEDULER] Ошибка: user_id={user.id}, brand={brand}, error={e}")
    finally:
        await db.close()
    print(f"[SCHEDULER] <<< Завершение парсера отзывов: {datetime.now().isoformat()}")


async def analyze_all_new_feedbacks():
    """Автоматический анализ всех новых отзывов без аспектов"""
    print(f"[SCHEDULER] >>> Запуск анализатора аспектов: {datetime.now().isoformat()}")
    
    db = await get_db_session()
    try:
        # Создаем процессор аспектов
        aspect_processor = AspectProcessor(db)
        
        print(f"[SCHEDULER] 🔍 Поиск новых отзывов для анализа...")
        
        # Получаем статистику по аспектам
        stats = await aspect_processor.get_aspect_statistics()
        print(f"[SCHEDULER] 📊 Текущая статистика: {stats.get('total_aspects', 0)} аспектов в БД")
        
        # Обрабатываем все существующие отзывы без аспектов
        result = await aspect_processor.process_existing_feedbacks(limit=1000)
        
        processed = result.get('processed', 0)
        new_aspects = result.get('new_aspects', 0)
        skipped = result.get('skipped_already_analyzed', 0)
        
        print(f"[SCHEDULER] ✅ Анализ завершен:")
        print(f"[SCHEDULER]    Обработано отзывов: {processed}")
        print(f"[SCHEDULER]    Создано новых аспектов: {new_aspects}")
        print(f"[SCHEDULER]    Пропущено уже проанализированных: {skipped}")
        
        if processed > 0:
            print(f"[SCHEDULER] 🎯 Успешно проанализировано {processed} новых отзывов")
        else:
            print(f"[SCHEDULER] ℹ️  Новых отзывов для анализа не найдено")
            
    except Exception as e:
        print(f"[SCHEDULER] ❌ Ошибка при анализе аспектов: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()
    
    print(f"[SCHEDULER] <<< Завершение анализатора аспектов: {datetime.now().isoformat()}")


def start_scheduler():
    # Задача обработки запланированных задач (каждые 5 секунд)
    scheduler.add_job(
        process_scheduled_tasks,
        'interval',
        seconds=5,
        max_instances=20,
        timezone='Europe/Moscow'
    )
    
    # Задача парсинга отзывов всех магазинов (каждые 30 минут)
    scheduler.add_job(
        parse_all_shops_feedbacks,
        'interval',
        minutes=30,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    
    # Задача анализа аспектов (каждые 32 минуты - через 2 минуты после парсера)
    scheduler.add_job(
        analyze_all_new_feedbacks,
        'interval',
        minutes=32,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    
    print("[SCHEDULER] 🚀 Планировщик запущен:")
    print("[SCHEDULER]    📝 Парсер отзывов: каждые 30 минут")
    print("[SCHEDULER]    🤖 Анализатор аспектов: каждые 32 минуты (через 2 мин после парсера)")
    print("[SCHEDULER]    ⚙️  Обработка задач: каждые 5 секунд")
    
    scheduler.start()