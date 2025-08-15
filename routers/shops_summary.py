from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from dependencies import get_db, get_current_user_with_wb_key
from models.user import User
from crud.shops_summary import get_products_by_brand, get_reviews_summary_crud, get_brands_by_shop, get_reviews_tops_crud

router = APIRouter(tags=["ShopsSummary"], prefix="/api")

@router.get("/products")
async def get_products(
    shop: str = Query(..., description="Тип магазина: wb или ozon"),
    brand_id: str = Query(..., description="ID бренда"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение товаров по бренду и магазину"""
    products = await get_products_by_brand(db, current_user.id, shop, brand_id)
    return products

@router.get("/reviews/summary")
async def get_reviews_summary(
    shop: str = Query(..., description="Тип магазина: wb или ozon"),
    brand_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),  # Изменено с int на str
    date_from: date = Query(...),
    date_to: date = Query(...),
    metrics: str = Query(..., description="Метрика для отображения"),
    filters: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение краткой статистики по отзывам (для графика)"""
    # Преобразуем строку в список для совместимости с CRUD
    metrics_list = [metrics]
    summary = await get_reviews_summary_crud(db, current_user.id, shop, brand_id, product_id, date_from, date_to, metrics_list, filters)
    return summary

@router.get("/reviews/tops")
async def get_reviews_tops(
    shop: str = Query(...),
    brand_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),  # Изменено с int на str
    date_from: date = Query(...),
    date_to: date = Query(...),
    type: str = Query(..., description="products_negative или reasons_negative"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    tops = await get_reviews_tops_crud(db, current_user.id, shop, brand_id, product_id, date_from, date_to, type, limit, offset)
    return tops

@router.get("/brands")
async def get_brands(
    shop: str = Query(..., description="Тип магазина: wb или ozon"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение брендов по магазину (wb или ozon)"""
    brands = await get_brands_by_shop(db, current_user.id, shop)
    return brands 