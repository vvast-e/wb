from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc, case, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.feedback import Feedback
from models.user import User
from models.product import Product


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
        try:
            product_id = int(product)
            query = query.where(Feedback.article == product_id)
        except (ValueError, TypeError):
            # Если product не является числом, ищем по vendor_code в таблице products
            product_query = select(Product.nm_id).where(Product.vendor_code == product)
            product_result = await db.execute(product_query)
            product_data = product_result.scalar_one_or_none()
            if product_data:
                query = query.where(Feedback.article == product_data)
            else:
                # Если товар не найден, возвращаем пустой результат
                return {
                    "reviews": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 0
                }

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
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Получаем отзывы с пагинацией
    query = query.order_by(desc(func.coalesce(Feedback.date, Feedback.created_at)), desc(Feedback.id)).offset(offset).limit(per_page)
    result = await db.execute(query)
    feedbacks = result.scalars().all()

    # Формируем ответ
    reviews = []
    
    # Получаем vendor_code для всех товаров
    article_ids = [f.article for f in feedbacks if f.article]
    vendor_codes = {}
    if article_ids:
        # Преобразуем строковые артикулы в целые числа
        nm_ids = []
        for article_id in article_ids:
            try:
                nm_id = int(article_id)
                nm_ids.append(str(nm_id))
            except (ValueError, TypeError):
                continue
        
        if nm_ids:
            product_query = select(Product.nm_id, Product.vendor_code).where(Product.nm_id.in_(nm_ids))
            product_result = await db.execute(product_query)
            products_data_db = product_result.fetchall()
            for nm_id, vendor_code in products_data_db:
                vendor_codes[nm_id] = vendor_code or str(nm_id)
    

    
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
        vendor_code = vendor_codes.get(feedback.article, str(feedback.article))
        
        # Логируем данные для отладки
        print(f"[DEBUG] Отзыв {feedback.id}: pros_text='{feedback.pros_text}', cons_text='{feedback.cons_text}', main_text='{feedback.main_text}'")
        
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
            product_query = select(Product.vendor_code).where(Product.nm_id == nm_id)
            product_result = await db.execute(product_query)
            product_data = product_result.scalar_one_or_none()
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
    """Получение данных эффективности"""
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
        query = query.where(Feedback.article == int(product_id))

    result = await db.execute(query)
    feedbacks = result.scalars().all()

    if not feedbacks:
        return None

    # Подсчитываем статистику
    total_reviews = len(feedbacks)
    negative_count = sum(1 for f in feedbacks if f.is_negative)
    negative_percentage = (negative_count / total_reviews) * 100 if total_reviews > 0 else 0

    # Пока нет данных об удаленных отзывах
    deleted_count = 0
    deleted_percentage = 0

    # Среднее время ответа (пока заглушка)
    response_time_avg = 24.5

    # Обработанные отзывы
    processed_count = sum(1 for f in feedbacks if f.is_processed)
    pending_count = total_reviews - processed_count

    # Распределение рейтингов
    ratings_distribution = {
        "5": sum(1 for f in feedbacks if f.rating == 5),
        "4": sum(1 for f in feedbacks if f.rating == 4),
        "3": sum(1 for f in feedbacks if f.rating == 3),
        "2": sum(1 for f in feedbacks if f.rating == 2),
        "1": sum(1 for f in feedbacks if f.rating == 1)
    }

    # Тренды (пока заглушки)
    negative_trend = [
        {"date": "2024-01-01", "count": 5},
        {"date": "2024-01-02", "count": 3}
    ]

    deleted_trend = [
        {"date": "2024-01-01", "count": 2},
        {"date": "2024-01-02", "count": 1}
    ]

    return {
        "total_reviews": total_reviews,
        "negative_count": negative_count,
        "negative_percentage": round(negative_percentage, 2),
        "deleted_count": deleted_count,
        "deleted_percentage": deleted_percentage,
        "response_time_avg": response_time_avg,
        "processed_count": processed_count,
        "pending_count": pending_count,
        "ratings_distribution": ratings_distribution,
        "negative_trend": negative_trend,
        "deleted_trend": deleted_trend
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
    from crud.feedback import sync_feedbacks_with_soft_delete
    from models.user import User

    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalars().first()

    if not user or not user.wb_api_key or shop_id not in user.wb_api_key:
        return {
            "success": False,
            "error": f"API ключ для бренда '{shop_id}' не найден"
        }

    try:
        # Получаем API ключ для бренда
        wb_api_key = await get_decrypted_wb_key(db, user, shop_id)

        # Получаем список товаров бренда
        wb_client = WBAPIClient(api_key=wb_api_key)
        items_result = await wb_client.get_cards_list()

        if not items_result.success:
            return {
                "success": False,
                "error": f"Не удалось получить товары бренда: {items_result.error}"
            }

        items = items_result.data.get("cards", [])
        if not items:
            return {
                "success": False,
                "error": "Товары не найдены"
            }

        # Статистика парсинга
        total_products = len(items)
        successful_products = 0
        failed_products = 0
        total_feedbacks = 0
        total_new_feedbacks = 0
        total_restored_feedbacks = 0
        total_deleted_feedbacks = 0

        results = []

        # Парсим отзывы для каждого товара
        for item in items:
            nm_id = item.get("nmID")
            vendor_code = item.get("vendorCode", "")

            if not nm_id:
                failed_products += 1
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": False,
                    "error": "nmID не найден"
                })
                continue

            try:
                # Парсим отзывы для товара
                feedbacks_data = await parse_feedbacks_optimized(
                    nm_id,
                    max_count_per_product
                )

                if feedbacks_data is None:
                    failed_products += 1
                    results.append({
                        "nm_id": nm_id,
                        "vendor_code": vendor_code,
                        "success": False,
                        "error": "Ошибка парсинга"
                    })
                    continue

                # Добавляем артикул к каждому отзыву
                for feedback in feedbacks_data:
                    feedback['article'] = nm_id

                total_feedbacks += len(feedbacks_data)

                # Синхронизируем отзывы с поддержкой soft delete
                if save_to_db and feedbacks_data:
                    sync_stats = await sync_feedbacks_with_soft_delete(
                        db=db,
                        feedbacks_from_wb=feedbacks_data,
                        brand=shop_id,
                        user_id=user_id
                    )
                    
                    total_new_feedbacks += sync_stats['new_feedbacks']
                    total_restored_feedbacks += sync_stats['restored_feedbacks']
                    total_deleted_feedbacks += sync_stats['deleted_feedbacks']

                successful_products += 1
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": True,
                    "parsed_count": len(feedbacks_data),
                    "sync_stats": sync_stats if save_to_db and feedbacks_data else None
                })

            except Exception as e:
                failed_products += 1
                results.append({
                    "nm_id": nm_id,
                    "vendor_code": vendor_code,
                    "success": False,
                    "error": str(e)
                })

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
        return {
            "success": False,
            "error": f"Ошибка массового парсинга: {str(e)}"
        } 