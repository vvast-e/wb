from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, Tuple
from models.feedback import Feedback
from datetime import datetime, timedelta

async def get_product_reviews_crud(
    db: AsyncSession,
    user_id: int,
    article: str,
    page: int = 1,
    per_page: int = 20,
    rating: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Dict[str, Any]:
    # Защита от некорректного article
    try:
        article_int = int(article)
    except (ValueError, TypeError):
        return {"items": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0}
    offset = (page - 1) * per_page
    query = select(Feedback).where(
        Feedback.article == str(article)
    )
    if rating:
        query = query.where(Feedback.rating == rating)
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            query = query.where(Feedback.date >= date_from_dt)
        except Exception:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            query = query.where(Feedback.date <= date_to_dt)
        except Exception:
            pass
    total_result = await db.execute(query)
    total = len(total_result.scalars().all())
    query = query.order_by(desc(Feedback.date)).offset(offset).limit(per_page)
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    items = []
    for f in feedbacks:
        items.append({
            "id": f.id,
            "author": getattr(f, 'author', None),
            "rating": getattr(f, 'rating', None),
            "text": getattr(f, 'text', None),
            "date": getattr(f, 'date', None),
            "is_negative": getattr(f, 'is_negative', None),
            "is_processed": getattr(f, 'is_processed', None),
            "is_deleted": bool(getattr(f, 'is_deleted', False))
        })
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

async def get_product_stats_crud(
    db: AsyncSession,
    user_id: int,
    article: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    # Защита от некорректного article
    try:
        article_int = int(article)
    except (ValueError, TypeError):
        return None
    query = select(Feedback).where(
        Feedback.article == str(article)
    )
    # For period filter
    period_query = query
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
            period_query = period_query.where(Feedback.date >= date_from_dt)
        except Exception:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
            period_query = period_query.where(Feedback.date <= date_to_dt)
        except Exception:
            pass
    # All-time feedbacks
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    # Period feedbacks
    period_result = await db.execute(period_query)
    period_feedbacks = period_result.scalars().all()
    if not feedbacks:
        return None
    # --- All-time ratings ---
    ratings = [f.rating for f in feedbacks if hasattr(f, 'rating') and isinstance(f.rating, (int, float))]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    # All-time market_rating
    def get_feedback_datetime(f):
        dt = getattr(f, 'date', None)
        if dt is None:
            dt = getattr(f, 'created_at', None)
        return dt if dt is not None else datetime.min
    feedbacks_sorted = sorted(feedbacks, key=get_feedback_datetime, reverse=True)
    valid_feedbacks = feedbacks_sorted[:20000]
    now = datetime.now()
    def get_decay(days):
        if days <= 0:
            return 1.0
        return 100 ** (-(days - 182) / (730 * 1.5))
    weighted_sum = 0.0
    decay_sum = 0.0
    for idx, f in enumerate(valid_feedbacks):
        dt = get_feedback_datetime(f)
        days = (now.date() - dt.date()).days
        decay = 1.0 if idx < 15 else get_decay(days)
        rating_val = getattr(f, 'rating', 0)
        if not isinstance(rating_val, (int, float)):
            rating_val = 0
        weighted_sum += rating_val * decay
        decay_sum += decay
    market_rating = (weighted_sum / decay_sum) if decay_sum > 0 else 0
    # --- Period ratings ---
    period_ratings = [f.rating for f in period_feedbacks if hasattr(f, 'rating') and isinstance(f.rating, (int, float))]
    period_avg_rating = sum(period_ratings) / len(period_ratings) if period_ratings else 0
    # Period market_rating
    period_feedbacks_sorted = sorted(period_feedbacks, key=get_feedback_datetime, reverse=True)
    period_valid_feedbacks = period_feedbacks_sorted[:20000]
    period_weighted_sum = 0.0
    period_decay_sum = 0.0
    for idx, f in enumerate(period_valid_feedbacks):
        dt = get_feedback_datetime(f)
        days = (now.date() - dt.date()).days
        decay = 1.0 if idx < 15 else get_decay(days)
        rating_val = getattr(f, 'rating', 0)
        if not isinstance(rating_val, (int, float)):
            rating_val = 0
        period_weighted_sum += rating_val * decay
        period_decay_sum += decay
    period_market_rating = (period_weighted_sum / period_decay_sum) if period_decay_sum > 0 else 0
    # Negative share (period)
    period_negative_count = sum(1 for f in period_feedbacks if hasattr(f, 'is_negative') and f.is_negative is not None and int(f.is_negative) == 1)
    period_total_reviews = len(period_ratings)
    period_negative_share = round((period_negative_count / period_total_reviews) * 100, 1) if period_total_reviews > 0 else 0.0
    # All-time negative share
    negative_count = sum(1 for f in feedbacks if hasattr(f, 'is_negative') and f.is_negative is not None and int(f.is_negative) == 1)
    total_reviews = len(ratings)
    internal_negative_percentage = round((negative_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0
    ratings_count = {
        "5": sum(1 for r in ratings if r == 5),
        "4": sum(1 for r in ratings if r == 4),
        "3": sum(1 for r in ratings if r == 3),
        "2": sum(1 for r in ratings if r == 2),
        "1": sum(1 for r in ratings if r == 1)
    }
    period_ratings_count = {
        "5": sum(1 for r in period_ratings if r == 5),
        "4": sum(1 for r in period_ratings if r == 4),
        "3": sum(1 for r in period_ratings if r == 3),
        "2": sum(1 for r in period_ratings if r == 2),
        "1": sum(1 for r in period_ratings if r == 1)
    }
    return {
        "article": article,
        "average_rating": round(avg_rating, 2),
        "market_rating": round(market_rating, 2),
        "total_reviews": total_reviews,
        "negative_count": negative_count,
        "internal_negative_percentage": internal_negative_percentage,
        "ratings_count": ratings_count,
        "period": {
            "average_rating": round(period_avg_rating, 2),
            "market_rating": round(period_market_rating, 2),
            "total_reviews": period_total_reviews,
            "negative_count": period_negative_count,
            "negative_share": period_negative_share,
            "ratings_count": period_ratings_count
        }
    } 