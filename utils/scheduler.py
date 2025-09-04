from datetime import datetime, timedelta
import os
import logging
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.executors.asyncio import AsyncIOExecutor

# Отключаем логи APScheduler
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)
logging.getLogger('apscheduler.schedulers').setLevel(logging.WARNING)

from crud import task as task_crud
from crud.history import update_history_status
from utils.wb_api import WBAPIClient, WBApiResponse
from crud.user import get_all_users, get_decrypted_wb_key
from crud.analytics import parse_shop_feedbacks_crud
from utils.aspect_processor import AspectProcessor
from database import AsyncSessionLocal

scheduler = AsyncIOScheduler(executors={'default': AsyncIOExecutor()})
logger = logging.getLogger(__name__)


async def get_db_session() -> AsyncSession:
    """Получение сессии базы данных для планировщика (вручную закрывается вызывающим кодом)."""
    return AsyncSessionLocal()


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
    # Одна сессия на тик планировщика; изменения выполняем по одной задаче за транзакцию
    async with AsyncSessionLocal() as db:
        tasks = await task_crud.get_pending_tasks(db)
        for task in tasks:
            try:
                wb_api_key = await _get_wb_api_key_for_task(db, task.id)

                async with db.begin():
                    task.status = 'processing'

                wb_client = WBAPIClient(api_key=wb_api_key)

                # Выполняем действие вне транзакции, т.к. это внешние вызовы
                if task.action == 'update_content':
                    result = await wb_client.update_card_content(task.nm_id, task.payload)
                elif task.action == 'update_media':
                    result = await wb_client.upload_meda(task.nm_id, task.payload.get("media"))
                elif task.action == 'upload_media_file':
                    if task.payload.get("immediate"):
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
                                except Exception:
                                    pass
                                async with db.begin():
                                    await db.delete(task)

                # Фиксируем результат статуса и истории в отдельной транзакции
                async with db.begin():
                    if result.success:
                        task.status = 'completed'
                        await update_history_status(db, status='completed', user_id=task.user_id, created_at=task.created_at)
                    else:
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
                async with db.begin():
                    task.status = 'pending'
                    task.scheduled_at = datetime.now() + timedelta(minutes=5)
                    task.error = str(e)


async def parse_all_shops_feedbacks():
    async with AsyncSessionLocal() as db:
        users = await get_all_users(db)
        for user in users:
            if not user.wb_api_key:
                continue
            for brand in (user.wb_api_key or {}).keys():
                max_attempts = 3
                attempt = 0
                backoff_base_sec = 5
                while attempt < max_attempts:
                    try:
                        await parse_shop_feedbacks_crud(db, user.id, brand, save_to_db=True)
                        break
                    except Exception as e:
                        attempt += 1
                        logger.error(f"[SCHEDULER] Ошибка парсинга бренда '{brand}' для user_id={user.id}: {e}. Попытка {attempt}/{max_attempts}")
                        if attempt < max_attempts:
                            await asyncio.sleep(backoff_base_sec * attempt)
                        else:
                            logger.error(f"[SCHEDULER] Бренд '{brand}' пропущен после {max_attempts} неудачных попыток")


async def analyze_all_new_feedbacks():
    """Автоматический анализ всех новых отзывов без аспектов"""
    try:
        async with AsyncSessionLocal() as db:
            # Создаем процессор аспектов
            aspect_processor = AspectProcessor(db)
            
            # Обрабатываем все существующие отзывы без аспектов (большими батчами)
            result = await aspect_processor.process_existing_feedbacks(limit=2000)  # Увеличиваем лимит
            
            processed = result.get('processed', 0)
            skipped = result.get('skipped_already_analyzed', 0)
            
            if processed > 0 or skipped > 0:
                print(f"[AI] Анализ аспектов: обработано {processed}, пропущено {skipped}")
    except Exception as e:
        print(f"[AI] Ошибка при анализе аспектов: {e}")


def start_scheduler():
    # Отключаем все логи APScheduler
    logging.getLogger('apscheduler').setLevel(logging.ERROR)
    logging.getLogger('apscheduler.executors.default').setLevel(logging.ERROR)
    logging.getLogger('apscheduler.schedulers').setLevel(logging.ERROR)
    logging.getLogger('apscheduler.triggers').setLevel(logging.ERROR)
    
    # Задача обработки запланированных задач (каждые 5 секунд)
    scheduler.add_job(
        process_scheduled_tasks,
        'interval',
        seconds=5,
        max_instances=1,
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
    
    # Задача анализа аспектов (каждые 15 минут)
    scheduler.add_job(
        analyze_all_new_feedbacks,
        'interval',
        minutes=15,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    
    scheduler.start()