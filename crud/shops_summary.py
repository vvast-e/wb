from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from crud.admin import get_brands
from models import User
from models.feedback import Feedback
from sqlalchemy import select, and_, func, desc

async def get_brands_by_shop(db: AsyncSession, user_id: int, shop: str) -> List[Dict[str, str]]:
    """Получение брендов пользователя (WB-only, без фильтрации по магазину)"""
    all_brands = await get_brands(db, user_id)
    return [{"name": k} for k in all_brands.keys()]

async def get_products_by_brand(db: AsyncSession, user_id: int, shop: str, brand_id: str) -> List[Dict[str, Any]]:
    """Получение товаров по бренду и магазину (артикулы из отзывов)"""
    if shop.lower() == 'wb':
        from utils.wb_api import WBAPIClient
        from crud.user import get_decrypted_wb_key
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()
        wb_api_key = await get_decrypted_wb_key(db, user, brand_id)
        wb = WBAPIClient(wb_api_key)
        payload = {
            "settings": {
                "cursor": {},
                "filter": {"brand": brand_id, "withPhoto": 1}
            }
        }
        resonse = await wb.get_cards_list(payload)

        cards = resonse.data.get("cards", [])
        return [{"id": str(card["nmID"]), "name": str(card["nmID"])} for card in cards]
    else:
        query = select(Feedback.article).where(
            and_(Feedback.user_id == user_id, Feedback.brand == brand_id)
        ).distinct()
        result = await db.execute(query)
        articles = result.scalars().all()
        return [{"id": str(a), "name": str(a)} for a in articles]

async def get_reviews_summary_crud(
        db: AsyncSession,
        user_id: int,
        shop: str,
        brand_id: Optional[str],
        product_id: Optional[str],
        date_from,
        date_to,
        metrics: List[str],
        filters: Optional[str]
) -> Dict[str, Any]:
    query = select(Feedback).where(Feedback.user_id == user_id)
    if brand_id:
        query = query.where(Feedback.brand == brand_id)
    if product_id:
        try:
            article_int = int(product_id)
            query = query.where(Feedback.article == article_int)
        except Exception:
            pass
    if date_from:
        query = query.where(Feedback.date >= date_from)
    if date_to:
        query = query.where(Feedback.date <= date_to)
    
    # Обработка фильтров
    if filters:
        try:
            import json
            filter_data = json.loads(filters)
            if 'is_negative' in filter_data:
                query = query.where(Feedback.is_negative == filter_data['is_negative'])
            if 'is_deleted' in filter_data:
                query = query.where(Feedback.is_deleted == filter_data['is_deleted'])
            if 'rating' in filter_data:
                query = query.where(Feedback.rating == filter_data['rating'])
            if 'rating_min' in filter_data:
                query = query.where(Feedback.rating >= filter_data['rating_min'])
            if 'rating_max' in filter_data:
                query = query.where(Feedback.rating <= filter_data['rating_max'])
        except:
            pass
    
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    total_reviews = len(feedbacks)
    by_day = {}
    for f in feedbacks:
        d = f.date.date().isoformat() if f.date else None
        if not d:
            continue
        if d not in by_day:
            by_day[d] = {m: 0 for m in metrics}
        
        # Подсчет метрик
        if 'negative' in metrics and f.is_negative:
            by_day[d]['negative'] += 1
        if 'deleted' in metrics and getattr(f, 'is_deleted', False):
            by_day[d]['deleted'] += 1
        
        # Подсчет отзывов по рейтингам
        if str(f.rating) in metrics:
            by_day[d][str(f.rating)] += 1
        
        # Подсчет отзывов по итоговому рейтингу
        if f.rating == 5 and '5.0' in metrics:
            by_day[d]['5.0'] += 1
        elif f.rating == 4 and '4.9' in metrics:
            by_day[d]['4.9'] += 1
        elif f.rating == 4 and '4.8' in metrics:
            by_day[d]['4.8'] += 1
        elif f.rating == 4 and '4.7' in metrics:
            by_day[d]['4.7'] += 1
        elif f.rating == 4 and '4.6' in metrics:
            by_day[d]['4.6'] += 1
        elif f.rating == 4 and '4.5' in metrics:
            by_day[d]['4.5'] += 1
        elif f.rating < 4 and '<4.5' in metrics:
            by_day[d]['<4.5'] += 1
    
    # Вычисление долей
    for d in by_day:
        neg = by_day[d].get('negative', 0)
        deleted = by_day[d].get('deleted', 0)
        total = sum(by_day[d].values())
        if 'negative_share' in metrics:
            by_day[d]['negative_share'] = round((neg / total) * 100, 1) if total > 0 else 0.0
        if 'deleted_share' in metrics:
            by_day[d]['deleted_share'] = round((deleted / total) * 100, 1) if total > 0 else 0.0
    by_day_list = [{"date": d, **by_day[d]} for d in sorted(by_day.keys())]
    return {"total_reviews": total_reviews, "by_day": by_day_list}

async def get_reviews_tops_crud(db: AsyncSession, user_id: int, shop: str, brand_id: Optional[str], product_id: Optional[str], date_from, date_to, type: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    query = select(Feedback).where(Feedback.user_id == user_id)
    if brand_id:
        query = query.where(Feedback.brand == brand_id)
    if product_id:
        try:
            article_int = int(product_id)
            query = query.where(Feedback.article == article_int)
        except Exception:
            pass
    if date_from:
        query = query.where(Feedback.date >= date_from)
    if date_to:
        query = query.where(Feedback.date <= date_to)
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    tops = []
    if type == 'products_negative':
        # Топ товаров по количеству негативных отзывов
        counter = {}
        for f in feedbacks:
            if f.is_negative:
                counter[f.article] = counter.get(f.article, 0) + 1
        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        for article, value in sorted_items[offset:offset+limit]:
            tops.append({"name": str(article), "value": value})
    elif type == 'reasons_negative':
        # Топ причин негатива (по cons_text)
        counter = {}
        for f in feedbacks:
            if f.is_negative and f.cons_text:
                reason = f.cons_text.strip().lower()
                counter[reason] = counter.get(reason, 0) + 1
        sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        for reason, value in sorted_items[offset:offset+limit]:
            tops.append({"name": reason, "value": value})
    return tops