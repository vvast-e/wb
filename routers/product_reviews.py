from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from crud.product_reviews import get_product_reviews_crud, get_product_stats_crud
from models.user import User
from dependencies import get_db, get_current_user_with_wb_key

router = APIRouter(tags=["ProductReviews"], prefix="/api/product-reviews")

@router.get("/{article}")
async def get_product_reviews(
    article: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    rating: Optional[int] = Query(None, ge=1, le=5),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    return await get_product_reviews_crud(db, current_user.id, article, page, per_page, rating, date_from, date_to)

@router.get("/{article}/stats")
async def get_product_stats(
    article: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    stats = await get_product_stats_crud(db, current_user.id, article, date_from, date_to)
    if not stats:
        raise HTTPException(status_code=404, detail="Нет данных по товару")
    return stats 