from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from crud import task as task_crud
from utils.wb_api import WBAPIClient
from dependencies import get_db, get_wb_api_key

scheduler = AsyncIOScheduler()


async def _get_wb_api_key_for_task(db: AsyncSession, task_id: int) -> str:
    task = await task_crud.get_task_by_id(db, task_id)
    if not task or not task.owner:
        raise ValueError("Task or user not found")
    wb_api_key = await get_wb_api_key(task.owner, db)
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
                elif task.action == 'update_media':
                    result = await wb_client.upload_media(task.nm_id, task.payload.get("media"))
                elif task.action == 'upload_media_file':
                    file_data = task.payload["file_data"].encode('latin1')
                    result = await wb_client.upload_mediaFile(
                        nm_id=task.nm_id,
                        file_data=file_data,
                        photo_number=task.payload["photo_number"],
                        media_type=task.payload.get("media_type", "image")
                    )

                if result.success:
                    task.status = 'completed'
                else:
                    # Если запрос не удался, переносим задачу на 5 минут вперед
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


def start_scheduler():
    scheduler.add_job(
        process_scheduled_tasks,
        'interval',
        seconds=5,
        max_instances=1,
        timezone='Europe/Moscow'
    )
    scheduler.start()