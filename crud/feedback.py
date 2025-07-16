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
    include_deleted: bool = False,
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
    
    # Фильтр по удалённым отзывам
    if not include_deleted:
        stmt = stmt.where(Feedback.is_deleted == False)
    
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
    date_to: Optional[datetime] = None,
    include_deleted: bool = False
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
    
    # Фильтр по удалённым отзывам
    if not include_deleted:
        stmt = stmt.where(Feedback.is_deleted == False)
    
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
    """
    Парсинг даты из Wildberries API с поддержкой различных форматов
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # Словарь месяцев для русского формата
    MONTHS = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }
    
    # 1. Пробуем русский формат: "15 января 2024, 10:30"
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

    # 2. Пробуем ISO формат: "2024-01-15T10:30:00" или "2024-01-15T10:30:00Z"
    if 'T' in date_str:
        try:
            # Для ISO форматов с Z (UTC) используем специальную обработку
            if 'Z' in date_str:
                # Убираем Z и парсим как UTC
                clean_date_str = date_str.replace('Z', '+00:00')
                parsed = datetime.fromisoformat(clean_date_str)
                # Конвертируем в московское время
                from zoneinfo import ZoneInfo
                moscow_tz = ZoneInfo("Europe/Moscow")
                parsed = parsed.astimezone(moscow_tz)
                # Убираем timezone info для сохранения в БД
                parsed = parsed.replace(tzinfo=None)
            else:
                # Убираем часовой пояс если есть
                clean_date_str = date_str
                if '+' in clean_date_str:
                    clean_date_str = clean_date_str.split('+')[0]
                
                # Парсим ISO формат
                parsed = datetime.fromisoformat(clean_date_str)
            
            # Проверяем, что дата не в будущем (с запасом в 1 день)
            now = datetime.now()
            if parsed > now + timedelta(days=1):
                print(f"[WARN] Будущая дата обнаружена: {parsed}, отзыв будет пропущен")
                return None
            return parsed
        except Exception as e:
            print(f"[WARN] Ошибка парсинга ISO даты '{date_str}': {e}")
            return None

    # 3. Пробуем другие форматы через dateutil
    try:
        from dateutil import parser
        parsed = parser.parse(date_str, dayfirst=True)
        # Конвертируем в московское время если есть timezone
        if parsed.tzinfo:
            from zoneinfo import ZoneInfo
            moscow_tz = ZoneInfo("Europe/Moscow")
            parsed = parsed.astimezone(moscow_tz)
            parsed = parsed.replace(tzinfo=None)
        
        # Проверяем, что дата не в будущем (с запасом в 1 день)
        now = datetime.now()
        if parsed > now + timedelta(days=1):
            print(f"[WARN] Будущая дата обнаружена: {parsed}, отзыв будет пропущен")
            return None
        return parsed
    except Exception as e:
        print(f"[WARN] Ошибка при парсинге даты '{date_str}': {e}")
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
        # Проверяем, есть ли уже такой отзыв в базе (без учета user_id)
        # Нормализуем текст для сравнения
        normalized_text = data.get('text', '').strip().replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
        existing_query = select(Feedback).where(
            and_(
                Feedback.article == data.get('article'),
                Feedback.brand == brand,
                Feedback.author == data.get('author', 'Аноним'),
                Feedback.text == normalized_text
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


async def sync_feedbacks_with_soft_delete(
    db: AsyncSession,
    feedbacks_from_wb: List[Dict[str, Any]],
    brand: str,
    user_id: Optional[int] = None,
    history_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Синхронизация отзывов с поддержкой soft delete.
    
    Args:
        db: Сессия базы данных
        feedbacks_from_wb: Список отзывов с Wildberries
        brand: Бренд/магазин
        user_id: ID пользователя
        history_id: ID истории (опционально)
    
    Returns:
        Dict с статистикой синхронизации
    """
    from datetime import datetime
    
    # Получаем все отзывы из базы для данного бренда (без учета user_id)
    existing_query = select(Feedback).where(Feedback.brand == brand)
    existing_result = await db.execute(existing_query)
    existing_feedbacks = existing_result.scalars().all()
    
    # Создаем уникальные ключи для отзывов из WB (только по автору и тексту)
    wb_feedback_keys = set()
    for fb in feedbacks_from_wb:
        author = fb.get('author', 'Аноним')
        text = fb.get('text', '')
        # Нормализуем текст для сравнения
        normalized_text = text.strip().replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
        # Используем только автора и нормализованный текст для ключа (без даты)
        key = (author, normalized_text)
        wb_feedback_keys.add(key)
    
    # Создаем уникальные ключи для существующих отзывов
    existing_feedback_keys = set()
    for fb in existing_feedbacks:
        author = fb.author or 'Аноним'
        text = fb.text or ''
        # Нормализуем текст для сравнения
        normalized_text = text.strip().replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
        # Используем только автора и нормализованный текст для ключа (без даты)
        key = (author, normalized_text)
        existing_feedback_keys.add(key)
    
    # Статистика
    stats = {
        'total_wb_feedbacks': len(feedbacks_from_wb),
        'total_existing_feedbacks': len(existing_feedbacks),
        'new_feedbacks': 0,
        'restored_feedbacks': 0,
        'deleted_feedbacks': 0,
        'unchanged_feedbacks': 0
    }
    
    # 1. Помечаем как удалённые отзывы, которых нет на WB
    for fb in existing_feedbacks:
        author = fb.author or 'Аноним'
        text = fb.text or ''
        # Нормализуем текст для сравнения
        normalized_text = text.strip().replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
        key = (author, normalized_text)
        
        if key not in wb_feedback_keys and not fb.is_deleted:
            # Отзыв есть в базе, но нет на WB - помечаем как удалённый
            fb.is_deleted = True
            fb.deleted_at = moscow_now()
            stats['deleted_feedbacks'] += 1
        elif key in wb_feedback_keys and fb.is_deleted:
            # Отзыв есть на WB и в базе, но был помечен как удалённый - восстанавливаем
            fb.is_deleted = False
            fb.deleted_at = None
            stats['restored_feedbacks'] += 1
        elif key in wb_feedback_keys and not fb.is_deleted:
            # Отзыв есть и на WB, и в базе, и не удалён - без изменений
            stats['unchanged_feedbacks'] += 1
    
    # 2. Добавляем новые отзывы
    new_feedbacks = []
    for fb_data in feedbacks_from_wb:
        author = fb_data.get('author', 'Аноним')
        text = fb_data.get('text', '')
        # Нормализуем текст для сравнения
        normalized_text = text.strip().replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')
        key = (author, normalized_text)
        
        if key not in existing_feedback_keys:
            # Новый отзыв - добавляем в базу
            # Разбираем текст на части
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
                main_text = text
                pros_text = None
                cons_text = None
            
            # Обработка даты
            date_obj = None
            date_str = fb_data.get('date', '')
            if date_str and isinstance(date_str, str) and date_str.strip():
                date_obj = parse_wb_date(date_str)
            
            new_feedback = Feedback(
                article=fb_data.get('article'),
                brand=brand,
                author=author,
                rating=fb_data.get('rating', 0),
                date=date_obj,
                status=fb_data.get('status', 'Без подтверждения'),
                text=text,
                main_text=main_text,
                pros_text=pros_text,
                cons_text=cons_text,
                user_id=user_id,
                history_id=history_id,
                is_negative=1 if fb_data.get('rating', 0) <= 2 else 0,
                is_deleted=False,
                deleted_at=None
            )
            new_feedbacks.append(new_feedback)
            stats['new_feedbacks'] += 1
    
    # Сохраняем изменения
    if new_feedbacks:
        db.add_all(new_feedbacks)
    
    await db.commit()
    
    # Обновляем статистику
    stats['total_after_sync'] = len(existing_feedbacks) + len(new_feedbacks)
    
    print(f"[SYNC] Статистика синхронизации для {brand}:")
    print(f"  - Отзывов на WB: {stats['total_wb_feedbacks']}")
    print(f"  - Отзывов в базе: {stats['total_existing_feedbacks']}")
    print(f"  - Новых отзывов: {stats['new_feedbacks']}")
    print(f"  - Восстановленных: {stats['restored_feedbacks']}")
    print(f"  - Помеченных как удалённые: {stats['deleted_feedbacks']}")
    print(f"  - Без изменений: {stats['unchanged_feedbacks']}")
    
    return stats