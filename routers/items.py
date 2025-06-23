from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from crud.task import create_scheduled_task
from crud.user import get_decrypted_wb_key
from models import ScheduledTask
from models.user import User
from utils.wb_api import WBAPIClient
from schemas import WBApiResponse, TaskCreate, MediaTaskRequest
from dependencies import get_db, get_current_user_with_wb_key, get_wb_api_key

router = APIRouter(tags=["Items"], prefix="/api/items")


@router.get("/", response_model=WBApiResponse)
async def get_items(
        brand: str = Query(..., description="Название бренда (обязательно)"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_with_wb_key),
):
    wb_api_key = await get_decrypted_wb_key(db, current_user, brand)

    try:
        wb_client = WBAPIClient(api_key=wb_api_key)
        result = await wb_client.get_cards_list()

        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=result.error or "Не удалось получить карточки с WB API"
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{nm_id}", response_model=WBApiResponse)
async def get_item(
        nm_id: int,
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key),
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


# @router.patch("/{nm_id}/content", response_model=WBApiResponse)
# async def update_item_content(
#         nm_id: int,
#         content: dict,
#         current_user: User = Depends(get_current_user_with_wb_key),
#         wb_api_key: str = Depends(get_wb_api_key),
#         db: AsyncSession = Depends(get_db)
# ):
#     wb_client = WBAPIClient(api_key=wb_api_key)
#     result = await wb_client.update_card_content(nm_id, content)
#
#     # # Логируем действие
#     # await history_crud.create_history_record(
#     #     db,
#     #     user_id=current_user["id"],
#     #     nm_id=nm_id,
#     #     action="update_content",
#     #     payload=content,
#     #     status="success" if result.success else "error",
#     #     wb_response=result.wb_response
#     # )
#
#     return result


@router.post("/{nm_id}/schedule", response_model=dict)
async def schedule_content_update(
        nm_id: int,
        task_data: TaskCreate,  # Содержит только content и scheduled_at
        brand: str = Query(..., description="Название бренда"),
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

    changes = {}
    for key, new_value in new_content.items():
        old_value = current_card.get(key)

        if compare_values(old_value, new_value):
            continue
        else:
            changes[key] = new_value

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
            user_id=current_user.id,
            changes=changes,
            brand=brand
        )

        return {"task_id": task.id, "scheduled_at": task.scheduled_at}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при создании задачи: {e}")


@router.post("/{nm_id}/media")
async def schedule_media_update(
        nm_id: int,
        request: MediaTaskRequest,
        brand: str = Query(..., description="Название бренда"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_with_wb_key)
):
    if nm_id != request.nmId:
        raise HTTPException(status_code=400, detail="nmId mismatch")

    if not (1 <= len(request.media) <= 30):
        raise HTTPException(status_code=400, detail="От 1 до 30 ссылок на фото")

    task = await create_scheduled_task(
        db=db,
        nm_id=nm_id,
        action="update_media",
        payload={"media": request.media},
        scheduled_at=request.scheduled_at,
        user_id=current_user.id,
        changes={"media": "Медиа обновлены"},
        brand=brand
    )

    return {"task_id": task.id, "scheduled_at": task.scheduled_at}


@router.post("/{nm_id}/upload-media-file", response_model=WBApiResponse)
async def upload_media_file(
        nm_id: int,
        brand: str = Query(..., description="Название бренда"),
        file: UploadFile = File(...),
        photo_number: int = Form(...),
        media_type: str = Form('image'),
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key),
        db: AsyncSession = Depends(get_db)
):
    if not file:
        raise HTTPException(status_code=422, detail="File is required")

    if media_type == 'video':
        if photo_number != 1:
            raise HTTPException(status_code=422, detail="Video can only be uploaded to position 1")

        existing_tasks = await db.execute(
            select(ScheduledTask).where(
                ScheduledTask.nm_id == nm_id,
                ScheduledTask.payload["media_type"].astext == 'video'
            )
        )
        if existing_tasks.scalars().first():
            raise HTTPException(status_code=422, detail="Only one video allowed per product")

    if photo_number < 1 or photo_number > 30:
        raise HTTPException(status_code=422, detail="Photo number must be between 1 and 30")

    if media_type not in ['image', 'video']:
        raise HTTPException(status_code=422, detail="Invalid media type")

    file_data = await file.read()

    task = await create_scheduled_task(
        db=db,
        nm_id=nm_id,
        action="upload_media_file",
        payload={
            "file_data": file_data.decode('latin1'),
            "photo_number": photo_number,
            "filename": file.filename,
            "media_type": media_type
        },
        scheduled_at=datetime.now(),
        user_id=current_user.id,
        changes={"media": f"Добавлено {media_type} {photo_number}"},
        brand=brand
    )

    return WBApiResponse(
        success=True,
        data={"task_id": task.id}
    )


@router.get("/search/{vendor_code}", response_model=WBApiResponse)
async def search_item(
        vendor_code: str,
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key),
        db: AsyncSession = Depends(get_db)
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    result = await wb_client.get_card_by_vendor(vendor_code)

    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=f"Товар с vendorCode {vendor_code} не найден"
        )

    return result


def compare_values(old, new):
    if isinstance(old, str) and isinstance(new, str):
        return old.strip() == new.strip()

    if isinstance(old, dict) and isinstance(new, dict):
        ignored_keys = {'isValid'}
        old_copy = {k: v for k, v in old.items() if k not in ignored_keys}
        new_copy = {k: v for k, v in new.items() if k not in ignored_keys}
        return old_copy == new_copy

    if isinstance(old, list) and isinstance(new, list):
        def normalize(lst):
            norm = []
            for item in lst:
                d = dict(item)  # копия
                if 'value' in d:
                    val = d['value']
                    if not isinstance(val, list):
                        val = [val]
                    val = [str(v).strip() for v in val]
                    d['value'] = val
                norm.append(d)
            norm.sort(key=lambda x: (x.get('id', 0), x.get('name', '')))
            return norm

        return normalize(old) == normalize(new)

    # Для всего остального — простое сравнение
    return old == new
