from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.crud.task import get_pending_tasks, delete_task, get_tasks_with_pending
from backend.models import User, ScheduledTask
from backend.schemas import Task
from backend.dependencies import get_db, get_current_user_with_wb_key
from backend.crud.user import get_user_by_email, get_decrypted_wb_key

router = APIRouter(tags=["Task"], prefix="/tasks")


@router.get("/", response_model=List[Task])
async def get_tasks(db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(get_current_user_with_wb_key)
                    ) -> List[Task]:
    tasks = []
    async for db in get_db():
        tasks = await get_tasks_with_pending(db)
    return [Task.from_orm(task) for task in tasks]


@router.delete("/delete/{task_id}", status_code=204)
async def delete_curr_task(task_id: int, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(get_current_user_with_wb_key)):
    task = await get_pending_tasks(db)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await delete_task(db, task_id)
    return
