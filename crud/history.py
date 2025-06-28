from zoneinfo import ZoneInfo
from fastapi import HTTPException
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import settings
from crud.task import create_scheduled_task
from dependencies import get_wb_api_key
from models import User, ScheduledTask
from models.history import History
from datetime import datetime
from PIL import Image
from io import BytesIO
import requests

from utils.wb_api import WBAPIClient


async def create_history(
        db: AsyncSession,
        vendor_code: str,
        action: str,
        payload: dict,
        scheduled_at: datetime,
        user_id: int,
        changes: dict,
        brand: str,
        status: str,
        created_at: datetime
) -> History:
    history = History(
        created_at=created_at,
        scheduled_at=scheduled_at,
        vendor_code=vendor_code,
        status=status,
        changes=changes,
        card_payload=payload,
        user_id=user_id,
        brand=brand,
        action=action
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)
    return history


async def update_history_status(db: AsyncSession, status: str, user_id: int, created_at: datetime) -> None:
    history_card = await get_history_by_user_id(db, user_id, created_at)
    if not history_card:
        return

    history_card.status = status

    try:
        await db.commit()
        await db.refresh(history_card)
    except Exception as e:
        await db.rollback()


from typing import List, Tuple, Optional
from sqlalchemy import func, desc, asc
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession


async def get_tasks(
        db: AsyncSession,
        offset: int = 0,
        limit: int = 20,
        order_by: str = "created_at",
        order_dir: str = "desc",
        email: Optional[str] = None,
        brand: Optional[str] = None,
        vendor_code: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
) -> Tuple[List[History], int]:
    # Базовый запрос
    stmt = select(History).options(joinedload(History.user))

    # Применяем фильтры
    if email:
        stmt = stmt.join(History.user).where(User.email.ilike(f"%{email}%"))
    if brand:
        stmt = stmt.where(History.brand.ilike(f"%{brand}%"))
    if vendor_code:
        stmt = stmt.where(History.vendor_code.ilike(f"%{vendor_code}%"))
    if date_from:
        stmt = stmt.where(History.created_at >= date_from)
    if date_to:
        stmt = stmt.where(History.created_at <= date_to)

    # Получаем общее количество
    total_query = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_query.scalar_one()

    # Сортировка
    sort_column_map = {
        "created_at": History.created_at,
        "scheduled_at": History.scheduled_at,
        "vendor_code": History.vendor_code,
        "brand": History.brand,
        "action": History.action,
        "status": History.status,
    }

    sort_col = sort_column_map.get(order_by, History.created_at)
    if order_dir == "asc":
        stmt = stmt.order_by(asc(sort_col))
    else:
        stmt = stmt.order_by(desc(sort_col))

    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    histories = result.scalars().all()

    return histories, total


async def get_history_by_user_id(db: AsyncSession, user_id: int, created_at: datetime) -> History:
    result = await db.execute(
        select(History).where(History.user_id == user_id).where(History.created_at == created_at).options(
            joinedload(History.user)))
    return result.scalars().first()


async def get_history_by_id(db: AsyncSession, id: int) -> History:
    result = await db.execute(
        select(History).where(History.id == id).options(joinedload(History.user)))
    return result.scalars().first()


async def revert_history_change_by_id(db: AsyncSession, history_id: int):
    history = await get_history_by_id(db, history_id)

    result_task = await db.execute(
        select(ScheduledTask).where(ScheduledTask.created_at == history.created_at)
    )
    task = result_task.scalars().first()

    if not history:
        raise HTTPException(status_code=404, detail="Запись истории не найдена")
    now = datetime.now(ZoneInfo("Europe/Moscow"))

    formatted_time = history.created_at.astimezone(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")

    await create_history(
        db=db,
        vendor_code=history.vendor_code,
        action="revert_content",
        payload=history.card_payload,
        scheduled_at=now,
        user_id=history.user_id,
        changes={"revert": f"Откат изменений {formatted_time} в карточке {history.vendor_code}"},
        brand=history.brand,
        status="pending",
        created_at=now
    )

    scheduled_task = await create_scheduled_task(
        db=db,
        nm_id=task.nm_id,
        action="update_content",
        payload=history.card_payload,
        scheduled_at=now,
        user_id=history.user_id,
        changes={"revert": f"Откат изменений {history.created_at}"},
        brand=history.brand,
        created_at=now
    )

    return scheduled_task


async def upload_to_imgbb(api_key, image_bytes, expiration=None):
    files = {"image": ("converted.jpg", image_bytes)}
    params = {"key": api_key}
    if expiration:
        params["expiration"] = expiration

    response = requests.post(
        "https://api.imgbb.com/1/upload",
        params=params,
        files=files
    )
    response.raise_for_status()
    return response.json()["data"]["url"]


async def get_new_photo_url_by_index(card: list, index: int) -> str:
    try:
        return card[index]["big"]
    except (IndexError, KeyError, TypeError):
        raise ValueError(f"Невозможно получить новое фото по индексу {index}")


async def revert_history_media(
        db: AsyncSession,
        history_id:int,
        wb_api_key: str
):
    history = await get_history_by_id(db, history_id)

    result_task = await db.execute(
        select(ScheduledTask).where(ScheduledTask.created_at == history.created_at)
    )
    task = result_task.scalars().first()

    wb_client = WBAPIClient(api_key=wb_api_key)
    current_card_response = await wb_client.get_card_by_vendor(history.vendor_code)
    if not current_card_response.success:
        raise HTTPException(
            status_code=404,
            detail=f"Товар с vendorCode {history.vendor_code} не найден"
        )

    media_payload = history.card_payload.get("media")
    if not media_payload or len(media_payload) < 2:
        raise HTTPException(status_code=400, detail="Неверный формат card_payload: media отсутствует или неполный")

    old_url = media_payload[0]
    photo_index = media_payload[1]

    photos = current_card_response.data.get("photos")
    if not photos:
        raise HTTPException(status_code=404, detail="Фото товара не найдены")

    media_urls = []
    for i, photo in enumerate(photos):
        if i == photo_index:
            media_urls.append(old_url)
        else:
            media_urls.append(photo.get("big") or photo.get("hq") or photo.get("c246x328") or "")

    media = media_urls
    now = datetime.now(ZoneInfo("Europe/Moscow"))
    formatted_time = history.created_at.astimezone(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")

    await create_history(
        db=db,
        vendor_code=history.vendor_code,
        action="revert_media",
        payload=history.card_payload,
        scheduled_at=now,
        user_id=history.user_id,
        changes={"revert": f"Откат изменений {formatted_time} в карточке {history.vendor_code}"},
        brand=history.brand,
        status="pending",
        created_at=now
    )

    scheduled_task = await create_scheduled_task(
        db=db,
        nm_id=task.nm_id,
        action="update_media",
        payload={"media": media},
        scheduled_at=now,
        user_id=history.user_id,
        changes={"revert": f"Откат изменений {history.created_at}"},
        brand=history.brand,
        created_at=now
    )

    return scheduled_task


async def convert_image_url_to_jpg_bytes(image_url: str) -> BytesIO:
    response = requests.get(image_url)
    response.raise_for_status()

    image = Image.open(BytesIO(response.content)).convert("RGB")

    jpg_bytes = BytesIO()
    image.save(jpg_bytes, format="JPEG", quality=95)
    jpg_bytes.seek(0)

    return jpg_bytes





