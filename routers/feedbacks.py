from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crud.feedback import (
    get_feedbacks, get_feedback_analytics, update_feedback_processing,
    save_feedbacks_batch, get_unprocessed_negative_feedbacks, sync_feedbacks_with_soft_delete_optimized
)
from utils.wb_nodriver_parser import parse_feedbacks_optimized
from models.user import User
from schemas import (
    FeedbackResponse, FeedbackAnalyticsResponse, FeedbackListResponse,
    FeedbackFilterRequest, FeedbackParseRequest, FeedbackUpdate
)
from dependencies import get_db, get_current_user_with_wb_key

router = APIRouter(tags=["Feedbacks"], prefix="/api/feedbacks")


@router.post("/parse", response_model=dict)
async def parse_and_save_feedbacks(
    request: FeedbackParseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Парсинг отзывов и сохранение в БД"""
    try:
        # Парсим отзывы через HTTP API
        feedbacks_data = await parse_feedbacks_optimized(
            request.article, 
            request.max_count
        )
        
        if feedbacks_data is None:
            raise HTTPException(status_code=500, detail="Ошибка парсинга отзывов")
        
        # Добавляем артикул к каждому отзыву
        for feedback in feedbacks_data:
            feedback['article'] = request.article
        
        result = {
            "parsed_count": len(feedbacks_data),
            "feedbacks": feedbacks_data
        }
        
        # Сохраняем в БД если нужно
        if request.save_to_db:
            # Используем оптимизированную функцию синхронизации
            sync_stats = await sync_feedbacks_with_soft_delete_optimized(
                db=db,
                feedbacks_from_wb=feedbacks_data,
                brand=request.brand,
                user_id=current_user.id
            )
            result["saved_count"] = sync_stats.get('new_feedbacks', 0)
            result["message"] = f"Сохранено {sync_stats.get('new_feedbacks', 0)} новых отзывов в БД"
            result["sync_stats"] = sync_stats
        
        return result
        
    except Exception as e:
        print(f"Ошибка при парсинге отзывов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


@router.get("/", response_model=FeedbackListResponse)
async def get_feedbacks_list(
    article: Optional[int] = Query(None),
    brand: Optional[str] = Query(None),
    rating_min: Optional[int] = Query(None),
    rating_max: Optional[int] = Query(None),
    is_negative: Optional[int] = Query(None),
    is_processed: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    include_deleted: bool = Query(False, description="Включить удаленные отзывы"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    order_by: str = Query("created_at"),
    order_dir: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение списка отзывов с фильтрацией и пагинацией"""
    offset = (page - 1) * per_page
    
    feedbacks = await get_feedbacks(
        db=db,
        article=article,
        brand=brand,
        rating_min=rating_min,
        rating_max=rating_max,
        is_negative=is_negative,
        is_processed=is_processed,
        date_from=date_from,
        date_to=date_to,
        include_deleted=include_deleted,
        limit=per_page,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir
    )
    
    # Получаем общее количество для пагинации
    total_feedbacks = await get_feedbacks(
        db=db,
        article=article,
        brand=brand,
        rating_min=rating_min,
        rating_max=rating_max,
        is_negative=is_negative,
        is_processed=is_processed,
        date_from=date_from,
        date_to=date_to,
        include_deleted=include_deleted,
        limit=10000,  # Большой лимит для подсчета
        offset=0
    )
    
    total = len(total_feedbacks)
    
    return FeedbackListResponse(
        items=[FeedbackResponse.from_orm(feedback) for feedback in feedbacks],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page
    )


@router.get("/analytics", response_model=FeedbackAnalyticsResponse)
async def get_feedbacks_analytics(
    article: Optional[int] = Query(None),
    brand: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение аналитики по отзывам"""
    analytics = await get_feedback_analytics(
        db=db,
        article=article,
        brand=brand,
        date_from=date_from,
        date_to=date_to
    )
    
    return FeedbackAnalyticsResponse(**analytics)


@router.get("/negative/unprocessed", response_model=List[FeedbackResponse])
async def get_unprocessed_negative(
    brand: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение необработанных негативных отзывов"""
    feedbacks = await get_unprocessed_negative_feedbacks(
        db=db,
        brand=brand,
        limit=limit
    )
    
    return [FeedbackResponse.from_orm(feedback) for feedback in feedbacks]


@router.patch("/{feedback_id}/processing", response_model=FeedbackResponse)
async def update_feedback_processing_status(
    feedback_id: int,
    update_data: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Обновление статуса обработки отзыва"""
    feedback = await update_feedback_processing(
        db=db,
        feedback_id=feedback_id,
        is_processed=update_data.is_processed,
        processing_notes=update_data.processing_notes,
        sentiment_score=update_data.sentiment_score
    )
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    
    return FeedbackResponse.from_orm(feedback)


@router.post("/sync", response_model=dict)
async def sync_feedbacks_endpoint(
    brand: str,
    feedbacks_data: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Массовая синхронизация отзывов с использованием оптимизированной функции"""
    try:
        sync_stats = await sync_feedbacks_with_soft_delete_optimized(
            db=db,
            feedbacks_from_wb=feedbacks_data,
            brand=brand,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "message": f"Синхронизация завершена для бренда {brand}",
            "stats": sync_stats
        }
        
    except Exception as e:
        print(f"Ошибка при синхронизации отзывов: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")


@router.get("/dashboard/stats", response_model=dict)
async def get_dashboard_stats(
    brand: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
):
    """Получение статистики для дашборда"""
    # Общая аналитика
    analytics = await get_feedback_analytics(db=db, brand=brand)
    
    # Необработанные негативные отзывы
    unprocessed_negative = await get_unprocessed_negative_feedbacks(
        db=db, brand=brand, limit=10
    )
    
    # Последние отзывы
    recent_feedbacks = await get_feedbacks(
        db=db, brand=brand, limit=10, order_by="created_at", order_dir="desc"
    )
    
    return {
        "analytics": analytics,
        "unprocessed_negative_count": len(unprocessed_negative),
        "recent_feedbacks": [
            {
                "id": f.id,
                "article": f.article,
                "rating": f.rating,
                "author": f.author,
                "created_at": f.created_at,
                "is_negative": f.is_negative,
                "is_processed": f.is_processed
            }
            for f in recent_feedbacks
        ]
    }