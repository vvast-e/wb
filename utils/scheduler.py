from datetime import datetime, timedelta
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.executors.pool import ThreadPoolExecutor

from crud import task as task_crud
from crud.history import update_history_status
from utils.wb_api import WBAPIClient, WBApiResponse
from dependencies import get_db, get_wb_api_key
from crud.user import get_all_users
from crud.analytics import parse_shop_feedbacks_crud

scheduler = AsyncIOScheduler(executors={'default': ThreadPoolExecutor(1)})


async def _get_wb_api_key_for_task(db: AsyncSession, task_id: int) -> str:
    task = await task_crud.get_task_by_id(db, task_id)
    if not task or not task.owner:
        raise ValueError("Task or user not found")

    if not task.brand:
        raise ValueError("Brand not specified in task")

    wb_api_key = await get_wb_api_key(task.brand, task.owner, db)  # передаем brand!
    return wb_api_key


async def process_scheduled_tasks():
    async for db in get_db():
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


async def parse_all_shops_feedbacks():
    print(f"[SCHEDULER] >>> Запуск парсера отзывов: {datetime.now().isoformat()}")
    async for db in get_db():
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
    print(f"[SCHEDULER] <<< Завершение парсера отзывов: {datetime.now().isoformat()}")


def start_scheduler():
    scheduler.add_job(
        process_scheduled_tasks,
        'interval',
        seconds=5,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    scheduler.add_job(
        parse_all_shops_feedbacks,
        'interval',
        minutes=30,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    scheduler.start()