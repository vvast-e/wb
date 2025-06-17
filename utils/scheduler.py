from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crud import task as task_crud
from utils.wb_api import WBAPIClient
from dependencies import get_db, get_wb_api_key
from models.user import User

scheduler = AsyncIOScheduler()


async def _get_wb_api_key_for_task(db: AsyncSession, task_id: int) -> str:
    task = await task_crud.get_task_by_id(db, task_id)
    if not task or not task.owner:
        raise ValueError("Task or user not found")
    wb_api_key = await get_wb_api_key(db, task.owner)
    return wb_api_key


async def process_scheduled_tasks():
    async for db in get_db():
        tasks = await task_crud.get_pending_tasks(db)
        for task in tasks:
            try:
                # Получаем API ключ из связанного пользователя
                wb_api_key = await _get_wb_api_key_for_task(db, task.id)

                task.status = 'processing'
                await db.commit()
                wb_client = WBAPIClient(api_key=wb_api_key)

                if task.action == 'update_content':
                    result = await wb_client.update_card_content(task.nm_id, task.payload)
                elif task.action == 'update_media':
                    result = await wb_client.upload_media(task.nm_id, task.payload.get("media"))

                task.status = 'completed' if result.success else 'error'
                task.wb_response = result.wb_response

            except Exception as e:
                task.status = 'error'
                task.error = str(e)
                # Логируем ошибку для отладки

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