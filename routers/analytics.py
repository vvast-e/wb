from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crud.analytics import (
    get_user_shopsList_crud, get_reviews_with_filters_crud, get_shop_data_crud,
    get_shop_products_crud, get_efficiency_data_crud, get_shops_summary_crud,
    parse_shop_feedbacks_crud
)
from models.user import User
from dependencies import get_db, get_current_user_with_wb_key

router = APIRouter(tags=["Analytics"], prefix="/api/analytics")


@router.get("/shops")
async def get_user_shops(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение списка магазинов (брендов) пользователя"""
    return await get_user_shopsList_crud(db, current_user.id)


@router.get("/reviews")
async def get_reviews_with_filters(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
    shop: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    negative: Optional[bool] = Query(None),
    deleted: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение отзывов с расширенной фильтрацией"""
    return await get_reviews_with_filters_crud(
        db, current_user.id, page, per_page, search, 
        rating, shop, product, date_from, date_to, negative, deleted
    )


@router.get("/shop/{shop_id}")
async def get_shop_data(
    shop_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение данных магазина за период или за весь период, если даты не заданы"""
    # Если не передан период, возвращаем за весь период
    data = await get_shop_data_crud(db, current_user.id, shop_id, start_date, end_date)
    if not data:
        raise HTTPException(status_code=404, detail="Магазин не найден или нет данных")
    return data


@router.get("/shop/{shop_id}/products")
async def get_shop_products(
    shop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение товаров магазина"""
    return await get_shop_products_crud(db, current_user.id, shop_id)


@router.get("/efficiency/{shop_id}")
async def get_efficiency_data(
    shop_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    product_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение данных эффективности"""
    data = await get_efficiency_data_crud(db, current_user.id, shop_id, start_date, end_date, product_id)
    if not data:
        raise HTTPException(status_code=404, detail="Данные не найдены")
    return data


@router.get("/shops-summary")
async def get_shops_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение сводки по магазинам"""
    return await get_shops_summary_crud(db, current_user.id, start_date, end_date)


@router.post("/shop/{shop_id}/parse-feedbacks")
async def parse_shop_feedbacks_endpoint(
    shop_id: str,
    save_to_db: bool = Query(True),
    max_date: Optional[str] = Query(None, description="Максимальная дата отзыва YYYY-MM-DD (включительно)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Массовый парсинг отзывов всех товаров магазина"""
    result = await parse_shop_feedbacks_crud(
        db=db,
        user_id=current_user.id,
        shop_id=shop_id,
        save_to_db=save_to_db,
        max_date=max_date
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result 