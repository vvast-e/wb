from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from backend.models.task import ScheduledTask
from datetime import datetime, timezone
from dateutil import tz


async def create_scheduled_task(
    db: AsyncSession,
    nm_id: int,
    action: str,
    payload: dict,
    scheduled_at: datetime,
    user_id: int
)-> ScheduledTask:
    task = ScheduledTask(
        nm_id=nm_id,
        action=action,
        payload=payload,
        scheduled_at=scheduled_at,
        user_id=user_id,
        status="pending"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


from datetime import datetime
from dateutil import tz


async def get_pending_tasks(db: AsyncSession)->List[ScheduledTask]:
    # Получаем текущее время в Москве
    msk_tz = tz.gettz('Europe/Moscow')
    now_msk = datetime.now(msk_tz)

    result = await db.execute(
        select(ScheduledTask).where(
            ScheduledTask.scheduled_at <= now_msk.replace(tzinfo=None),
            ScheduledTask.status == 'pending'
        )
    )
    return result.scalars().all()


async def get_tasks_with_pending(db: AsyncSession)->List[ScheduledTask]:

    result = await db.execute(
        select(ScheduledTask).where(
            ScheduledTask.status == 'pending'
        )
    )
    return result.scalars().all()

async def get_task_by_id(db: AsyncSession, task_id: int)->ScheduledTask:
    result = await db.execute(
        select(ScheduledTask).where(ScheduledTask.id == task_id).options(joinedload(ScheduledTask.owner)))
    return result.scalars().first()

async def delete_task(db: AsyncSession, task_id: int):
    task = await get_task_by_id(db, task_id)
    await db.delete(task)
    await db.commit()