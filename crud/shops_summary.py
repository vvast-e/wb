from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from crud.admin import get_brands
from models import User
from models.feedback import Feedback
from models.product import Product
from sqlalchemy import select, and_, func, desc

async def get_brands_by_shop(db: AsyncSession, user_id: int, shop: str) -> List[Dict[str, str]]:
    """Получение брендов пользователя (WB-only, без фильтрации по магазину)"""
    all_brands = await get_brands(db, user_id)
    return [{"name": k} for k in all_brands.keys()]

async def get_products_by_brand(db: AsyncSession, user_id: int, shop: str, brand_id: str) -> List[Dict[str, Any]]:
    """Получение товаров по бренду и магазину (vendor_code из таблицы products)"""
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

        cards = response.data.get("cards", [])
        # Получаем vendor_code для всех nmID
        nm_ids = [str(card["nmID"]) for card in cards]  # Преобразуем в строки
        vendor_codes = {}
        if nm_ids:
            product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
            product_result = await db.execute(product_query)
            products_data_db = product_result.fetchall()
            for nm_id, vendor_code in products_data_db:
                vendor_codes[nm_id] = vendor_code or nm_id
        
        return [{"id": str(vendor_codes.get(str(card["nmID"]), card["nmID"])), "name": f"товар {vendor_codes.get(str(card['nmID']), card['nmID'])}"} for card in cards]
    else:
        # Получаем артикулы из отзывов
        query = select(Feedback.article).where(
            and_(Feedback.user_id == user_id, Feedback.brand == brand_id)
        ).distinct()
        result = await db.execute(query)
        articles = result.scalars().all()
        
        # Получаем vendor_code для всех артикулов
        vendor_codes = {}
        if articles:
            # Преобразуем артикулы в строки для поиска в таблице products
            nm_ids = []
            for article in articles:
                try:
                    # Преобразуем в строку для поиска в Product.nm_id
                    nm_id_str = str(article)
                    nm_ids.append(nm_id_str)
                except (ValueError, TypeError):
                    continue
            
            if nm_ids:
                product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
                product_result = await db.execute(product_query)
                products_data_db = product_result.fetchall()
                for nm_id, vendor_code in products_data_db:
                    vendor_codes[nm_id] = vendor_code or nm_id
        
        return [{"id": str(vendor_codes.get(str(a), a)), "name": f"товар {vendor_codes.get(str(a), a)}"} for a in articles]

async def get_reviews_summary_crud(
        db: AsyncSession,
        user_id: int,
        shop: str,
        brand_id: Optional[str],
        product_id: Optional[str],  # Изменено с int на str
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
            # Если product_id - это vendor_code, ищем соответствующий nm_id
            product_query = select(Product.nm_id).where(Product.vendor_code == product_id)
            product_result = await db.execute(product_query)
            product_data = product_result.scalars().first()
            
            if product_data:
                # Приводим nm_id к строке для сравнения с Feedback.article
                query = query.where(Feedback.article == str(product_data))
            else:
                print(f"[DEBUG] Товар с vendor_code '{product_id}' не найден")
        except Exception as e:
            print(f"[DEBUG] Ошибка при поиске товара по vendor_code '{product_id}': {e}")
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
    
    # Если нет отзывов, возвращаем пустой результат
    if total_reviews == 0:
        return {"total_reviews": 0, "by_day": []}
    
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
        
        # Подсчет отзывов по рейтингам (1, 2, 3, 4, 5)
        if str(f.rating) in metrics:
            by_day[d][str(f.rating)] += 1
    
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
            # Если product_id - это vendor_code, ищем соответствующий nm_id
            product_query = select(Product.nm_id).where(Product.vendor_code == product_id)
            product_result = await db.execute(product_query)
            product_data = product_result.scalars().first()
            
            if product_data:
                # Приводим nm_id к строке для сравнения с Feedback.article
                query = query.where(Feedback.article == str(product_data))
            else:
                print(f"[DEBUG] Товар с vendor_code '{product_id}' не найден")
        except Exception as e:
            print(f"[DEBUG] Ошибка при поиске товара по vendor_code '{product_id}': {e}")
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
            article = feedback.article
            if article not in products_data:
                products_data[article] = []
            products_data[article].append(feedback.rating)

        # Получаем vendor_code для всех артикулов
        vendor_codes = {}
        if products_data:
            # Преобразуем артикулы в строки для поиска в таблице products
            nm_ids = []
            for article_key in products_data.keys():
                try:
                    # Преобразуем в строку для поиска в Product.nm_id
                    nm_id_str = str(article_key)
                    nm_ids.append(nm_id_str)
                except (ValueError, TypeError):
                    continue
            
            if nm_ids:
                product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
                product_result = await db.execute(product_query)
                products_data_db = product_result.fetchall()
                for nm_id, vendor_code in products_data_db:
                    vendor_codes[nm_id] = vendor_code or nm_id

        top_products = []
        for article, ratings_list in products_data.items():
            avg_product_rating = sum(ratings_list) / len(ratings_list)
            vendor_code = vendor_codes.get(str(article), str(article))
            top_products.append({
                "name": f"товар {vendor_code}",
                "rating": round(avg_product_rating, 2)
            })

        top_products.sort(key=lambda x: x["rating"], reverse=True)
        tops = top_products[offset:offset+limit]
    return tops