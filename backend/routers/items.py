from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config import settings
from backend.crud.task import create_scheduled_task
from backend.models import User
from backend.utils.wb_api import WBAPIClient
from backend.crud import history as history_crud
from backend.crud import task as task_crud
from backend.schemas import WBApiResponse, Task, TaskCreate
from backend.dependencies import get_db, get_current_user_with_wb_key, get_wb_api_key
from backend.crud.user import get_user_by_email, get_decrypted_wb_key

router = APIRouter(tags=["Items"], prefix="/items")

@router.get("/", response_model=WBApiResponse)
async def get_items(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key)
):
    wb_client=WBAPIClient(api_key=wb_api_key)
    result=await wb_client.get_cards_list()
    return result

@router.get("/{nm_id}", response_model=WBApiResponse)
async def get_item(
        nm_id: int,
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key:str=Depends(get_wb_api_key),
        db: AsyncSession = Depends(get_db)
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    result = await wb_client.get_card_by_nm(nm_id)

    # Логируем действие
    # await history_crud.create_history_record(
    #     db,
    #     user_id=current_user["email"],
    #     nm_id=nm_id,
    #     action="get_item",
    #     payload={"nm_id": nm_id},
    #     status="success" if result.success else "error",
    #     wb_response=result.wb_response
    # )

    return result


@router.patch("/{nm_id}/content", response_model=WBApiResponse)
async def update_item_content(
        nm_id: int,
        content: dict,
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key),
        db: AsyncSession = Depends(get_db)
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    result = await wb_client.update_card_content(nm_id, content)

    # # Логируем действие
    # await history_crud.create_history_record(
    #     db,
    #     user_id=current_user["id"],
    #     nm_id=nm_id,
    #     action="update_content",
    #     payload=content,
    #     status="success" if result.success else "error",
    #     wb_response=result.wb_response
    # )

    return result

from datetime import datetime

@router.post("/{nm_id}/schedule", response_model=dict)
async def schedule_content_update(
    nm_id: int,
    task_data: TaskCreate,  # Содержит только content и scheduled_at
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key),
    wb_api_key: str = Depends(get_wb_api_key)
):
    wb_client = WBAPIClient(api_key=wb_api_key)

    current_card_response = await wb_client.get_card_by_nm(nm_id)
    if not current_card_response.success:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    current_card = current_card_response.data
    new_content = task_data.content or {}

    payload = {
        key: value
        for key, value in new_content.items()
        if value is not None and value != current_card.get(key)
    }

    if not payload:
        raise HTTPException(status_code=400, detail="Нет изменений для обновления")

    try:
        scheduled_at = (
            datetime.fromisoformat(task_data.scheduled_at)
            if isinstance(task_data.scheduled_at, str)
            else task_data.scheduled_at
        )

        task = await create_scheduled_task(
            db=db,
            nm_id=nm_id,
            action="update_content",
            payload=payload,
            scheduled_at=scheduled_at,
            user_id=current_user.id
        )

        return {"task_id": task.id, "scheduled_at": task.scheduled_at}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при создании задачи: {e}")


@router.get("/search/{nm_id}", response_model=WBApiResponse)
async def search_item(
        nm_id: int,
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key),
        db: AsyncSession = Depends(get_db)
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    result = await wb_client.get_card_by_nm(nm_id)

    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=f"Товар с артикулом {nm_id} не найден"
        )

    return result