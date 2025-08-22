from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from crud.admin import get_brands
from models import User
from models.feedback import Feedback
from sqlalchemy import select, and_, func, desc
from datetime import date

async def get_brands_by_shop(db: AsyncSession, user_id: int, shop: str) -> List[Dict[str, str]]:
    """Получение брендов пользователя (WB-only, без фильтрации по магазину)"""
    all_brands = await get_brands(db, user_id)
    return [{"name": k} for k in all_brands.keys()]

async def get_products_by_brand(db: AsyncSession, user_id: int, shop: str, brand_id: str) -> List[Dict[str, Any]]:
    """Получение товаров по бренду и магазину (vendor_code из feedbacks)"""
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
        response = await wb.get_cards_list(payload)

        # Безопасная обработка ответа WB API
        if not response or not getattr(response, 'success', False):
            return []
        data = response.data or {}
        if not isinstance(data, dict):
            return []
        cards = data.get("cards", [])
        
        # Получаем vendor_code из feedbacks для всех nmID
        nm_ids = [str(card["nmID"]) for card in cards]
        vendor_codes = {}
        
        if nm_ids:
            # Ищем vendor_code в feedbacks по nm_id (article)
            feedback_query = select(Feedback.vendor_code).where(
                and_(
                    Feedback.user_id == user_id,
                    Feedback.brand == brand_id,
                    Feedback.article.in_(nm_ids)
                )
            ).distinct()
            feedback_result = await db.execute(feedback_query)
            feedback_vendor_codes = feedback_result.scalars().all()
            
            # Создаем маппинг nm_id -> vendor_code
            for nm_id in nm_ids:
                # Ищем vendor_code для конкретного nm_id
                specific_query = select(Feedback.vendor_code).where(
                    and_(
                        Feedback.user_id == user_id,
                        Feedback.brand == brand_id,
                        Feedback.article == nm_id
                    )
                ).limit(1)
                specific_result = await db.execute(specific_query)
                vendor_code = specific_result.scalar()
                vendor_codes[nm_id] = vendor_code or nm_id
        
        return [{"id": str(vendor_codes.get(str(card["nmID"]), card["nmID"])), "name": f"товар {vendor_codes.get(str(card['nmID']), card['nmID'])}"} for card in cards]
    else:
        # Получаем vendor_code из отзывов
        query = select(Feedback.vendor_code).where(
            and_(Feedback.user_id == user_id, Feedback.brand == brand_id)
        ).distinct()
        result = await db.execute(query)
        vendor_codes = result.scalars().all()
        
        return [{"id": str(vc), "name": f"товар {vc}"} for vc in vendor_codes if vc]

async def get_shop_feedbacks_crud(
    db: AsyncSession,
    user_id: int,
    brand_id: Optional[str] = None,
    product_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    filters: Optional[str] = None,
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Получение отзывов для магазина с фильтрацией"""
    from models.feedback import Feedback
    from sqlalchemy import select, func, and_, or_
    
    if not metrics:
        metrics = ['total', 'negative', 'deleted']
    
    query = select(Feedback).where(Feedback.user_id == user_id)
    if brand_id:
        query = query.where(Feedback.brand == brand_id)
    if product_id:
        print(f"[DEBUG] Фильтруем по vendor_code: {product_id}")
        # Простое сравнение по vendor_code в feedbacks
        query = query.where(Feedback.vendor_code == product_id)
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
    
    # Если нет отзывов, возвращаем пустой результат
    if total_reviews == 0:
        return {"total_reviews": 0, "by_day": []}

    # Внутренние агрегаты, не зависящие от запрошенных метрик
    day_aggregates: Dict[str, Dict[str, Any]] = {}
    for f in feedbacks:
        d = f.date.date().isoformat() if f.date else None
        if not d:
            continue
        if d not in day_aggregates:
            day_aggregates[d] = {
                'total': 0,
                'negative': 0,
                'deleted': 0,
                'ratings': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        day_aggregates[d]['total'] += 1
        if getattr(f, 'is_negative', False):
            day_aggregates[d]['negative'] += 1
        if getattr(f, 'is_deleted', False):
            day_aggregates[d]['deleted'] += 1
        try:
            r = int(f.rating) if f.rating is not None else None
            if r in (1, 2, 3, 4, 5):
                day_aggregates[d]['ratings'][r] += 1
        except Exception:
            pass

    # Формируем ответ только с запрошенными метриками
    by_day_list: List[Dict[str, Any]] = []
    sorted_dates = sorted(day_aggregates.keys())
    
    # Для накопительных расчётов (доли)
    cumulative_total = 0
    cumulative_negative = 0
    cumulative_deleted = 0
    
    for d in sorted_dates:
        counts = day_aggregates[d]
        cumulative_total += counts['total']
        cumulative_negative += counts['negative']
        cumulative_deleted += counts['deleted']
        
        entry: Dict[str, Any] = {"date": d}
        for m in metrics:
            if m == 'negative':
                entry['negative'] = counts['negative']
            elif m == 'deleted':
                entry['deleted'] = counts['deleted']
            elif m == 'negative_share':
                entry['negative_share'] = round((cumulative_negative / cumulative_total) * 100, 1) if cumulative_total > 0 else 0.0
            elif m == 'deleted_share':
                entry['deleted_share'] = round((cumulative_deleted / cumulative_total) * 100, 1) if cumulative_total > 0 else 0.0
            elif m in ('1', '2', '3', '4', '5'):
                entry[m] = counts['ratings'].get(int(m), 0)
        by_day_list.append(entry)

    return {"total_reviews": total_reviews, "by_day": by_day_list}

async def get_reviews_tops_crud(db: AsyncSession, user_id: int, brand_id: Optional[str], product_id: Optional[str], date_from, date_to, type: str, limit: int, offset: int) -> List[Dict[str, Any]]:
    query = select(Feedback).where(Feedback.user_id == user_id)
    if brand_id:
        query = query.where(Feedback.brand == brand_id)
    if product_id:
        print(f"[DEBUG] Фильтруем по vendor_code: {product_id}")
        # Простое сравнение по vendor_code в feedbacks
        query = query.where(Feedback.vendor_code == product_id)
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
    elif type == 'top_products':
        # Топ товаров
        products_data = {}
        for feedback in feedbacks:
            vendor_code = feedback.vendor_code or str(feedback.article)
            if vendor_code not in products_data:
                products_data[vendor_code] = []
            products_data[vendor_code].append(feedback.rating)

        top_products = []
        for vendor_code, ratings_list in products_data.items():
            avg_product_rating = sum(ratings_list) / len(ratings_list)
            top_products.append({
                "name": f"товар {vendor_code}",
                "rating": round(avg_product_rating, 2)
            })

        top_products.sort(key=lambda x: x["rating"], reverse=True)
        tops = top_products[offset:offset+limit]
    return tops