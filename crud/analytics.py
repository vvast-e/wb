from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc, case, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.feedback import Feedback
from models.user import User
from models.product import Product

import logging
logger = logging.getLogger(__name__)


async def get_user_shopsList_crud(
        db: AsyncSession,
        user_id: int
) -> List[Dict[str, Any]]:
    """Получение списка магазинов (брендов) пользователя с статистикой"""
    query = select(Feedback.brand).distinct().where(Feedback.user_id == user_id)
    result = await db.execute(query)
    brands = result.scalars().all()

    shops = []
    for brand in brands:
        # Получаем статистику для каждого бренда
        stats_query = select(
            func.count(Feedback.id).label('total_reviews'),
            func.avg(Feedback.rating).label('avg_rating'),
            func.sum(Feedback.is_negative).label('negative_count')
        ).where(Feedback.brand == brand)

        stats_result = await db.execute(stats_query)
        stats = stats_result.first()

        shops.append({
            "id": brand,
            "name": brand,
            "status": "active",
            "total_reviews": stats.total_reviews or 0,
            "avg_rating": round(float(stats.avg_rating or 0), 2),
            "negative_count": stats.negative_count or 0
        })

    return shops


async def get_reviews_with_filters_crud(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        rating: Optional[int] = None,
        shop: Optional[str] = None,
        product: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        negative: Optional[bool] = None,
        deleted: Optional[bool] = None
) -> Dict[str, Any]:
    """Получение отзывов с расширенной фильтрацией"""
    offset = (page - 1) * per_page

    # Базовый запрос
    query = select(Feedback).where(Feedback.user_id == user_id)

    # Применяем фильтры
    if search:
        search_filter = or_(
            Feedback.text.ilike(f"%{search}%"),
            Feedback.main_text.ilike(f"%{search}%"),
            Feedback.pros_text.ilike(f"%{search}%"),
            Feedback.cons_text.ilike(f"%{search}%"),
            Feedback.author.ilike(f"%{search}%")
        )
        query = query.where(search_filter)

    if rating:
        query = query.where(Feedback.rating == rating)

    if shop:
        query = query.where(Feedback.brand == shop)

    if product:
        logger.debug(f"[DEBUG] ===== ФИЛЬТР ПО ТОВАРУ =====")
        logger.debug(f"[DEBUG] product: '{product}' (тип: {type(product)})")
        logger.debug(f"[DEBUG] shop: '{shop}' (тип: {type(shop)})")
        
        # Нормализация бренда для сравнения
        normalized_shop = shop.lower() if shop else ""
        if normalized_shop == "mona biolab":
            normalized_shop = "Mona Premium"
        logger.debug(f"[DEBUG] Нормализованный shop: '{normalized_shop}'")
        
        # Ищем товар по vendor_code и brand в таблице products
        logger.debug(f"[DEBUG] Ищем товар по vendor_code: '{product}' и brand: '{normalized_shop}'")
        product_query = select(Product.nm_id).where(
            and_(Product.vendor_code == product, func.lower(Product.brand) == normalized_shop)
        )
        logger.debug(f"[DEBUG] SQL запрос: {product_query}")
        product_result = await db.execute(product_query)
        product_data = product_result.scalars().first()
        logger.debug(f"[DEBUG] Найден nm_id: {product_data} (тип: {type(product_data)})")
        
        if product_data:
            # Преобразуем nm_id в int для сравнения с Feedback.article
            try:
                nm_id_int = int(product_data)
                logger.debug(f"[DEBUG] Преобразовали nm_id в int: {nm_id_int}")
                query = query.where(Feedback.article == str(nm_id_int))
                logger.debug(f"[DEBUG] Применяем фильтр по найденному nm_id: {nm_id_int}")
                logger.debug(f"[DEBUG] Итоговый запрос после фильтра: {query}")
            except (ValueError, TypeError) as e:
                logger.debug(f"[DEBUG] Ошибка преобразования nm_id '{product_data}' в int: {e}")
                logger.debug(f"[DEBUG] Пропускаем фильтр по товару для '{product}'")
        else:
            # Если товар не найден, не возвращаем пустой результат, просто не применяем фильтр
            logger.debug(f"[DEBUG] Товар с vendor_code '{product}' и brand '{normalized_shop}' не найден, пропускаем фильтр")
    else:
        logger.debug(f"[DEBUG] Фильтр по товару не применяется (product = {product})")

    if date_from:
        query = query.where(func.coalesce(Feedback.date, Feedback.created_at) >= date_from)

    if date_to:
        query = query.where(func.coalesce(Feedback.date, Feedback.created_at) <= date_to)

    if negative is not None:
        query = query.where(Feedback.is_negative == (1 if negative else 0))

    # Фильтрация по удалённости
    if deleted is not None:
        query = query.where(Feedback.is_deleted == deleted)

    # Получаем общее количество
    count_query = select(func.count()).select_from(query.subquery())
    logger.debug(f"[DEBUG] Запрос для подсчета: {count_query}")
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    logger.debug(f"[DEBUG] Общее количество записей: {total}")

    # Получаем отзывы с пагинацией
    final_query = query.order_by(desc(func.coalesce(Feedback.date, Feedback.created_at)), desc(Feedback.id)).offset(offset).limit(per_page)
    logger.debug(f"[DEBUG] Финальный запрос с пагинацией: {final_query}")
    result = await db.execute(final_query)
    feedbacks = result.scalars().all()
    logger.debug(f"[DEBUG] Получено отзывов: {len(feedbacks)}")

    # Формируем ответ
    reviews = []
    
    # Получаем vendor_code для всех товаров
    article_ids = [f.article for f in feedbacks if f.article]
    vendor_codes = {}
    if article_ids:
        # Преобразуем артикулы в строки для поиска в таблице products
        nm_ids = []
        for article_id in article_ids:
            try:
                # Преобразуем в строку для поиска в Product.nm_id
                nm_id_str = str(article_id)
                nm_ids.append(nm_id_str)
            except (ValueError, TypeError):
                continue
        
        if nm_ids:
            product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
            product_result = await db.execute(product_query)
            products_data_db = product_result.fetchall()
            for nm_id, vendor_code in products_data_db:
                # Используем nm_id как ключ для поиска
                vendor_codes[nm_id] = vendor_code or nm_id
    

    
    for feedback in feedbacks:
        # Определяем sentiment на основе рейтинга
        if feedback.rating >= 4:
            sentiment = "positive"
        elif feedback.rating <= 2:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        dt = feedback.date if feedback.date else feedback.created_at
        
        # Получаем vendor_code для товара
        article_str = str(feedback.article) if feedback.article else ""
        vendor_code = vendor_codes.get(article_str, article_str)
        
        # Логируем данные для отладки
        logger.debug(f"[DEBUG] Отзыв {feedback.id}: pros_text='{feedback.pros_text}', cons_text='{feedback.cons_text}', main_text='{feedback.main_text}'")
        
        reviews.append({
            "id": feedback.id,
            "main_text": feedback.main_text or "",
            "pros_text": feedback.pros_text or "",
            "cons_text": feedback.cons_text or "",
            "rating": feedback.rating,
            "author_name": feedback.author or "Аноним",
            "product_name": f"товар {vendor_code}",
            "shop_name": feedback.brand,
            "created_at": dt.isoformat() if dt else None,
            "photos": [],  # Пока нет фото в модели
            "sentiment": sentiment,
            "is_processed": bool(feedback.is_processed),
            "is_deleted": bool(getattr(feedback, "is_deleted", False))
        })

    return {
        "reviews": reviews,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


async def get_shop_data_crud(
        db: AsyncSession,
        user_id: int,
        shop_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
) -> Dict[str, Any]:
    """Получение данных магазина за период"""
    # Получаем все отзывы магазина
    query_all = select(Feedback).where(
        and_(Feedback.brand == shop_id, Feedback.user_id == user_id)
    )
    result_all = await db.execute(query_all)
    feedbacks_all = result_all.scalars().all()

    # Если фильтр по периоду
    if start_date or end_date:
        query_period = select(Feedback).where(
            and_(Feedback.brand == shop_id, Feedback.user_id == user_id)
        )
        if start_date:
            query_period = query_period.where(Feedback.date >= start_date)
        if end_date:
            query_period = query_period.where(Feedback.date <= end_date)
        result_period = await db.execute(query_period)
        feedbacks_period = result_period.scalars().all()
    else:
        feedbacks_period = feedbacks_all

    # --- market_rating_all_time ---
    def get_feedback_datetime(f):
        dt = getattr(f, 'date', None)
        if dt is None:
            dt = getattr(f, 'created_at', None)
        return dt if dt is not None else datetime.min
    feedbacks_all_sorted = sorted(feedbacks_all, key=get_feedback_datetime, reverse=True)
    valid_feedbacks_all = feedbacks_all_sorted[:20000]
    now = datetime.now()
    def get_decay(days):
        if days <= 0:
            return 1.0
        return 100 ** (-(days - 182) / (730 * 1.5))
    weighted_sum_all = 0.0
    decay_sum_all = 0.0
    for idx, f in enumerate(valid_feedbacks_all):
        dt = get_feedback_datetime(f)
        days = (now.date() - dt.date()).days
        decay = 1.0 if idx < 15 else get_decay(days)
        rating_val = getattr(f, 'rating', 0)
        if not isinstance(rating_val, (int, float)):
            rating_val = 0
        weighted_sum_all += rating_val * decay
        decay_sum_all += decay
    market_rating_all_time = (weighted_sum_all / decay_sum_all) if decay_sum_all > 0 else 0

    # --- market_rating_period ---
    feedbacks_period_sorted = sorted(feedbacks_period, key=get_feedback_datetime, reverse=True)
    valid_feedbacks_period = feedbacks_period_sorted[:20000]
    weighted_sum_period = 0.0
    decay_sum_period = 0.0
    for idx, f in enumerate(valid_feedbacks_period):
        dt = get_feedback_datetime(f)
        days = (now.date() - dt.date()).days
        decay = 1.0 if idx < 15 else get_decay(days)
        rating_val = getattr(f, 'rating', 0)
        if not isinstance(rating_val, (int, float)):
            rating_val = 0
        weighted_sum_period += rating_val * decay
        decay_sum_period += decay
    market_rating_period = (weighted_sum_period / decay_sum_period) if decay_sum_period > 0 else 0

    # --- average_rating_period ---
    ratings_period = [f.rating for f in feedbacks_period if hasattr(f, 'rating') and isinstance(f.rating, (int, float))]
    average_rating_period = sum(ratings_period) / len(ratings_period) if ratings_period else 0

    # --- Остальная статистика (оставляем как есть, берем из feedbacks_period) ---
    total_reviews = len(feedbacks_period)
    negative_reviews = sum(1 for f in feedbacks_period if hasattr(f, 'is_negative') and f.is_negative is not None and int(f.is_negative) == 1)
    five_star_reviews = sum(1 for f in feedbacks_period if hasattr(f, 'rating') and f.rating == 5)

    products_data = {}
    for f in feedbacks_period:
        article = getattr(f, 'article', None)
        if article is None or isinstance(article, type(Feedback.article)):
            try:
                article = int(getattr(f, 'article', 0))
            except Exception:
                continue
        article_key = str(article)
        if article_key not in products_data:
            products_data[article_key] = {"ratings": [], "feedbacks": [], "negative_count": 0}
        rating_val = getattr(f, 'rating', None)
        if rating_val is not None:
            products_data[article_key]["ratings"].append(rating_val)
        products_data[article_key]["feedbacks"].append(f)
        is_neg = getattr(f, 'is_negative', None)
        if is_neg is not None and (isinstance(is_neg, bool) or isinstance(is_neg, int)) and int(is_neg) == 1:
            products_data[article_key]["negative_count"] += 1

    # --- Собираем all-time данные по товарам ---
    products_data_all_time = {}
    for f in feedbacks_all:
        article = getattr(f, 'article', None)
        if article is None or isinstance(article, type(Feedback.article)):
            try:
                article = int(getattr(f, 'article', 0))
            except Exception:
                continue
        article_key = str(article)
        if article_key not in products_data_all_time:
            products_data_all_time[article_key] = {"ratings": [], "feedbacks": [], "negative_count": 0}
        rating_val = getattr(f, 'rating', None)
        if rating_val is not None:
            products_data_all_time[article_key]["ratings"].append(rating_val)
        products_data_all_time[article_key]["feedbacks"].append(f)
        is_neg = getattr(f, 'is_negative', None)
        if is_neg is not None and (isinstance(is_neg, bool) or isinstance(is_neg, int)) and int(is_neg) == 1:
            products_data_all_time[article_key]["negative_count"] += 1

    products = []
    all_keys = set()
    if products_data_all_time:
        all_keys.update(products_data_all_time.keys())
    if products_data:
        all_keys.update(products_data.keys())
    
    # Получаем vendor_code для всех товаров
    vendor_codes = {}
    if all_keys:
        # Преобразуем строковые артикулы в целые числа
        nm_ids = []
        for article_key in all_keys:
            try:
                nm_id = int(article_key)
                nm_ids.append(str(nm_id))
            except (ValueError, TypeError):
                continue
        
        if nm_ids:
            product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
            product_result = await db.execute(product_query)
            products_data_db = product_result.fetchall()
            for nm_id, vendor_code in products_data_db:
                vendor_codes[str(nm_id)] = vendor_code or str(nm_id)
    
    for article_key in all_keys:
        # Получаем vendor_code для товара
        vendor_code = vendor_codes.get(article_key, article_key)
        
        # All-time рейтинги
        data_all = products_data_all_time.get(article_key) or {"ratings": [], "feedbacks": [], "negative_count": 0}
        ratings_all = [r for r in data_all.get("ratings", []) if r is not None]
        product_avg_all = sum(ratings_all) / len(ratings_all) if ratings_all else 0
        valid_fb_all = [f for f in data_all.get("feedbacks", []) if get_feedback_datetime(f) >= now - timedelta(days=730)]
        valid_fb_all.sort(key=get_feedback_datetime, reverse=True)
        valid_fb_all = valid_fb_all[:20000]
        weighted_sum_all = 0.0
        decay_sum_all = 0.0
        for idx, f in enumerate(valid_fb_all):
            dt = get_feedback_datetime(f)
            days = (now.date() - dt.date()).days
            decay = 1.0 if idx < 15 else get_decay(days)
            rating_val = getattr(f, 'rating', 0)
            if not isinstance(rating_val, (int, float)):
                rating_val = 0
            weighted_sum_all += rating_val * decay
            decay_sum_all += decay
        product_market_rating_all = (weighted_sum_all / decay_sum_all) if decay_sum_all > 0 else 0
        # Только period негатив и счетчики
        data_period = products_data.get(article_key) or {"ratings": [], "feedbacks": [], "negative_count": 0}
        ratings_period = [r for r in data_period.get("ratings", []) if r is not None]
        product_avg_period = sum(ratings_period) / len(ratings_period) if ratings_period else 0
        valid_fb_period = [f for f in data_period.get("feedbacks", []) if get_feedback_datetime(f) >= now - timedelta(days=730)]
        valid_fb_period.sort(key=get_feedback_datetime, reverse=True)
        valid_fb_period = valid_fb_period[:20000]
        weighted_sum_period = 0.0
        decay_sum_period = 0.0
        for idx, f in enumerate(valid_fb_period):
            dt = get_feedback_datetime(f)
            days = (now.date() - dt.date()).days
            decay = 1.0 if idx < 15 else get_decay(days)
            rating_val = getattr(f, 'rating', 0)
            if not isinstance(rating_val, (int, float)):
                rating_val = 0
            weighted_sum_period += rating_val * decay
            decay_sum_period += decay
        product_market_rating_period = (weighted_sum_period / decay_sum_period) if decay_sum_period > 0 else 0
        negative_count_period = data_period.get("negative_count", 0)
        total_reviews_period = len(ratings_period)
        internal_negative_percentage_period = round((negative_count_period / total_reviews_period) * 100, 1) if total_reviews_period > 0 else 0.0
        ratings_count_period = {
            "5": sum(1 for r in ratings_period if r == 5),
            "4": sum(1 for r in ratings_period if r == 4),
            "3": sum(1 for r in ratings_period if r == 3),
            "2": sum(1 for r in ratings_period if r == 2),
            "1": sum(1 for r in ratings_period if r == 1)
        }
        products.append({
            "article": article_key,
            "vendor_code": vendor_code,
            "name": f"товар {vendor_code}",
            "market_rating_all_time": round(product_market_rating_all, 2),
            "market_rating": round(product_market_rating_period, 2),
            "rating_all_time": round(product_avg_all, 2),
            "rating": round(product_avg_period, 2),
            "internal_negative_percentage": internal_negative_percentage_period,
            "total_reviews": total_reviews_period,
            "ratings_count": ratings_count_period,
            "five_stars_before_upgrade": "Заглушка"
        })
    products.sort(key=lambda x: x["market_rating_all_time"], reverse=True)

    negative_tops = []
    for article_key, data in products_data.items():
        if data["negative_count"] > 0:
            vendor_code = vendor_codes.get(article_key, article_key)
            negative_tops.append({
                "product_name": f"товар {vendor_code}",
                "negative_count": data["negative_count"]
            })
    negative_tops.sort(key=lambda x: x["negative_count"], reverse=True)

    # Подсчитываем общий негатив всех товаров
    total_negative_all_products = sum(data["negative_count"] for data in products_data.values())
    
    negative_percentage_tops = []
    internal_negative_tops = []
    for article_key, data in products_data.items():
        total_product_reviews = len([r for r in data["ratings"] if r is not None])
        vendor_code = vendor_codes.get(article_key, article_key)
        
        # Доля негатива внутри товара (негатив товара / все отзывы товара)
        if total_product_reviews > 0:
            internal_negative_percentage = (data["negative_count"] / total_product_reviews) * 100
            internal_negative_tops.append({
                "product_name": f"товар {vendor_code}",
                "internal_negative_percentage": round(internal_negative_percentage, 1)
            })
        
        # Доля негативных от всех отзывов (негатив товара / общий негатив всех товаров)
        if total_negative_all_products > 0:
            negative_percentage = (data["negative_count"] / total_negative_all_products) * 100
            negative_percentage_tops.append({
                "product_name": f"товар {vendor_code}",
                "negative_percentage": round(negative_percentage, 1)
            })
    
    negative_percentage_tops.sort(key=lambda x: x["negative_percentage"], reverse=True)
    internal_negative_tops.sort(key=lambda x: x["internal_negative_percentage"], reverse=True)

    return {
        "market_rating_all_time": round(market_rating_all_time, 2),
        "market_rating_period": round(market_rating_period, 2),
        "average_rating_period": round(average_rating_period, 2),
        "total_reviews": total_reviews,
        "negative_reviews": negative_reviews,
        "five_star_reviews": five_star_reviews,
        "products": products[:10],
        "negative_tops": negative_tops[:10],
        "negative_percentage_tops": negative_percentage_tops[:10],
        "internal_negative_tops": internal_negative_tops[:10]
    }


async def get_shop_products_crud(
        db: AsyncSession,
        user_id: int,
        shop_id: str
) -> List[Dict[str, Any]]:
    """Получение товаров магазина с расчетом рейтингов за весь период"""
    query = select(Feedback.article).distinct().where(
        and_(
            Feedback.brand == shop_id,
            Feedback.user_id == user_id
        )
    )

    result = await db.execute(query)
    articles = result.scalars().all()

    products = []
    for article in articles:
        # Получаем все отзывы по товару за весь период
        feedbacks_query = select(Feedback).where(
            and_(
                Feedback.article == article,
                Feedback.brand == shop_id,
                Feedback.user_id == user_id
            )
        )
        feedbacks_result = await db.execute(feedbacks_query)
        feedbacks = feedbacks_result.scalars().all()
        # average_rating
        ratings = [f.rating for f in feedbacks if hasattr(f, 'rating') and isinstance(f.rating, (int, float))]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        # market_rating
        def get_feedback_datetime(f):
            dt = getattr(f, 'date', None)
            if dt is None:
                dt = getattr(f, 'created_at', None)
            return dt if dt is not None else datetime.min
        feedbacks_sorted = sorted(feedbacks, key=get_feedback_datetime, reverse=True)
        valid_feedbacks = feedbacks_sorted[:20000]  # только последние 20 000, если их больше
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
        # Корректно формируем id и name
        article_id = str(article) if not hasattr(article, 'key') else str(getattr(article, 'key', ''))
        
        # Получаем vendor_code для товара
        try:
            nm_id = int(article)
            product_query = select(Product.vendor_code).where(Product.nm_id == str(nm_id))
            product_result = await db.execute(product_query)
            product_data = product_result.scalars().first()  # Исправлено: используем scalars().first()
            vendor_code = product_data or article_id
        except (ValueError, TypeError):
            vendor_code = article_id
        
        products.append({
            "id": vendor_code,
            "name": f"товар {vendor_code}",
            "rating": round(float(avg_rating), 2),
            "market_rating": round(float(market_rating), 2)
        })
    products.sort(key=lambda x: x["market_rating"], reverse=True)
    return products


async def get_efficiency_data_crud(
        db: AsyncSession,
        user_id: int,
        shop_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_id: Optional[str] = None
) -> Dict[str, Any]:
    """Получение данных эффективности отдела репутации"""
    from datetime import datetime, timedelta
    
    # Базовый запрос
    query = select(Feedback).where(
        and_(
            Feedback.brand == shop_id,
            Feedback.user_id == user_id
        )
    )

    if start_date:
        query = query.where(Feedback.date >= start_date)
    if end_date:
        query = query.where(Feedback.date <= end_date)
    if product_id:
        # Нормализация бренда для сравнения
        normalized_shop = shop_id.lower() if shop_id else ""
        if normalized_shop == "mona biolab":
            normalized_shop = "mona premium"
        logger.debug(f"[DEBUG] Нормализованный shop: '{normalized_shop}'")
        
        # Ищем товар по vendor_code и brand в таблице products
        logger.debug(f"[DEBUG] Ищем товар по vendor_code: '{product_id}' и brand: '{normalized_shop}'")
        product_query = select(Product.nm_id).where(
            and_(Product.vendor_code == product_id, func.lower(Product.brand) == normalized_shop)
        )
        product_result = await db.execute(product_query)
        product_data = product_result.scalars().first()
        logger.debug(f"[DEBUG] Найден nm_id: {product_data}")
        
        if product_data:
            # Преобразуем nm_id в int для сравнения с Feedback.article
            try:
                nm_id_int = int(product_data)
                query = query.where(Feedback.article == str(nm_id_int))
                logger.debug(f"[DEBUG] Применяем фильтр по найденному nm_id: {nm_id_int}")
            except (ValueError, TypeError):
                logger.debug(f"[DEBUG] Не удалось преобразовать nm_id '{product_data}' в int")
                logger.debug(f"[DEBUG] Пропускаем фильтр по товару для '{product_id}'")
        else:
            # Если товар не найден, не возвращаем пустой результат, просто не применяем фильтр
            logger.debug(f"[DEBUG] Товар с vendor_code '{product_id}' и brand '{normalized_shop}' не найден, пропускаем фильтр")

    result = await db.execute(query)
    feedbacks = result.scalars().all()

    if not feedbacks:
        return None

    # 1. Базовая статистика
    total_reviews = len(feedbacks)
    negative_count = sum(1 for f in feedbacks if f.is_negative)
    deleted_count = sum(1 for f in feedbacks if getattr(f, 'is_deleted', False))

    # 2. Расчет времени пребывания негатива в ТОПе
    def calculate_top_time(feedbacks_list):
        """Рассчитывает среднее время пребывания негатива в ТОПе"""
        if not feedbacks_list:
            return {
                "top_1": 0, "top_3": 0, "top_5": 0, "top_10": 0
            }
        
        # Сортируем отзывы по дате (новые сверху)
        sorted_feedbacks = sorted(feedbacks_list, key=lambda x: x.date or x.created_at, reverse=True)
        
        top_times = {"top_1": [], "top_3": [], "top_5": [], "top_10": []}
        now = datetime.now()
        
        for i, negative_feedback in enumerate(sorted_feedbacks):
            if not negative_feedback.is_negative:
                continue
                
            negative_date = negative_feedback.date or negative_feedback.created_at
            if not negative_date:
                continue
            
            # Ищем следующий положительный отзыв (рейтинг 4-5) после негативного
            next_positive_date = None
            for j in range(i + 1, len(sorted_feedbacks)):
                if sorted_feedbacks[j].rating >= 4:
                    next_positive_date = sorted_feedbacks[j].date or sorted_feedbacks[j].created_at
                    break
            
            # Если нет следующего положительного, считаем до текущего момента
            if not next_positive_date:
                next_positive_date = now
            
            # Рассчитываем время пребывания в каждом ТОПе
            time_diff = next_positive_date - negative_date
            hours = time_diff.total_seconds() / 3600
            
            # Определяем позицию в ТОПе на момент негативного отзыва
            position = i + 1  # Позиция в отсортированном списке
            
            if position <= 1:
                top_times["top_1"].append(hours)
            if position <= 3:
                top_times["top_3"].append(hours)
            if position <= 5:
                top_times["top_5"].append(hours)
            if position <= 10:
                top_times["top_10"].append(hours)
        
        # Вычисляем средние значения
        result = {}
        for top_key in top_times:
            values = top_times[top_key]
            if values:
                avg_hours = sum(values) / len(values)
                hours_int = int(avg_hours)
                minutes = int((avg_hours - hours_int) * 60)
                result[top_key] = f"{hours_int}ч {minutes:02d}мин"
            else:
                result[top_key] = "0ч 00мин"
        
        return result
    
    # 3. Расчет среднего времени удаления негатива
    def calculate_deletion_time(feedbacks_list):
        """Рассчитывает среднее время удаления негатива"""
        negative_feedbacks = [f for f in feedbacks_list if f.is_negative and f.is_deleted]
        
        if not negative_feedbacks:
            return "0ч 00мин"
        
        total_hours = 0
        count = 0
        
        for feedback in negative_feedbacks:
            if feedback.date and feedback.deleted_at:
                time_diff = feedback.deleted_at - feedback.date
                total_hours += time_diff.total_seconds() / 3600
                count += 1
        
        if count == 0:
            return "0ч 00мин"
        
        avg_hours = total_hours / count
        hours_int = int(avg_hours)
        minutes = int((avg_hours - hours_int) * 60)
        return f"{hours_int}ч {minutes:02d}мин"
    
    # Выполняем расчеты
    top_times = calculate_top_time(feedbacks)
    deletion_time = calculate_deletion_time(feedbacks)
    
    # Дополнительная статистика
    processed_count = sum(1 for f in feedbacks if f.is_processed)
    pending_count = total_reviews - processed_count
    
    # Распределение рейтингов
    ratings_distribution = {}
    for rating in range(1, 6):
        ratings_distribution[f"rating_{rating}"] = sum(1 for f in feedbacks if f.rating == rating)
    
    # 4. Формируем данные для графика (тренды по дням)
    def generate_trends_data(feedbacks_list, start_date, end_date):
        """Генерирует данные для графиков по дням"""
        if not start_date or not end_date:
            return []
        
        trends = []
        current_date = start_date
        
        while current_date <= end_date:
            day_feedbacks = [f for f in feedbacks_list 
                           if f.date and f.date.date() == current_date]
            
            day_negative = sum(1 for f in day_feedbacks if f.is_negative)
            day_deleted = sum(1 for f in day_feedbacks if f.is_deleted)
            
            trends.append({
                "date": current_date.strftime("%d.%m"),
                "total": len(day_feedbacks),
                "negative": day_negative,
                "deleted": day_deleted,
                "negative_percent": round((day_negative / len(day_feedbacks) * 100) if day_feedbacks else 0, 1),
                "deleted_percent": round((day_deleted / len(day_feedbacks) * 100) if day_feedbacks else 0, 1)
            })
            
            current_date += timedelta(days=1)
        
        return trends
    
    trends_data = generate_trends_data(feedbacks, start_date, end_date) if start_date and end_date else []

    return {
        # Базовая статистика
        "total_reviews": total_reviews,
        "negative_count": negative_count,
        "deleted_count": deleted_count,
        "processed_count": processed_count,
        "pending_count": pending_count,
        
        # Время пребывания в ТОПе
        "top_1_time": top_times["top_1"],
        "top_3_time": top_times["top_3"],
        "top_5_time": top_times["top_5"],
        "top_10_time": top_times["top_10"],
        
        # Время удаления
        "deletion_time": deletion_time,
        
        # Распределение рейтингов
        "ratings_distribution": ratings_distribution,
        
        # Данные для графиков
        "trends": trends_data
    }


async def get_shops_summary_crud(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Получение сводки по магазинам"""
    # Получаем все бренды пользователя
    brands_query = select(Feedback.brand).distinct().where(Feedback.user_id == user_id)
    brands_result = await db.execute(brands_query)
    brands = brands_result.scalars().all()

    summary = []
    for brand in brands:
        # Базовый запрос для бренда
        query = select(Feedback).where(
            and_(
                Feedback.brand == brand,
                Feedback.user_id == user_id
            )
        )

        if start_date:
            query = query.where(Feedback.date >= start_date)
        if end_date:
            query = query.where(Feedback.date <= end_date)

        result = await db.execute(query)
        feedbacks = result.scalars().all()

        if not feedbacks:
            continue

        # Подсчитываем статистику
        total_reviews = len(feedbacks)
        ratings = [f.rating for f in feedbacks]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        negative_reviews = sum(1 for f in feedbacks if f.is_negative)
        five_star_reviews = sum(1 for f in feedbacks if f.rating == 5)

        negative_percentage = (negative_reviews / total_reviews) * 100 if total_reviews > 0 else 0
        five_star_percentage = (five_star_reviews / total_reviews) * 100 if total_reviews > 0 else 0

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
            # Преобразуем строковые артикулы в целые числа
            nm_ids = []
            for article_key in products_data.keys():
                try:
                    nm_id = int(article_key)
                    nm_ids.append(str(nm_id))
                except (ValueError, TypeError):
                    continue
            
            if nm_ids:
                product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
                product_result = await db.execute(product_query)
                products_data_db = product_result.fetchall()
                for nm_id, vendor_code in products_data_db:
                    vendor_codes[nm_id] = vendor_code or str(nm_id)

        top_products = []
        for article, ratings_list in products_data.items():
            avg_product_rating = sum(ratings_list) / len(ratings_list)
            vendor_code = vendor_codes.get(article, str(article))
            top_products.append({
                "name": f"товар {vendor_code}",
                "rating": round(avg_product_rating, 2)
            })

        top_products.sort(key=lambda x: x["rating"], reverse=True)

        summary.append({
            "id": brand,
            "name": brand,
            "total_reviews": total_reviews,
            "average_rating": round(avg_rating, 3),
            "negative_reviews": negative_reviews,
            "five_star_reviews": five_star_reviews,
            "negative_percentage": round(negative_percentage, 2),
            "five_star_percentage": round(five_star_percentage, 2),
            "status": "active",
            "is_processing": False,  # Пока заглушка
            "top_products": top_products[:5]  # Топ 5
        })

    # Сортируем по общему количеству отзывов
    summary.sort(key=lambda x: x["total_reviews"], reverse=True)

    return summary


async def parse_shop_feedbacks_crud(
        db: AsyncSession,
        user_id: int,
        shop_id: str,
        max_count_per_product: int = 1000,
        save_to_db: bool = True
) -> Dict[str, Any]:
    """Массовый парсинг отзывов всех товаров магазина с поддержкой soft delete"""
    from crud.user import get_decrypted_wb_key
    from utils.wb_api import WBAPIClient
    from utils.wb_nodriver_parser import parse_feedbacks_optimized
    from crud.feedback import sync_feedbacks_with_soft_delete_optimized
    from models.user import User
    import logging

    logger = logging.getLogger("parse_shop_feedbacks")
    logger.setLevel(logging.INFO)
    
    logger.info(f"[PARSE] Начинаем парсинг отзывов для магазина: {shop_id}")
    logger.info(f"[PARSE] user_id: {user_id}, max_count_per_product: {max_count_per_product}, save_to_db: {save_to_db}")

    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user or not user.wb_api_key or shop_id not in user.wb_api_key:
        error_msg = f"API ключ для бренда '{shop_id}' не найден"
        logger.error(f"[PARSE] ОШИБКА: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    try:
        # Получаем API ключ для бренда
        logger.info(f"[PARSE] Получаем API ключ для бренда {shop_id}...")
        wb_api_key = await get_decrypted_wb_key(db, user, shop_id)
        logger.info(f"[PARSE] API ключ получен успешно")

        # Получаем список товаров бренда
        logger.info(f"[PARSE] Получаем список товаров бренда {shop_id}...")
        wb_client = WBAPIClient(api_key=wb_api_key)
        items_result = await wb_client.get_cards_list()

        if not items_result.success:
            error_msg = f"Не удалось получить товары бренда: {items_result.error}"
            logger.error(f"[PARSE] ОШИБКА: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

        items = items_result.data.get("cards", [])
        logger.info(f"[PARSE] Получено товаров: {len(items)}")
        
        if not items:
            error_msg = "Товары не найдены"
            logger.error(f"[PARSE] ОШИБКА: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

        # Выводим первые несколько товаров для отладки
        logger.info(f"[PARSE] Первые 3 товара:")
        for i, item in enumerate(items[:3]):
            logger.info(f"  {i+1}. nmID: {item.get('nmID')}, vendorCode: {item.get('vendorCode')}, brand: {item.get('brand')}")

        # Статистика парсинга
        total_products = len(items)
        successful_products = 0
        failed_products = 0
        total_feedbacks = 0
        total_new_feedbacks = 0
        total_restored_feedbacks = 0
        total_deleted_feedbacks = 0

        results = []
        all_feedbacks_data = []  # Собираем все отзывы

        # Парсим отзывы для каждого товара
        for i, item in enumerate(items):
            nm_id = item.get("nmID")
            vendor_code = item.get("vendorCode", "")

            logger.info(f"[PARSE] Обрабатываем товар {i+1}/{total_products}: nmID={nm_id}, vendorCode={vendor_code}")

            if not nm_id:
                failed_products += 1
                logger.error(f"[PARSE] Пропущен товар {i+1}: nmID не найден")
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": False,
                    "error": "nmID не найден"
                })
                continue

            try:
                # Парсим отзывы для товара
                logger.info(f"[PARSE] Парсим отзывы для товара nmID={nm_id}...")
                feedbacks_data = await parse_feedbacks_optimized(
                    nm_id,
                    max_count_per_product
                )

                if feedbacks_data is None:
                    failed_products += 1
                    logger.error(f"[PARSE] Ошибка парсинга для товара nmID={nm_id}")
                    results.append({
                        "nm_id": nm_id,
                        "vendor_code": vendor_code,
                        "success": False,
                        "error": "Ошибка парсинга"
                    })
                    continue

                logger.info(f"[PARSE] Найдено отзывов для товара nmID={nm_id}: {len(feedbacks_data)}")

                # Добавляем артикул к каждому отзыву
                for feedback in feedbacks_data:
                    feedback['article'] = nm_id

                total_feedbacks += len(feedbacks_data)
                all_feedbacks_data.extend(feedbacks_data)  # Добавляем к общему списку

                successful_products += 1
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": True,
                    "parsed_count": len(feedbacks_data)
                })

            except Exception as e:
                failed_products += 1
                logger.error(f"[PARSE] Исключение при обработке товара nmID={nm_id}: {e}")
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": False,
                    "error": str(e)
                })

        # Синхронизируем все отзывы один раз для всего бренда
        if save_to_db and all_feedbacks_data:
            # Дедупликация отзывов по wb_id
            unique_feedbacks = {}
            for feedback in all_feedbacks_data:
                wb_id = feedback.get('id') or feedback.get('wb_id')
                if wb_id and wb_id not in unique_feedbacks:
                    unique_feedbacks[wb_id] = feedback
            
            deduplicated_feedbacks = list(unique_feedbacks.values())
            logger.info(f"[PARSE] Дедупликация: было {len(all_feedbacks_data)}, стало {len(deduplicated_feedbacks)}")
            
            logger.info(f"[PARSE] Синхронизируем все {len(deduplicated_feedbacks)} отзывов для бренда {shop_id}...")
            sync_stats = await sync_feedbacks_with_soft_delete_optimized(
                db=db,
                feedbacks_from_wb=deduplicated_feedbacks,
                brand=shop_id,
                user_id=user_id
            )
            
            total_new_feedbacks = sync_stats['new_feedbacks']
            total_restored_feedbacks = sync_stats['restored_feedbacks']
            total_deleted_feedbacks = sync_stats['deleted_feedbacks']
            
            logger.info(f"[PARSE] Итоговая статистика синхронизации:")
            logger.info(f"  Новых: {total_new_feedbacks}")
            logger.info(f"  Восстановленных: {total_restored_feedbacks}")
            logger.info(f"  Удаленных: {total_deleted_feedbacks}")
        elif not all_feedbacks_data:
            logger.info(f"[PARSE] Нет отзывов для сохранения в БД")

        logger.info(f"[PARSE] ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"  Всего товаров: {total_products}")
        logger.info(f"  Успешно обработано: {successful_products}")
        logger.info(f"  Ошибок: {failed_products}")
        logger.info(f"  Всего отзывов: {total_feedbacks}")
        logger.info(f"  Новых отзывов: {total_new_feedbacks}")
        logger.info(f"  Восстановленных отзывов: {total_restored_feedbacks}")
        logger.info(f"  Удаленных отзывов: {total_deleted_feedbacks}")

        return {
            "success": True,
            "shop_id": shop_id,
            "total_products": total_products,
            "successful_products": successful_products,
            "failed_products": failed_products,
            "total_feedbacks": total_feedbacks,
            "total_new_feedbacks": total_new_feedbacks,
            "total_restored_feedbacks": total_restored_feedbacks,
            "total_deleted_feedbacks": total_deleted_feedbacks,
            "results": results
        }

    except Exception as e:
        error_msg = f"Ошибка массового парсинга: {str(e)}"
        logger.critical(f"[PARSE] КРИТИЧЕСКАЯ ОШИБКА: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        } 