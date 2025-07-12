from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import re

from models.feedback import Feedback, FeedbackAnalytics
from models.user import User
from zoneinfo import ZoneInfo


def moscow_now():
    return datetime.now(ZoneInfo("Europe/Moscow"))


async def create_feedback(
    db: AsyncSession,
    article: int,
    brand: str,
    author: str,
    rating: int,
    date: Optional[datetime],
    status: str,
    text: str,
    main_text: Optional[str] = None,
    pros_text: Optional[str] = None,
    cons_text: Optional[str] = None,
    user_id: Optional[int] = None,
    history_id: Optional[int] = None
) -> Feedback:
    """Создание нового отзыва"""
    feedback = Feedback(
        article=article,
        brand=brand,
        author=author,
        rating=rating,
        date=date,
        status=status,
        text=text,
        main_text=main_text,
        pros_text=pros_text,
        cons_text=cons_text,
        user_id=user_id,
        history_id=history_id,
        is_negative=1 if rating <= 2 else 0
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def get_feedbacks(
    db: AsyncSession,
    article: Optional[int] = None,
    brand: Optional[str] = None,
    rating_min: Optional[int] = None,
    rating_max: Optional[int] = None,
    is_negative: Optional[int] = None,
    is_processed: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    order_by: str = "created_at",
    order_dir: str = "desc"
) -> List[Feedback]:
    """Получение отзывов с фильтрацией"""
    stmt = select(Feedback).options(joinedload(Feedback.user))
    
    # Применяем фильтры
    if article:
        stmt = stmt.where(Feedback.article == article)
    if brand:
        stmt = stmt.where(Feedback.brand == brand)
    if rating_min is not None:
        stmt = stmt.where(Feedback.rating >= rating_min)
    if rating_max is not None:
        stmt = stmt.where(Feedback.rating <= rating_max)
    if is_negative is not None:
        stmt = stmt.where(Feedback.is_negative == is_negative)
    if is_processed is not None:
        stmt = stmt.where(Feedback.is_processed == is_processed)
    if date_from:
        stmt = stmt.where(Feedback.date >= date_from)
    if date_to:
        stmt = stmt.where(Feedback.date <= date_to)
    
    # Сортировка
    sort_column_map = {
        "created_at": Feedback.created_at,
        "date": Feedback.date,
        "rating": Feedback.rating,
        "article": Feedback.article,
        "brand": Feedback.brand
    }
    
    sort_col = sort_column_map.get(order_by, Feedback.created_at)
    if order_dir == "asc":
        stmt = stmt.order_by(asc(sort_col))
    else:
        stmt = stmt.order_by(desc(sort_col))
    
    stmt = stmt.offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_feedback_analytics(
    db: AsyncSession,
    article: Optional[int] = None,
    brand: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
) -> Dict[str, Any]:
    """Получение аналитики по отзывам"""
    stmt = select(Feedback)
    
    # Применяем фильтры
    if article:
        stmt = stmt.where(Feedback.article == article)
    if brand:
        stmt = stmt.where(Feedback.brand == brand)
    if date_from:
        stmt = stmt.where(Feedback.date >= date_from)
    if date_to:
        stmt = stmt.where(Feedback.date <= date_to)
    
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()
    
    if not feedbacks:
        return {
            "total_reviews": 0,
            "avg_rating": 0.0,
            "rating_distribution": {},
            "negative_count": 0,
            "processed_negative_count": 0,
            "unprocessed_negative_count": 0,
            "processing_rate": 0.0
        }
    
    # Статистика
    total_reviews = len(feedbacks)
    avg_rating = sum(f.rating for f in feedbacks) / total_reviews
    
    # Распределение по рейтингам
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = len([f for f in feedbacks if f.rating == i])
    
    # Негативные отзывы
    negative_count = len([f for f in feedbacks if f.is_negative == 1])
    processed_negative_count = len([f for f in feedbacks if f.is_negative == 1 and f.is_processed == 1])
    unprocessed_negative_count = negative_count - processed_negative_count
    
    return {
        "total_reviews": total_reviews,
        "avg_rating": round(avg_rating, 2),
        "rating_distribution": rating_distribution,
        "negative_count": negative_count,
        "processed_negative_count": processed_negative_count,
        "unprocessed_negative_count": unprocessed_negative_count,
        "processing_rate": round(processed_negative_count / negative_count * 100, 2) if negative_count > 0 else 0.0
    }


async def update_feedback_processing(
    db: AsyncSession,
    feedback_id: int,
    is_processed: int,
    processing_notes: Optional[str] = None,
    sentiment_score: Optional[float] = None
) -> Optional[Feedback]:
    """Обновление статуса обработки отзыва"""
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    feedback = result.scalars().first()
    
    if not feedback:
        return None
    
    feedback.is_processed = is_processed
    feedback.processing_notes = processing_notes
    feedback.sentiment_score = sentiment_score
    feedback.updated_at = moscow_now()
    
    await db.commit()
    await db.refresh(feedback)
    return feedback


def parse_wb_date(date_str: str) -> datetime:
    MONTHS = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    match = re.match(r'(\d+)\s+(\w+)(?:\s+(\d+))?,\s+(\d+):(\d+)', date_str)
    if match:
        day, month_str, year, hour, minute = match.groups()
        month = MONTHS.get(month_str.lower())
        if not month:
            print(f"[WARN] Неизвестный месяц: {month_str} в дате: '{date_str}'")
            return None
        now = datetime.now()
        year_was_missing = not year
        if not year:
            year = str(now.year)
        parsed_date_str = f"{year}-{month}-{day} {hour}:{minute}"
        print("-" * 50)
        print(parsed_date_str)
        try:
            parsed = datetime.strptime(parsed_date_str, "%Y-%m-%d %H:%M")
            # Если год был подставлен и дата в будущем — уменьшить год на 1
            if year_was_missing and parsed > now:
                parsed = parsed.replace(year=parsed.year - 1)
            if parsed > now:
                print(f"[WARN] Будущая дата обнаружена: {parsed}, отзыв будет пропущен")
                return None
            return parsed
        except Exception as e:
            print(f"[ERROR] strptime fail for '{parsed_date_str}': {e}")
            return None

    try:
        from dateutil import parser
        if re.match(r'^\d{4}-\d{2}-\d{2}T', date_str):
            # ISO-формат: год-месяц-день
            parsed = parser.parse(date_str)
        else:
            parsed = parser.parse(date_str, dayfirst=True)
        now = datetime.now()
        if parsed > now:
            print(f"[WARN] Будущая дата обнаружена: {parsed}, отзыв будет пропущен")
            return None
        return parsed
    except Exception as e:
        #print(f"[WARN] Ошибка при парсинге даты '{date_str}': {e}")
        return None


async def save_feedbacks_batch(
    db: AsyncSession,
    feedbacks_data: List[Dict[str, Any]],
    brand: str,
    user_id: Optional[int] = None,
    history_id: Optional[int] = None
) -> List[Feedback]:
    """Сохранение пакета отзывов с проверкой дублей"""
    feedbacks = []
    
    for data in feedbacks_data:
        # Проверяем, есть ли уже такой отзыв в базе
        existing_query = select(Feedback).where(
            and_(
                Feedback.article == data.get('article'),
                Feedback.brand == brand,
                Feedback.author == data.get('author', 'Аноним'),
                Feedback.text == data.get('text', ''),
                Feedback.user_id == user_id
            )
        )
        existing_result = await db.execute(existing_query)
        existing_feedback = existing_result.scalars().first()
        
        # Если отзыв уже существует, пропускаем
        if existing_feedback:
            continue
        
        # Разбираем текст на части
        text = data.get('text', '')
        main_text = None
        pros_text = None
        cons_text = None
        
        if 'Достоинства:' in text:
            parts = text.split('Достоинства:')
            main_text = parts[0].strip()
            if 'Недостатки:' in parts[1]:
                pros_cons = parts[1].split('Недостатки:')
                pros_text = pros_cons[0].strip()
                cons_text = pros_cons[1].strip()
            else:
                pros_text = parts[1].strip()
        elif 'Недостатки:' in text:
            parts = text.split('Недостатки:')
            main_text = parts[0].strip()
            cons_text = parts[1].strip()
        else:
            # Если нет разделителей, весь текст идет в main_text
            main_text = text
            pros_text = None
            cons_text = None
        
        # Обработка даты
        date_str = data.get('date')
        date_obj = None
        if date_str and isinstance(date_str, str) and date_str.strip():
            date_obj = parse_wb_date(date_str)
            if date_obj is None:
                print(f"[WARN] Не удалось распарсить дату: '{date_str}' для отзыва: {data}")
        
        feedback = Feedback(
            article=data.get('article'),
            brand=brand,
            author=data.get('author', 'Аноним'),
            rating=data.get('rating', 0),
            date=date_obj,  # Используем обработанную дату
            status=data.get('status', 'Без подтверждения'),
            text=text,
            main_text=main_text,
            pros_text=pros_text,
            cons_text=cons_text,
            user_id=user_id,
            history_id=history_id,
            is_negative=1 if data.get('rating', 0) <= 2 else 0
        )
        feedbacks.append(feedback)
    
    if feedbacks:
        db.add_all(feedbacks)
        await db.commit()
        
        for feedback in feedbacks:
            await db.refresh(feedback)
    
    return feedbacks


async def get_unprocessed_negative_feedbacks(
    db: AsyncSession,
    brand: Optional[str] = None,
    limit: int = 50
) -> List[Feedback]:
    """Получение необработанных негативных отзывов"""
    stmt = select(Feedback).where(
        and_(
            Feedback.is_negative == 1,
            Feedback.is_processed == 0
        )
    ).options(joinedload(Feedback.user))
    
    if brand:
        stmt = stmt.where(Feedback.brand == brand)
    
    stmt = stmt.order_by(desc(Feedback.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()