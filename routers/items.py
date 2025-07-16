from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.admin import get_imagebb_key
from crud.history import create_history, upload_to_imgbb, convert_image_url_to_jpg_bytes
from crud.task import create_scheduled_task
from crud.user import get_decrypted_wb_key
from models import ScheduledTask
from models.user import User
from utils.wb_api import WBAPIClient
from schemas import WBApiResponse, TaskCreate, MediaTaskRequest
from dependencies import get_db, get_current_user_with_wb_key, get_wb_api_key
from config import settings
from utils.wb_nodriver_parser import parse_feedbacks_optimized

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
        cards = await wb_client.get_all_cards()
        return WBApiResponse(success=True, data={"cards": cards, "total": len(cards)})
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
    cards = await wb_client.get_all_cards()
    if not cards:
        return WBApiResponse(success=False, error="Карточка не найдена")
    for card in cards:
        if card.get("nmID") == nm_id:
            # Гарантируем, что photos и video попадут в ответ
            result = dict(card)
            result["photos"] = card.get("photos", [])
            if "video" in card:
                result["video"] = card["video"]
            return WBApiResponse(success=True, data=result)
    return WBApiResponse(success=False, error="Карточка не найдена")


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

    now=datetime.now(ZoneInfo("Europe/Moscow"))
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
            brand=brand,
            created_at=now
        )

        await create_history(
            db=db,
            vendor_code=current_card.get("vendorCode"),
            action="update_content",
            payload=current_card,
            scheduled_at=scheduled_at,
            user_id=current_user.id,
            changes=changes,
            brand=brand,
            status="pending",
            created_at=now
        )

        return {"task_id": task.id, "scheduled_at": task.scheduled_at}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при создании задачи: {e}")


@router.post("/{nm_id}/upload-imgbb", response_model=WBApiResponse)
async def upload_file_to_imgbb(
    nm_id: int,
    brand: str = Query(..., description="Название бренда"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_with_wb_key),
    db: AsyncSession = Depends(get_db)
):
    if not file:
        raise HTTPException(status_code=422, detail="File is required")

    imagebb_key=await get_imagebb_key(db, current_user.id)
    if not imagebb_key:
        return HTTPException(status_code=404, detail="Not found imagebb_key")

    try:
        image_bytes = await file.read()
        url = await upload_to_imgbb(imagebb_key, image_bytes)

        return WBApiResponse(
            success=True,
            data={"url": url}
        )
    except requests.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки на imgbb: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки файла: {str(e)}")


@router.post("/{nm_id}/media")
async def schedule_media_update(
        nm_id: int,
        request: MediaTaskRequest,
        brand: str = Query(..., description="Название бренда"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user_with_wb_key),
        wb_api_key: str = Depends(get_wb_api_key)
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    current_card_response = await wb_client.get_card_by_nm(nm_id)
    if not current_card_response.success:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    imagebb_key = await get_imagebb_key(db, current_user.id)
    if not imagebb_key:
        return HTTPException(status_code=404, detail="Not found imagebb_key")

    current_card = current_card_response.data

    if nm_id != request.nmId:
        raise HTTPException(status_code=400, detail="nmId mismatch")

    if not (1 <= len(request.media) <= 30):
        raise HTTPException(status_code=400, detail="От 1 до 30 ссылок на фото")
    now = datetime.now(ZoneInfo("Europe/Moscow"))

    old_converted_url=await convert_image_url_to_jpg_bytes(current_card.get("photos")[request.index]["big"])
    old_url=await upload_to_imgbb(imagebb_key, old_converted_url)
    await create_history(
        db=db,
        vendor_code=current_card.get("vendorCode"),
        action="update_media",
        payload={"media": [old_url, request.index]},
        scheduled_at=request.scheduled_at,
        user_id=current_user.id,
        changes={"media": "Медиа обновлены"},
        brand=brand,
        status="pending",
        created_at=now
    )

    task = await create_scheduled_task(
        db=db,
        nm_id=nm_id,
        action="update_media",
        payload={"media": request.media},
        scheduled_at=request.scheduled_at,
        user_id=current_user.id,
        changes={"media": "Медиа обновлены"},
        brand=brand,
        created_at=now
    )

    return {"task_id": task.id, "scheduled_at": task.scheduled_at}


@router.post("/{nm_id}/upload-media-file", response_model=WBApiResponse)
async def upload_media_file(
        nm_id: int,
        brand: str = Query(..., description="Название бренда"),
        scheduled_at: str = Form(...),
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

    try:
        scheduled_dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="Некорректный формат времени")

    file_data = await file.read()

    now = datetime.now(ZoneInfo("Europe/Moscow"))

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
        scheduled_at=scheduled_dt,
        user_id=current_user.id,
        changes={"media": f"Добавлено {media_type} {photo_number}"},
        brand=brand,
        created_at=now
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
        db: AsyncSession = Depends(get_db),
        brand: str = Query(..., description="Название бренда")
):
    wb_client = WBAPIClient(api_key=wb_api_key)
    cards = await wb_client.get_all_cards()
    if not cards:
        return WBApiResponse(success=False, error="Карточка не найдена")
    for card in cards:
        current_vc = str(card.get("vendorCode", "")).lower()
        if current_vc == vendor_code.lower():
            result = dict(card)
            result["photos"] = card.get("photos", [])
            if "video" in card:
                result["video"] = card["video"]
            return WBApiResponse(success=True, data=result)
    return WBApiResponse(success=False, error="Карточка не найдена")


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


@router.get("/feedbacks", tags=["Parser"])
async def get_feedbacks(article: int = Query(..., description="Артикул товара")):
    feedbacks = await parse_feedbacks_optimized(article)
    if feedbacks is None:
        raise HTTPException(status_code=500, detail="Ошибка парсинга отзывов")
    return {"count": len(feedbacks), "feedbacks": feedbacks}


