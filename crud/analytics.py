from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc, case, literal_column, text
from models.feedback import Feedback, FeedbackTopTracking
import asyncio

import logging
logger = logging.getLogger(__name__)

# Маппинг брендов убран - используем исходные названия напрямую




async def get_user_shopsList_crud(
        db: AsyncSession,
        user_id: int
) -> List[Dict[str, Any]]:
    """Получение списка всех доступных магазинов (брендов) с статистикой"""
    query = select(Feedback.brand).distinct()  # Убираем фильтр по user_id
    result = await db.execute(query)
    brands = result.scalars().all()

    shops = []
    for brand in brands:
        # Получаем статистику для каждого бренда - убираем фильтр по user_id
        stats_query = select(
            func.count(Feedback.id).label('total_reviews'),
            func.avg(Feedback.rating).label('avg_rating'),
            func.sum(Feedback.is_negative).label('negative_count')
        ).where(Feedback.brand == brand)  # Оставляем только фильтр по бренду

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

    # Базовый запрос - убираем фильтр по user_id, чтобы все отзывы были доступны всем
    query = select(Feedback)

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
        
        # Ищем товар по vendor_code в feedbacks
        logger.debug(f"[DEBUG] Ищем товар по vendor_code: '{product}' и brand: '{normalized_shop}'")
        # Просто фильтруем по vendor_code в feedbacks
        query = query.where(Feedback.vendor_code == product)
        logger.debug(f"[DEBUG] Применяем фильтр по vendor_code: {product}")
        logger.debug(f"[DEBUG] Итоговый запрос после фильтра: {query}")
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
        # Получаем vendor_code из feedbacks по nm_id (article)
        for article_id in article_ids:
            article_str = str(article_id)
            # Ищем vendor_code в feedbacks - убираем фильтр по user_id
            vendor_code_query = select(Feedback.vendor_code).where(
                Feedback.article == article_str
            ).limit(1)
            vendor_code_result = await db.execute(vendor_code_query)
            vendor_code = vendor_code_result.scalar()
            vendor_codes[article_str] = vendor_code or article_str
    

    
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
    # Получаем все отзывы магазина - убираем фильтр по user_id
    query_all = select(Feedback).where(Feedback.brand == shop_id)
    result_all = await db.execute(query_all)
    feedbacks_all = result_all.scalars().all()

    # Если фильтр по периоду
    if start_date or end_date:
        query_period = select(Feedback).where(Feedback.brand == shop_id)
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
        # Получаем vendor_code из feedbacks по nm_id (article)
        for article_key in all_keys:
            try:
                nm_id = int(article_key)
                nm_id_str = str(nm_id)
                # Ищем vendor_code в feedbacks
                vendor_code_query = select(Feedback.vendor_code).where(
                    and_(
                        Feedback.user_id == user_id,
                        Feedback.article == nm_id_str
                    )
                ).limit(1)
                vendor_code_result = await db.execute(vendor_code_query)
                vendor_code = vendor_code_result.scalar()
                vendor_codes[article_key] = vendor_code or article_key
            except (ValueError, TypeError):
                vendor_codes[article_key] = article_key
    
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
    """Получение активных товаров магазина (с отзывами за последние 6 месяцев)"""
    from models.product import Product  # Добавляем импорт
    import logging
    
    logger = logging.getLogger("shop_products")
    logger.info(f"[SHOP_PRODUCTS] Запрос активных товаров для shop_id={shop_id}, user_id={user_id}")
    
    # Вычисляем дату 6 месяцев назад
    six_months_ago = datetime.now() - timedelta(days=180)
    logger.info(f"[SHOP_PRODUCTS] Фильтруем отзывы за последние 6 месяцев (с {six_months_ago.strftime('%Y-%m-%d')})")
    
    # Получаем уникальные артикулы с отзывами за последние 6 месяцев
    query = select(Feedback.article).distinct().where(
        and_(
            Feedback.brand == shop_id,
            Feedback.user_id == user_id,
            Feedback.is_deleted == False,
            # Отзывы за последние 6 месяцев
            or_(
                Feedback.date >= six_months_ago,
                Feedback.created_at >= six_months_ago
            )
        )
    )

    result = await db.execute(query)
    articles = result.scalars().all()
    logger.info(f"[SHOP_PRODUCTS] Найдено уникальных артикулов: {len(articles)}")

    products = []
    for article in articles:
        logger.info(f"[SHOP_PRODUCTS] Обрабатываем артикул: {article}")
        
        # Получаем активные отзывы по товару за последние 6 месяцев
        feedbacks_query = select(Feedback).where(
            and_(
                Feedback.article == article,
                Feedback.brand == shop_id,
                Feedback.user_id == user_id,
                Feedback.is_deleted == False,
                # Отзывы за последние 6 месяцев
                or_(
                    Feedback.date >= six_months_ago,
                    Feedback.created_at >= six_months_ago
                )
            )
        )
        feedbacks_result = await db.execute(feedbacks_query)
        feedbacks = feedbacks_result.scalars().all()
        logger.info(f"[SHOP_PRODUCTS] Для артикула {article} найдено активных отзывов: {len(feedbacks)}")
        
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
            # Ищем vendor_code в feedbacks по nm_id (article) - убираем фильтр по user_id
            vendor_code_query = select(Feedback.vendor_code).where(
                and_(
                    Feedback.brand == shop_id,
                    Feedback.article == str(nm_id)
                )
            ).limit(1)
            vendor_code_result = await db.execute(vendor_code_query)
            vendor_code = vendor_code_result.scalar() or article_id
            logger.info(f"[SHOP_PRODUCTS] Для nm_id {nm_id} найден vendor_code: {vendor_code}")
        except (ValueError, TypeError):
            vendor_code = article_id
            logger.info(f"[SHOP_PRODUCTS] Не удалось преобразовать {article} в int, используем как есть: {vendor_code}")
        
        product_info = {
            "id": vendor_code,  # Возвращаем vendor_code как id для фронтенда
            "nm_id": article_id,  # Добавляем nm_id для внутреннего использования
            "name": f"товар {vendor_code}",
            "rating": round(float(avg_rating), 2),
            "market_rating": round(float(market_rating), 2),
            "active_reviews_count": len(feedbacks)  # Добавляем количество активных отзывов
        }
        
        logger.info(f"[SHOP_PRODUCTS] Добавляем товар: {product_info}")
        products.append(product_info)
    
    products.sort(key=lambda x: x["market_rating"], reverse=True)
    logger.info(f"[SHOP_PRODUCTS] Итого активных товаров (с отзывами за 6 мес): {len(products)}")
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
    from models.feedback import Feedback, FeedbackTopTracking
    from sqlalchemy import func, and_, or_
    import logging
    
    logger = logging.getLogger("efficiency_data")
    logger.info(f"[EFFICIENCY] Запрос данных для shop_id={shop_id}, product_id={product_id}, user_id={user_id}")
    
    # Базовый запрос для отзывов - убираем фильтр по user_id
    query = select(Feedback).where(Feedback.brand == shop_id)
    
    if start_date:
        query = query.where(Feedback.date >= start_date)
        logger.info(f"[EFFICIENCY] Добавлен фильтр по start_date: {start_date}")
    if end_date:
        query = query.where(Feedback.date <= end_date)
        logger.info(f"[EFFICIENCY] Добавлен фильтр по end_date: {end_date}")
    
    # Фильтр по товару - простое сравнение по vendor_code
    if product_id:
        logger.info(f"[EFFICIENCY] Фильтруем по vendor_code: {product_id}")
        query = query.where(Feedback.vendor_code == product_id)
    else:
        logger.info(f"[EFFICIENCY] Фильтр по товару не применяется")
    
    # Получаем отзывы
    logger.info(f"[EFFICIENCY] Выполняем запрос: {query}")
    result = await db.execute(query)
    feedbacks = result.scalars().all()
    logger.info(f"[EFFICIENCY] Найдено отзывов: {len(feedbacks)}")
    
    if not feedbacks:
        logger.info(f"[EFFICIENCY] Отзывы не найдены, возвращаем пустой результат")
        return {
            "total_reviews": 0,
            "negative_count": 0,
            "deleted_count": 0,
            "ratings_distribution": {},
            "top_1_time": "00:00:00",
            "top_3_time": "00:00:00", 
            "top_5_time": "00:00:00",
            "top_10_time": "00:00:00",
            "deletion_time": "00:00:00",
            "trends": []
        }
    
    # Базовая статистика
    total_reviews = len(feedbacks)
    negative_count = sum(1 for f in feedbacks if f.is_negative)
    deleted_count = sum(1 for f in feedbacks if getattr(f, 'is_deleted', False))
    
    logger.info(f"[EFFICIENCY] Статистика: total={total_reviews}, negative={negative_count}, deleted={deleted_count}")
    
    # Распределение по рейтингам
    ratings_distribution = {}
    for rating in range(1, 6):
        count = sum(1 for f in feedbacks if f.rating == rating)
        ratings_distribution[f"rating_{rating}"] = count
    
    # Тренды по дням с накопительной долей
    day_aggregates: Dict[str, Dict[str, Any]] = {}
    for f in feedbacks:
        dt_val = getattr(f, 'date', None) or getattr(f, 'created_at', None)
        if not dt_val:
            continue
        d = dt_val.date().isoformat()
        if d not in day_aggregates:
            day_aggregates[d] = {
                'total': 0,
                'negative': 0,
                'deleted': 0
            }
        day_aggregates[d]['total'] += 1
        if getattr(f, 'is_negative', 0):
            day_aggregates[d]['negative'] += 1
        if getattr(f, 'is_deleted', False):
            day_aggregates[d]['deleted'] += 1

    trends: List[Dict[str, Any]] = []
    cumulative_total = 0
    cumulative_negative = 0
    cumulative_deleted = 0
    for d in sorted(day_aggregates.keys()):
        counts = day_aggregates[d]
        cumulative_total += counts['total']
        cumulative_negative += counts['negative']
        cumulative_deleted += counts['deleted']
        trends.append({
            "date": d,
            "negative_percent": round((cumulative_negative / cumulative_total) * 100, 1) if cumulative_total > 0 else 0.0,
            "deleted_percent": round((cumulative_deleted / cumulative_total) * 100, 1) if cumulative_total > 0 else 0.0
        })
    
    logger.info(f"[EFFICIENCY] Создано трендов: {len(trends)}")
    
    # Функция для расчета ежедневного трекинга времени в топах
    async def calculate_daily_tracking() -> List[Dict[str, Any]]:
        # Вспомогательная функция для форматирования времени
        def format_time_from_seconds(seconds):
            if seconds == 0:
                return "00:00:00"
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            remaining_seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
        
        daily_data: Dict[str, Dict[str, Any]] = {}
        
        # Генерируем все дни в диапазоне
        if start_date and end_date:
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.isoformat()
                daily_data[date_str] = {
                    'date': date_str,
                    'top_1_time': 0,
                    'top_3_time': 0,
                    'top_5_time': 0,
                    'top_10_time': 0,
                    'total_products_in_top': 0
                }
                current_date += timedelta(days=1)
        
        if not daily_data:
            return []
        
        # Получаем все записи FeedbackTopTracking для данного магазина и пользователя
        all_top_tracking_query = select(FeedbackTopTracking).where(
            and_(
                FeedbackTopTracking.user_id == user_id,
                FeedbackTopTracking.brand == shop_id
            )
        )
        
        # Фильтр по товару
        if product_id:
            nm_ids = set(f.article for f in feedbacks)
            if nm_ids:
                all_top_tracking_query = all_top_tracking_query.where(FeedbackTopTracking.article.in_(nm_ids))
        
        all_top_tracking_result = await db.execute(all_top_tracking_query)
        all_top_tracking_records = all_top_tracking_result.scalars().all()
        
        logger.info(f"[EFFICIENCY] Найдено записей top_tracking для ежедневного трекинга: {len(all_top_tracking_records)}")
        
        # Обрабатываем каждую запись
        for record in all_top_tracking_records:
            # Проверяем, находится ли товар в топе в указанный день
            for level in [1, 3, 5, 10]:
                time_attr = f"time_in_top_{level}"
                entered_attr = f"entered_top_{level}_at"
                is_in_attr = f"is_in_top_{level}"
                
                # Базовое время из записи
                base_time = int(getattr(record, time_attr, 0) or 0)
                
                # Дополнительное время, если товар в топе
                extra_time = 0
                if getattr(record, is_in_attr, False):
                    entered_at = getattr(record, entered_attr, None)
                    if entered_at:
                        # Рассчитываем время в топе для каждого дня
                        for date_str, day_data in daily_data.items():
                            day_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            
                            # Если товар вошел в топ до этого дня или в этот день
                            # Делаем datetime объекты timezone-naive для корректного сравнения
                            if hasattr(entered_at, 'tzinfo') and entered_at.tzinfo:
                                entered_at_naive = entered_at.replace(tzinfo=None)
                            else:
                                entered_at_naive = entered_at
                            
                            if entered_at_naive.date() <= day_date:
                                # Время в топе для этого дня (максимум 24 часа = 86400 секунд)
                                day_start = datetime.combine(day_date, datetime.min.time())
                                day_end = datetime.combine(day_date, datetime.max.time())
                                
                                # Ограничиваем диапазон
                                if start_date:
                                    day_start = max(day_start, datetime.combine(start_date, datetime.min.time()))
                                if end_date:
                                    day_end = min(day_end, datetime.combine(end_date, datetime.max.time()))
                                
                                # Делаем datetime объекты timezone-naive для корректного сравнения
                                if hasattr(entered_at, 'tzinfo') and entered_at.tzinfo:
                                    entered_at_naive = entered_at.replace(tzinfo=None)
                                else:
                                    entered_at_naive = entered_at
                                
                                if hasattr(day_end, 'tzinfo') and day_end.tzinfo:
                                    day_end_naive = day_end.replace(tzinfo=None)
                                else:
                                    day_end_naive = day_end
                                
                                # Рассчитываем время в топе для этого дня
                                if entered_at_naive < day_end_naive:
                                    # Делаем datetime объекты timezone-naive для корректного сравнения
                                    if hasattr(entered_at, 'tzinfo') and entered_at.tzinfo:
                                        entered_at_naive = entered_at.replace(tzinfo=None)
                                    else:
                                        entered_at_naive = entered_at
                                    
                                    if hasattr(day_start, 'tzinfo') and day_start.tzinfo:
                                        day_start_naive = day_start.replace(tzinfo=None)
                                    else:
                                        day_start_naive = day_start
                                    
                                    start_point = max(entered_at_naive, day_start_naive)
                                    end_point = min(datetime.utcnow(), day_end)
                                    
                                    if end_point > start_point:
                                        # Делаем datetime объекты timezone-naive для корректного сравнения
                                        if hasattr(start_point, 'tzinfo') and start_point.tzinfo:
                                            start_point = start_point.replace(tzinfo=None)
                                        if hasattr(end_point, 'tzinfo') and end_point.tzinfo:
                                            end_point = end_point.replace(tzinfo=None)
                                        
                                        day_seconds = int((end_point - start_point).total_seconds())
                                        day_data[f'top_{level}_time'] += day_seconds
                                        day_data['total_products_in_top'] += 1
                
                # Добавляем базовое время равномерно по дням
                if base_time > 0:
                    days_count = len(daily_data)
                    if days_count > 0:
                        time_per_day = base_time // days_count
                        for day_data in daily_data.values():
                            day_data[f'top_{level}_time'] += time_per_day
        
        # Форматируем время и считаем средние значения
        result = []
        for date_str, day_data in daily_data.items():
            # Форматируем время в чч:мм:сс
            formatted_data = {
                'date': date_str,
                'top_1_time': format_time_from_seconds(day_data['top_1_time']),
                'top_3_time': format_time_from_seconds(day_data['top_3_time']),
                'top_5_time': format_time_from_seconds(day_data['top_5_time']),
                'top_10_time': format_time_from_seconds(day_data['top_10_time']),
                'total_products_in_top': day_data['total_products_in_top']
            }
            result.append(formatted_data)
        
        return result
    
    # Получаем ежедневный трекинг
    daily_tracking = await calculate_daily_tracking()
    
    # Получаем данные о времени в топах
    top_tracking_query = select(FeedbackTopTracking).where(
        and_(
            FeedbackTopTracking.user_id == user_id,
            FeedbackTopTracking.brand == shop_id
        )
    )
    
    # Фильтр по товару для top_tracking - используем nm_id из feedbacks
    if product_id:
        # Получаем nm_id из найденных отзывов
        nm_ids = set(f.article for f in feedbacks)
        if nm_ids:
            top_tracking_query = top_tracking_query.where(FeedbackTopTracking.article.in_(nm_ids))
            logger.info(f"[EFFICIENCY] Фильтр top_tracking по nm_ids: {nm_ids}")
        else:
            logger.warning(f"[EFFICIENCY] Не найдено nm_ids для top_tracking")
    
    top_tracking_result = await db.execute(top_tracking_query)
    top_tracking_records = top_tracking_result.scalars().all()
    logger.info(f"[EFFICIENCY] Найдено записей top_tracking: {len(top_tracking_records)}")
    
    # Вычисляем среднее время в топах
    def format_time_from_seconds(seconds):
        if seconds == 0:
            return "00:00:00"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"
    
    # С учетом текущего нахождения в топе и дат диапазона
    def calculate_avg_time_in_top(level: int) -> str:
        time_attr = f"time_in_top_{level}"
        entered_attr = f"entered_top_{level}_at"
        is_in_attr = f"is_in_top_{level}"

        range_start = datetime.combine(start_date, datetime.min.time()) if start_date else None
        range_end = datetime.combine(end_date, datetime.max.time()) if end_date else None
        now_dt = datetime.utcnow()

        # Собираем время для каждого товара отдельно
        product_times = {}
        for record in top_tracking_records:
            article = record.article
            if article not in product_times:
                product_times[article] = []
            
            base_seconds = int(getattr(record, time_attr, 0) or 0)
            extra = 0
            if getattr(record, is_in_attr, False):
                entered_at = getattr(record, entered_attr, None)
                if entered_at is not None:
                    start_point = entered_at
                    end_point = now_dt
                    
                    # Делаем datetime объекты timezone-naive для корректного сравнения
                    if hasattr(start_point, 'tzinfo') and start_point.tzinfo:
                        start_point = start_point.replace(tzinfo=None)
                    if hasattr(end_point, 'tzinfo') and end_point.tzinfo:
                        end_point = end_point.replace(tzinfo=None)
                    if hasattr(range_start, 'tzinfo') and range_start and range_start.tzinfo:
                        range_start_naive = range_start.replace(tzinfo=None)
                    else:
                        range_start_naive = range_start
                    if hasattr(range_end, 'tzinfo') and range_end and range_end.tzinfo:
                        range_end_naive = range_end.replace(tzinfo=None)
                    else:
                        range_end_naive = range_end
                    
                    if range_start_naive and start_point < range_start_naive:
                        start_point = range_start_naive
                    if range_end_naive and end_point > range_end_naive:
                        end_point = range_end_naive
                    if end_point and start_point and end_point > start_point:
                        extra = int((end_point - start_point).total_seconds())
            
            total = base_seconds + extra
            if total > 0:
                product_times[article].append(total)
        
        # Усредняем время по товарам
        if not product_times:
            return "00:00:00"
        
        # Для каждого товара берем среднее время
        avg_times = []
        for article, times in product_times.items():
            if times:
                avg_times.append(sum(times) // len(times))
        
        if not avg_times:
            return "00:00:00"
        
        # Возвращаем среднее по всем товарам
        final_avg = sum(avg_times) // len(avg_times)
        return format_time_from_seconds(final_avg)
    
    # Fallback: если трекинг не дал значений, оцениваем по хронологии отзывов товара
    async def compute_avg_top_time_via_chronology(k: int) -> str:
        if not product_id:
            return "00:00:00"
        # Берем все отзывы товара (любой тональности), сортируем по времени
        fb_query = select(Feedback).where(
            and_(
                Feedback.user_id == user_id,
                Feedback.brand == shop_id,
                Feedback.vendor_code == product_id
            )
        ).order_by(func.coalesce(Feedback.date, Feedback.created_at).asc())
        if start_date:
            fb_query = fb_query.where(func.coalesce(Feedback.date, Feedback.created_at) >= start_date)
        if end_date:
            fb_query = fb_query.where(func.coalesce(Feedback.date, Feedback.created_at) <= end_date)
        fb_result = await db.execute(fb_query)
        fb_list = fb_result.scalars().all()
        if not fb_list:
            return "00:00:00"

        # Считаем длительность нахождения негативов в топ-K: от момента появления до появления K-го следующего отзыва
        durations: List[int] = []
        times = []
        for f in fb_list:
            dt_val = getattr(f, 'date', None) or getattr(f, 'created_at', None)
            if dt_val is None:
                continue
            times.append(dt_val)
        n = len(times)
        for i, f in enumerate(fb_list):
            if not getattr(f, 'is_negative', 0):
                continue
            # индекс K-го следующего отзыва
            j = i + k
            start_t = getattr(f, 'date', None) or getattr(f, 'created_at', None)
            if start_t is None:
                continue
            if j < n:
                end_t = times[j]
            else:
                # если меньше K последующих отзывов — до конца периода/текущего времени
                end_t = datetime.utcnow()
                if end_date:
                    end_t = min(end_t, datetime.combine(end_date, datetime.max.time()))
            # обрезаем начальную границу
            if start_date:
                start_t = max(start_t, datetime.combine(start_date, datetime.min.time()))
            if end_t > start_t:
                durations.append(int((end_t - start_t).total_seconds()))
        if not durations:
            return "00:00:00"
        avg_sec = sum(durations) // len(durations)
        return format_time_from_seconds(avg_sec)
    
    # Для всего магазина: усредняем время по всем товарам
    async def compute_avg_top_time_via_chronology_all_products(k: int) -> str:
        # Получаем все уникальные vendor_code для магазина
        vendor_codes_query = select(Feedback.vendor_code).where(
            and_(
                Feedback.user_id == user_id,
                Feedback.brand == shop_id,
                Feedback.vendor_code.isnot(None)
            )
        ).distinct()
        
        vendor_codes_result = await db.execute(vendor_codes_query)
        vendor_codes = [row[0] for row in vendor_codes_result.fetchall()]
        
        if not vendor_codes:
            return "00:00:00"
        
        # Считаем время для каждого товара
        product_times = []
        for vendor_code in vendor_codes:
            time_for_product = await compute_avg_top_time_via_chronology_single_product(vendor_code, k)
            if time_for_product != "00:00:00":
                # Конвертируем время обратно в секунды для усреднения
                seconds = time_to_seconds(time_for_product)
                if seconds > 0:
                    product_times.append(seconds)
        
        if not product_times:
            return "00:00:00"
        
        # Усредняем по всем товарам
        avg_seconds = sum(product_times) // len(product_times)
        return format_time_from_seconds(avg_seconds)
    
    # Вспомогательная функция для конвертации времени в секунды
    def time_to_seconds(time_str: str) -> int:
        if not time_str or time_str == "00:00:00":
            return 0
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return 0
    
    # Вспомогательная функция для расчета времени одного товара
    async def compute_avg_top_time_via_chronology_single_product(vendor_code: str, k: int) -> str:
        # Берем все отзывы товара (любой тональности), сортируем по времени
        fb_query = select(Feedback).where(
            and_(
                Feedback.user_id == user_id,
                Feedback.brand == shop_id,
                Feedback.vendor_code == vendor_code
            )
        ).order_by(func.coalesce(Feedback.date, Feedback.created_at).asc())
        if start_date:
            fb_query = fb_query.where(func.coalesce(Feedback.date, Feedback.created_at) >= start_date)
        if end_date:
            fb_query = fb_query.where(func.coalesce(Feedback.date, Feedback.created_at) <= end_date)
        fb_result = await db.execute(fb_query)
        fb_list = fb_result.scalars().all()
        if not fb_list:
            return "00:00:00"

        # Считаем длительность нахождения негативов в топ-K
        durations: List[int] = []
        times = []
        for f in fb_list:
            dt_val = getattr(f, 'date', None) or getattr(f, 'created_at', None)
            if dt_val is None:
                continue
            times.append(dt_val)
        n = len(times)
        for i, f in enumerate(fb_list):
            if not getattr(f, 'is_negative', 0):
                continue
            # индекс K-го следующего отзыва
            j = i + k
            start_t = getattr(f, 'date', None) or getattr(f, 'created_at', None)
            if start_t is None:
                continue
            if j < n:
                end_t = times[j]
            else:
                # если меньше K последующих отзывов — до конца периода/текущего времени
                end_t = datetime.utcnow()
                if end_date:
                    end_t = min(end_t, datetime.combine(end_date, datetime.max.time()))
            # обрезаем начальную границу
            if start_date:
                start_t = max(start_t, datetime.combine(start_date, datetime.min.time()))
            if end_t > start_t:
                durations.append(int((end_t - start_t).total_seconds()))
        if not durations:
            return "00:00:00"
        avg_sec = sum(durations) // len(durations)
        return format_time_from_seconds(avg_sec)

    # Инициализируем переменные времени в топах
    top_1_time = "00:00:00"
    top_3_time = "00:00:00"
    top_5_time = "00:00:00"
    top_10_time = "00:00:00"
    
    # Всегда используем fallback логику, так как основной трекинг работает медленно
    if product_id:
        logger.info(f"[EFFICIENCY] Используем fallback логику для товара {product_id}")
        top_1_time = await compute_avg_top_time_via_chronology(1)
        top_3_time = await compute_avg_top_time_via_chronology(3)
        top_5_time = await compute_avg_top_time_via_chronology(5)
        top_10_time = await compute_avg_top_time_via_chronology(10)
    else:
        # Для всего магазина используем fallback логику по всем товарам
        logger.info(f"[EFFICIENCY] Используем fallback логику для всего магазина")
        top_1_time = await compute_avg_top_time_via_chronology_all_products(1)
        top_3_time = await compute_avg_top_time_via_chronology_all_products(3)
        top_5_time = await compute_avg_top_time_via_chronology_all_products(5)
        top_10_time = await compute_avg_top_time_via_chronology_all_products(10)
    
    # Время удаления (пока заглушка)
    deletion_time = "00:00:00"
    
    # Рассчитываем ежедневный трекинг
    daily_tracking = await calculate_daily_tracking()
    logger.info(f"[EFFICIENCY] Создан ежедневный трекинг: {len(daily_tracking)} дней")
    
    result_data = {
        "total_reviews": total_reviews,
        "negative_count": negative_count,
        "deleted_count": deleted_count,
        "ratings_distribution": ratings_distribution,
        "negative_percentage": round((negative_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0,
        "deleted_percentage": round((deleted_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0,
        "top_1_time": top_1_time,
        "top_3_time": top_3_time,
        "top_5_time": top_5_time,
        "top_10_time": top_10_time,
        "deletion_time": deletion_time,
        "trends": trends,
        "daily_tracking": daily_tracking
    }
    
    logger.info(f"[EFFICIENCY] Возвращаем результат: {result_data}")
    return result_data


async def update_feedback_top_tracking(
    db: AsyncSession,
    feedback_id: int,
    article: str,
    brand: str,
    user_id: int,
    feedback_date: datetime,
    is_negative: bool
) -> None:
    """Обновление отслеживания времени в топах для негативного отзыва"""
    from sqlalchemy import select, and_
    
    # Создаем записи отслеживания только для негативных отзывов
    tracking = None
    if is_negative:
        # Получаем или создаем запись отслеживания
        tracking_query = select(FeedbackTopTracking).where(
            and_(
                FeedbackTopTracking.feedback_id == feedback_id,
                FeedbackTopTracking.article == article,
                FeedbackTopTracking.brand == brand,
                FeedbackTopTracking.user_id == user_id
            )
        )
        
        tracking_result = await db.execute(tracking_query)
        tracking = tracking_result.scalars().first()
        
        if not tracking:
            tracking = FeedbackTopTracking(
                feedback_id=feedback_id,
                article=article,
                brand=brand,
                user_id=user_id
            )
            db.add(tracking)
    
    # Обновляем время в топах для всех отзывов (негативные могут выталкиваться позитивными)
    # Получаем последние отзывы для определения позиции в топах
    recent_feedbacks_query = select(Feedback).where(
        and_(
            Feedback.user_id == user_id,
            Feedback.article == article,
            Feedback.brand == brand,
            Feedback.date <= feedback_date
        )
    ).order_by(Feedback.date.desc())
    
    recent_result = await db.execute(recent_feedbacks_query)
    recent_feedbacks = recent_result.scalars().all()
    
    # Определяем позицию в топах
    position = 1
    for i, recent_feedback in enumerate(recent_feedbacks):
        if recent_feedback.id == feedback_id:
            position = i + 1
            break
    
    # Если это негативный отзыв, обновляем его статус в топах
    if is_negative:
        # Обновляем статус в топах
        if position == 1 and not tracking.is_in_top_1:
            tracking.entered_top_1_at = feedback_date
            tracking.is_in_top_1 = True
        elif position > 1 and tracking.is_in_top_1:
            # Выпал из топ-1
            tracking.exited_top_1_at = feedback_date
            tracking.is_in_top_1 = False
            if tracking.entered_top_1_at:
                tracking.time_in_top_1 += int((feedback_date - tracking.entered_top_1_at).total_seconds())
        
        if 1 <= position <= 3 and not tracking.is_in_top_3:
            tracking.entered_top_3_at = feedback_date
            tracking.is_in_top_3 = True
        elif position > 3 and tracking.is_in_top_3:
            # Выпал из топ-3
            tracking.exited_top_3_at = feedback_date
            tracking.is_in_top_3 = False
            if tracking.entered_top_3_at:
                tracking.time_in_top_3 += int((feedback_date - tracking.entered_top_3_at).total_seconds())
        
        if 1 <= position <= 5 and not tracking.is_in_top_5:
            tracking.entered_top_5_at = feedback_date
            tracking.is_in_top_5 = True
        elif position > 5 and tracking.is_in_top_5:
            # Выпал из топ-5
            tracking.exited_top_5_at = feedback_date
            tracking.is_in_top_5 = False
            if tracking.entered_top_5_at:
                tracking.time_in_top_5 += int((feedback_date - tracking.entered_top_5_at).total_seconds())
        
        if 1 <= position <= 10 and not tracking.is_in_top_10:
            tracking.entered_top_10_at = feedback_date
            tracking.is_in_top_10 = True
        elif position > 10 and tracking.is_in_top_10:
            # Выпал из топ-10
            tracking.exited_top_10_at = feedback_date
            tracking.is_in_top_10 = False
            if tracking.entered_top_10_at:
                tracking.time_in_top_10 += int((feedback_date - tracking.entered_top_10_at).total_seconds())
    
    # Если это позитивный отзыв, проверяем, не выталкивает ли он негативные из топов
    else:
        # Получаем все записи отслеживания для этого товара
        all_tracking_query = select(FeedbackTopTracking).where(
            and_(
                FeedbackTopTracking.article == article,
                FeedbackTopTracking.brand == brand,
                FeedbackTopTracking.user_id == user_id
            )
        )
        
        all_tracking_result = await db.execute(all_tracking_query)
        all_tracking_records = all_tracking_result.scalars().all()
        
        # Пересчитываем позиции всех негативных отзывов
        for tracking_record in all_tracking_records:
            # Получаем позицию этого негативного отзыва из уже полученного списка
            negative_position = None
            for i, feedback in enumerate(recent_feedbacks):
                if feedback.id == tracking_record.feedback_id:
                    negative_position = i + 1
                    break
            
            if negative_position is None:
                continue
            
            # Проверяем топ-1
            if tracking_record.is_in_top_1 and negative_position > 1:
                # Негативный отзыв выпал из топ-1
                tracking_record.exited_top_1_at = feedback_date
                tracking_record.is_in_top_1 = False
                if tracking_record.entered_top_1_at:
                    tracking_record.time_in_top_1 += int((feedback_date - tracking_record.entered_top_1_at).total_seconds())
            
            # Проверяем топ-3
            if tracking_record.is_in_top_3 and negative_position > 3:
                # Негативный отзыв выпал из топ-3
                tracking_record.exited_top_3_at = feedback_date
                tracking_record.is_in_top_3 = False
                if tracking_record.entered_top_3_at:
                    tracking_record.time_in_top_3 += int((feedback_date - tracking_record.entered_top_3_at).total_seconds())
            
            # Проверяем топ-5
            if tracking_record.is_in_top_5 and negative_position > 5:
                # Негативный отзыв выпал из топ-5
                tracking_record.exited_top_5_at = feedback_date
                tracking_record.is_in_top_5 = False
                if tracking_record.entered_top_5_at:
                    tracking_record.time_in_top_5 += int((feedback_date - tracking_record.entered_top_5_at).total_seconds())
            
            # Проверяем топ-10
            if tracking_record.is_in_top_10 and negative_position > 10:
                # Негативный отзыв выпал из топ-10
                tracking_record.exited_top_10_at = feedback_date
                tracking_record.is_in_top_10 = False
                if tracking_record.entered_top_10_at:
                    tracking_record.time_in_top_10 += int((feedback_date - tracking_record.entered_top_10_at).total_seconds())
    
    await db.commit()


async def get_top_tracking_times_crud(
    db: AsyncSession,
    brand: str,
    product_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, str]:
    """Получение среднего времени нахождения негативных отзывов в топах"""
    
    # Базовый запрос для топ-трекинга
    query = select(FeedbackTopTracking).where(
        and_(
            FeedbackTopTracking.brand == brand,
            FeedbackTopTracking.feedback_id.isnot(None)
        )
    )
    
    if product_id:
        query = query.where(FeedbackTopTracking.article == product_id)
    
    if start_date:
        query = query.where(FeedbackTopTracking.created_at >= start_date)
    if end_date:
        query = query.where(FeedbackTopTracking.created_at <= end_date)
    
    result = await db.execute(query)
    tracking_records = result.scalars().all()
    
    if not tracking_records:
        return {
            "top_1": "0ч 00мин",
            "top_3": "0ч 00мин", 
            "top_5": "0ч 00мин",
            "top_10": "0ч 00мин"
        }
    
    # Вычисляем среднее время для каждого топа
    top_times = {}
    for top_size in [1, 3, 5, 10]:
        top_key = f"top_{top_size}"
        time_field = f"time_in_{top_key}"
        
        # Фильтруем записи с ненулевым временем
        valid_times = [
            getattr(record, time_field) 
            for record in tracking_records 
            if getattr(record, time_field) is not None and getattr(record, time_field) > 0
        ]
        
        if valid_times:
            avg_seconds = sum(valid_times) / len(valid_times)
            top_times[top_key] = format_time_duration(avg_seconds)
        else:
            top_times[top_key] = "0ч 00мин"
    
    return top_times


def format_time_duration(seconds: int) -> str:
    """Форматирование времени в формат чч:мм:сс"""
    if not seconds or seconds <= 0:
        return "0ч 00мин"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}ч {minutes:02d}мин"
    elif minutes > 0:
        return f"{minutes}мин {secs:02d}сек"
    else:
        return f"{secs}сек"


async def update_top_tracking_for_feedback(
    db: AsyncSession,
    feedback_id: int,
    article: str,
    brand: str,
    feedback_date: datetime,
    user_id: int
) -> None:
    """Обновление топ-трекинга при добавлении нового отзыва"""
    
    # Получаем или создаем запись трекинга
    tracking_query = select(FeedbackTopTracking).where(
        FeedbackTopTracking.feedback_id == feedback_id
    )
    result = await db.execute(tracking_query)
    tracking = result.scalars().first()
    
    if not tracking:
        tracking = FeedbackTopTracking(
            feedback_id=feedback_id,
            article=article,
            brand=brand,
            user_id=user_id,
            created_at=datetime.now()
        )
        db.add(tracking)
    
    # Получаем все отзывы для товара (по времени) с учетом user_id
    all_feedbacks_query = select(Feedback).where(
        and_(
            Feedback.article == article,
            Feedback.brand == brand,
            Feedback.user_id == user_id,
            Feedback.is_deleted == False
        )
    ).order_by(Feedback.date.asc())  # От старых к новым
    
    result = await db.execute(all_feedbacks_query)
    all_feedbacks = result.scalars().all()
    
    # Находим позицию текущего отзыва в общем списке
    current_feedback_index = None
    for i, fb in enumerate(all_feedbacks):
        if fb.id == feedback_id:
            current_feedback_index = i
            break
    
    if current_feedback_index is None:
        return
    
    # Определяем, в каких топах находится текущий отзыв
    top_sizes = [1, 3, 5, 10]
    
    for top_size in top_sizes:
        is_in_top = current_feedback_index < top_size
        entered_field = f"entered_top_{top_size}_at"
        is_in_field = f"is_in_top_{top_size}"
        time_field = f"time_in_top_{top_size}"
        
        if is_in_top:
            # Отзыв в топе
            if not getattr(tracking, entered_field):
                # Впервые вошел в топ
                setattr(tracking, entered_field, feedback_date)
            setattr(tracking, is_in_field, True)
        else:
            # Отзыв не в топе
            if getattr(tracking, is_in_field):
                # Вышел из топа - вычисляем время нахождения
                entered_time = getattr(tracking, entered_field)
                if entered_time:
                    # Приводим к одинаковому типу времени (без часовых поясов)
                    try:
                        if hasattr(entered_time, 'replace'):
                            entered_time_naive = entered_time.replace(tzinfo=None) if entered_time.tzinfo else entered_time
                        else:
                            entered_time_naive = entered_time
                        
                        if hasattr(feedback_date, 'replace'):
                            feedback_date_naive = feedback_date.replace(tzinfo=None) if feedback_date.tzinfo else feedback_date
                        else:
                            feedback_date_naive = feedback_date
                        
                        time_in_seconds = int((feedback_date_naive - entered_time_naive).total_seconds())
                        current_time = getattr(tracking, time_field, 0)
                        setattr(tracking, time_field, current_time + time_in_seconds)
                    except Exception as e:
                        logger.warning(f"[TOP_TRACKING] Ошибка вычисления времени для feedback_id={feedback_id}: {e}")
                        # Пропускаем обновление времени при ошибке
                
                # Сбрасываем статус
                setattr(tracking, is_in_field, False)
                setattr(tracking, entered_field, None)
    
    tracking.updated_at = datetime.now()
    await db.commit()


async def recalculate_all_top_tracking(
    db: AsyncSession,
    user_id: int,
    brand: str
) -> None:
    """Пересчитывает все топ-трекинги для бренда"""
    logger = logging.getLogger(__name__)
    logger.info(f"[TOP_TRACKING] Пересчитываем топ-трекинги для бренда {brand} user_id={user_id}")
    
    try:
        # Получаем все отзывы бренда, отсортированные по времени - убираем фильтр по user_id
        feedbacks_query = select(Feedback).where(
            and_(
                Feedback.brand == brand,
                Feedback.is_deleted == False
            )
        ).order_by(Feedback.date.asc())
        
        result = await db.execute(feedbacks_query)
        feedbacks = result.scalars().all()
        
        logger.info(f"[TOP_TRACKING] Найдено отзывов: {len(feedbacks)}")
        
        # Группируем отзывы по артикулам
        articles = {}
        for feedback in feedbacks:
            article = feedback.article
            if article not in articles:
                articles[article] = []
            articles[article].append(feedback)
        
        logger.info(f"[TOP_TRACKING] Найдено артикулов: {len(articles)}")
        
        # Обрабатываем артикулы параллельно
        logger.info(f"[TOP_TRACKING] Начинаем параллельную обработку артикулов...")
        
        # Создаем задачи для каждого артикула
        article_tasks = []
        for article, article_feedbacks in articles.items():
            logger.info(f"[TOP_TRACKING] Подготавливаем артикул {article} ({len(article_feedbacks)} отзывов)")
            
            # Сортируем отзывы по времени
            sorted_feedbacks = sorted(article_feedbacks, key=lambda f: f.date or f.created_at or datetime.min)
            
            # Создаем задачу для артикула
            task = process_article_top_tracking_batch(db, article, brand, sorted_feedbacks, user_id)
            article_tasks.append(task)
        
        # Выполняем все артикулы параллельно
        logger.info(f"[TOP_TRACKING] Запускаем {len(article_tasks)} артикулов параллельно...")
        await asyncio.gather(*article_tasks, return_exceptions=True)
        
        logger.info(f"[TOP_TRACKING] Топ-трекинги пересчитаны для бренда {brand} параллельно")
        
    except Exception as e:
        logger.error(f"[TOP_TRACKING] Ошибка при пересчете топ-трекингов: {e}")
        import traceback
        logger.error(f"[TOP_TRACKING] Traceback: {traceback.format_exc()}")


async def process_article_top_tracking_batch(
    db: AsyncSession,
    article: str,
    brand: str,
    feedbacks: List[Feedback],
    user_id: int
) -> None:
    """Обрабатывает топ-трекинг для всех отзывов артикула батчами"""
    logger = logging.getLogger(__name__)
    logger.info(f"[TOP_TRACKING_BATCH] Обрабатываем артикул {article} ({len(feedbacks)} отзывов)")
    
    try:
        # Разбиваем отзывы на батчи для параллельной обработки
        BATCH_SIZE = 50
        feedback_batches = [feedbacks[i:i + BATCH_SIZE] for i in range(0, len(feedbacks), BATCH_SIZE)]
        
        logger.info(f"[TOP_TRACKING_BATCH] Разбито на {len(feedback_batches)} батчей по {BATCH_SIZE}")
        
        # Обрабатываем каждый батч параллельно
        for batch_num, batch in enumerate(feedback_batches):
            batch_tasks = []
            for feedback in batch:
                task = update_top_tracking_for_feedback(
                    db, feedback.id, article, brand, feedback.date or feedback.created_at or datetime.now(), user_id
                )
                batch_tasks.append(task)
            
            # Выполняем батч параллельно
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            logger.info(f"[TOP_TRACKING_BATCH] Обработан батч {batch_num + 1}/{len(feedback_batches)} ({len(batch)} отзывов)")
        
        logger.info(f"[TOP_TRACKING_BATCH] Артикул {article} обработан полностью")
        
    except Exception as e:
        logger.error(f"[TOP_TRACKING_BATCH] Ошибка при обработке артикула {article}: {e}")


async def process_top_tracking_for_product(
    db: AsyncSession,
    article: str,
    brand: str,
    user_id: int
) -> None:
    """Обработка топ-трекинга для всех отзывов товара"""
    
    # Получаем все отзывы товара, отсортированные по времени - убираем фильтр по user_id
    feedbacks_query = select(Feedback).where(
        and_(
            Feedback.article == article,
            Feedback.brand == brand,
            Feedback.is_deleted == False
        )
    ).order_by(Feedback.date.asc())  # От старых к новым
    
    result = await db.execute(feedbacks_query)
    feedbacks = result.scalars().all()
    
    # Обрабатываем каждый отзыв
    for i, feedback in enumerate(feedbacks):
        await update_top_tracking_for_feedback(
            db, feedback.id, article, brand, feedback.date, user_id
        )


async def get_shops_summary_crud(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Получение сводки по магазинам"""
    # Получаем все бренды - убираем фильтр по user_id
    brands_query = select(Feedback.brand).distinct()
    brands_result = await db.execute(brands_query)
    brands = brands_result.scalars().all()

    summary = []
    for brand in brands:
        # Базовый запрос для бренда - убираем фильтр по user_id
        query = select(Feedback).where(Feedback.brand == brand)

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
            # Получаем vendor_code из feedbacks по nm_id (article)
            for article in products_data.keys():
                try:
                    nm_id = int(article)
                    nm_id_str = str(nm_id)
                    # Ищем vendor_code в feedbacks - убираем фильтр по user_id
                    vendor_code_query = select(Feedback.vendor_code).where(
                        Feedback.article == nm_id_str
                    ).limit(1)
                    vendor_code_result = await db.execute(vendor_code_query)
                    vendor_code = vendor_code_result.scalar()
                    vendor_codes[article] = vendor_code or str(article)
                except (ValueError, TypeError):
                    vendor_codes[article] = str(article)

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
    logger.info(f"[PARSE] user_id: {user_id}, save_to_db: {save_to_db}")

    # Используем исходный shop_id напрямую (без маппинга)
    logger.info(f"[PARSE] Используем бренд: '{shop_id}'")

    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    # Проверяем API ключ для бренда
    if not user or not user.wb_api_key or shop_id not in user.wb_api_key:
        error_msg = f"API ключ для бренда '{shop_id}' не найден"
        logger.error(f"[PARSE] ОШИБКА: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }
    
    logger.info(f"[PARSE] Используем API ключ для бренда: {shop_id}")

    try:
        # Получаем API ключ для бренда
        logger.info(f"[PARSE] Получаем API ключ для бренда {shop_id}...")
        wb_api_key = await get_decrypted_wb_key(db, user, shop_id)
        logger.info(f"[PARSE] API ключ получен успешно")

        # Получаем список товаров бренда с пагинацией
        logger.info(f"[PARSE] Получаем список товаров бренда {shop_id} с пагинацией...")
        wb_client = WBAPIClient(api_key=wb_api_key)
        items_result = await wb_client.get_all_cards_with_pagination(brand=shop_id)

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
                    None  # Используем дефолтную дату (2 года назад)
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

                # Добавляем артикул и vendor_code к каждому отзыву
                for feedback in feedbacks_data:
                    feedback['article'] = nm_id
                    feedback['vendor_code'] = vendor_code  # Добавляем vendor_code

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
            # Дедупликация отзывов по wb_id + article + brand (а не только по wb_id)
            unique_feedbacks = {}
            for feedback in all_feedbacks_data:
                wb_id = feedback.get('id') or feedback.get('wb_id')
                article = feedback.get('article')
                brand = shop_id  # Используем shop_id напрямую
                
                if wb_id and article and brand:
                    # Создаем уникальный ключ по комбинации wb_id + article + brand
                    unique_key = f"{wb_id}_{article}_{brand}"
                    if unique_key not in unique_feedbacks:
                        unique_feedbacks[unique_key] = feedback
            
            deduplicated_feedbacks = list(unique_feedbacks.values())
            logger.info(f"[PARSE] Дедупликация: было {len(all_feedbacks_data)}, стало {len(deduplicated_feedbacks)}")
            logger.info(f"[PARSE] Дедупликация по ключу: wb_id + article + brand")
            
            logger.info(f"[PARSE] Синхронизируем все {len(deduplicated_feedbacks)} отзывов для бренда {shop_id}...")
            sync_stats = await sync_feedbacks_with_soft_delete_optimized(
                db=db,
                feedbacks_from_wb=deduplicated_feedbacks,
                brand=shop_id,  # Используем исходный shop_id
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
        
        # Обновляем топ-трекинг для всех товаров бренда (ВСЕГДА, если save_to_db=True)
        if save_to_db:
            logger.info(f"[PARSE] ===== НАЧИНАЕМ ОБНОВЛЕНИЕ ТОП-ТРЕКИНГА =====")
            logger.info(f"[PARSE] Обновляем топ-трекинг для всех товаров бренда {shop_id}...")
            logger.info(f"[PARSE] user_id: {user_id}")
            logger.info(f"[PARSE] shop_id: {shop_id}")
            
            try:
                # Получаем уникальные артикулы для бренда
                logger.info(f"[PARSE] Выполняем запрос для получения артикулов...")
                unique_articles_query = select(Feedback.article).where(
                    and_(
                        Feedback.brand == shop_id,
                        Feedback.is_deleted == False
                    )
                ).distinct()
                articles_result = await db.execute(unique_articles_query)
                unique_articles = articles_result.scalars().all()
                
                logger.info(f"[PARSE] Найдено уникальных артикулов: {len(unique_articles)}")
                logger.info(f"[PARSE] Артикулы: {unique_articles[:5]}...")  # Показываем первые 5
                
                # Обновляем топ-трекинг для всех артикулов параллельно
                logger.info(f"[PARSE] Начинаем параллельную обработку артикулов...")
                
                # Создаем задачи для параллельного выполнения
                tasks = []
                for article in unique_articles:
                    task = update_top_tracking_for_all_feedbacks(db, article, shop_id, user_id)
                    tasks.append(task)
                
                # Выполняем все задачи параллельно
                logger.info(f"[PARSE] Запускаем {len(tasks)} задач параллельно...")
                await asyncio.gather(*tasks, return_exceptions=True)
                
                logger.info(f"[PARSE] Топ-трекинг обновлен для всех артикулов параллельно")
            except Exception as e:
                logger.error(f"[PARSE] Ошибка при обновлении топ-трекинга: {e}")
                import traceback
                logger.error(f"[PARSE] Traceback: {traceback.format_exc()}")

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


async def update_top_tracking_for_all_feedbacks(
    db: AsyncSession,
    article: str,
    brand: str,
    user_id: int
) -> None:
    """Обновляет топ-трекинг для всех отзывов товара"""
    logger = logging.getLogger(__name__)
    logger.info(f"[TOP_TRACKING] СТАРТ: Обновляем топ-трекинг для товара {article} бренда {brand} user_id={user_id}")
    
    try:
        # Получаем все отзывы товара, отсортированные по времени - убираем фильтр по user_id
        feedbacks_query = select(Feedback).where(
            and_(
                Feedback.article == article,
                Feedback.brand == brand,
                Feedback.is_deleted == False
            )
        ).order_by(Feedback.date.asc())  # От старых к новым
        
        result = await db.execute(feedbacks_query)
        feedbacks = result.scalars().all()
        
        if not feedbacks:
            return
        
        # Обрабатываем отзывы батчами для ускорения
        BATCH_SIZE = 50  # Размер батча для параллельной обработки
        
        # Разбиваем отзывы на батчи
        feedback_batches = [feedbacks[i:i + BATCH_SIZE] for i in range(0, len(feedbacks), BATCH_SIZE)]
        
        logger.info(f"[TOP_TRACKING] Обрабатываем {len(feedbacks)} отзывов в {len(feedback_batches)} батчах по {BATCH_SIZE}")
        
        # Обрабатываем каждый батч параллельно
        for batch_num, batch in enumerate(feedback_batches):
            # Создаем задачи для батча
            batch_tasks = []
            for feedback in batch:
                task = update_top_tracking_for_feedback(
                    db, feedback.id, article, brand, feedback.date, user_id
                )
                batch_tasks.append(task)
            
            # Выполняем батч параллельно
            await asyncio.gather(*batch_tasks, return_exceptions=True)
            logger.info(f"[TOP_TRACKING] Обработан батч {batch_num + 1}/{len(feedback_batches)} ({len(batch)} отзывов)")
        
        logger.info(f"[TOP_TRACKING] Обновлен топ-трекинг для товара {article} бренда {brand}")
        
    except Exception as e:
        logger.error(f"[TOP_TRACKING] Ошибка при обновлении топ-трекинга для товара {article}: {e}") 