from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
import re
import logging

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
    history_id: Optional[int] = None,
    aspects: Optional[Dict[str, List[str]]] = None
) -> Feedback:
    """Создание нового отзыва"""
    # Определяем негативность по рейтингу (1-2 = негативный, 3 = нейтральный, 4-5 = позитивный)
    is_negative = 1 if rating <= 2 else 0
    
    feedback = Feedback(
        article=str(article),  # Конвертируем артикул в строку
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
        is_negative=is_negative,
        aspects=aspects
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
        stmt = stmt.where(Feedback.article == str(article))
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
        stmt = stmt.where(Feedback.article == str(article))
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
    Парсинг даты из Wildberries API с поддержкой ISO-формата с Z (например, 2025-07-22T22:30:23Z)
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    if not date_str:
        return None
    
    # 1. ISO-формат с Z (UTC): "2025-07-22T22:30:23Z"
    try:
        if date_str.endswith('Z'):
            # Используем более точный формат для парсинга
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            # Переводим в московское время
            msk = ZoneInfo("Europe/Moscow")
            dt = dt.replace(tzinfo=timezone.utc).astimezone(msk)
            result = dt.replace(tzinfo=None)
            return result
        # 2. ISO-формат без Z
        elif 'T' in date_str:
            dt = datetime.fromisoformat(date_str)
            return dt
    except Exception as e:
        print(f"[ERROR] parse_wb_date: не удалось распарсить ISO формат '{date_str}': {e}")
    
    # 3. Старый формат (русский) — если вдруг встретится
    import re
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
        try:
            parsed = datetime.strptime(parsed_date_str, "%Y-%m-%d %H:%M")
            if year_was_missing and parsed > now:
                parsed = parsed.replace(year=parsed.year - 1)
            if parsed > now:
                print(f"[WARN] Будущая дата обнаружена: {parsed}, отзыв будет пропущен")
                return None
            return parsed
        except Exception as e:
            print(f"[ERROR] strptime fail for '{parsed_date_str}': {e}")
            return None
    
    # 4. Если ничего не подошло
    print(f"[WARN] parse_wb_date: не удалось распарсить дату '{date_str}' - неизвестный формат")
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
        date_str = data.get('createdDate')
        date_obj = None
        if date_str and isinstance(date_str, str) and date_str.strip():
            date_obj = parse_wb_date(date_str)
            if date_obj is None:
                print(f"[WARN] Не удалось распарсить дату: '{date_str}' для отзыва: {data}")
        
        # Определяем негативность по рейтингу (1-2 = негативный, 3 = нейтральный, 4-5 = позитивный)
        rating = data.get('productValuation', 0)
        is_negative = 1 if rating <= 3 else 0
        
        # Анализируем аспекты отзыва используя новую систему аспектов
        aspects = None  # Убираем анализ аспектов из парсинга - будет анализироваться отдельно
        
        # Проверяем, есть ли текст для анализа
        has_text_for_analysis = False
        if text and text.strip():
            has_text_for_analysis = True
        if main_text and main_text.strip():
            has_text_for_analysis = True
        if pros_text and pros_text.strip():
            has_text_for_analysis = True
        if cons_text and cons_text.strip():
            has_text_for_analysis = True
        
        if has_text_for_analysis:
            # Просто помечаем, что отзыв готов к анализу аспектов
            pass  # Анализ будет происходить отдельно через планировщик
        else:
            logger.info(f"Отзыв {data.get('article', 'unknown')} пропущен - нет текста для анализа аспектов")
        
        feedback = Feedback(
            article=str(data.get('article', '')),  # Конвертируем артикул в строку
            brand=brand,
            author=data.get('author', 'Аноним'),
            rating=rating,
            date=date_obj,
            status=data.get('status', 'Без подтверждения'),
            text=text,
            main_text=main_text,
            pros_text=pros_text,
            cons_text=cons_text,
            user_id=user_id,
            history_id=history_id,
            is_negative=is_negative,
            aspects=aspects,  # Добавляем проанализированные аспекты
            wb_id=str(data.get('wb_id', ''))  # Конвертируем в строку
        )
        
        feedbacks.append(feedback)
    
    if feedbacks:
        db.add_all(feedbacks)
        await db.commit()
        
        for feedback in feedbacks:
            await db.refresh(feedback)
            
            # Обновляем отслеживание времени в топах после сохранения
            try:
                from crud.analytics import update_feedback_top_tracking
                await update_feedback_top_tracking(
                    db=db,
                    feedback_id=feedback.id,
                    article=feedback.article,
                    brand=feedback.brand,
                    user_id=user_id,
                    feedback_date=feedback.date,
                    is_negative=bool(feedback.is_negative)
                )
            except Exception as e:
                print(f"[WARN] Не удалось обновить топ-трекинг для отзыва {feedback.id}: {e}")
    
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
            Feedback.is_processed == 0,
            Feedback.is_deleted == False
        )
    ).options(joinedload(Feedback.user))
    
    if brand:
        stmt = stmt.where(Feedback.brand == brand)
    
    stmt = stmt.order_by(desc(Feedback.created_at)).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()


async def sync_feedbacks_with_soft_delete_optimized(
    db: AsyncSession,
    feedbacks_from_wb: List[Dict[str, Any]],
    brand: str,
    user_id: Optional[int] = None,
    history_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Оптимизированная синхронизация отзывов с поддержкой soft delete по wb_id.
    """
    from datetime import datetime
    logger = logging.getLogger("feedback_sync")
    logger.setLevel(logging.INFO)
    
    # Очищаем существующие хендлеры
    logger.handlers.clear()
    
    # Хендлер для файла
    file_handler = logging.FileHandler("feedback_sync.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(file_handler)
    
    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("[SYNC] %(levelname)s: %(message)s"))
    logger.addHandler(console_handler)
    logger.info(f"=== СТАРТ ОПТИМИЗИРОВАННОЙ СИНХРОНИЗАЦИИ ДЛЯ БРЕНДА: {brand} ===")
    logger.info(f"Отзывов из WB: {len(feedbacks_from_wb)}")

    # ОПТИМИЗАЦИЯ 1: Загружаем только wb_id вместо всех полей
    existing_query = select(Feedback.wb_id, Feedback.id, Feedback.is_deleted).where(
        and_(Feedback.brand == brand, Feedback.wb_id.isnot(None))
    )
    existing_result = await db.execute(existing_query)
    existing_feedbacks_data = existing_result.fetchall()

    logger.info(f"Существующих отзывов в БД: {len(existing_feedbacks_data)}")

    # Создаем словари для быстрого поиска
    wb_ids = set(fb['id'] for fb in feedbacks_from_wb)
    existing_wb_ids = {row.wb_id for row in existing_feedbacks_data}
    existing_feedback_map = {row.wb_id: (row.id, row.is_deleted) for row in existing_feedbacks_data}

    logger.info(f"Уникальных wb_id из WB: {len(wb_ids)}")
    logger.info(f"Уникальных wb_id в БД: {len(existing_wb_ids)}")

    stats = {
        'total_wb_feedbacks': len(feedbacks_from_wb),
        'total_existing_feedbacks': len(existing_feedbacks_data),
        'new_feedbacks': 0,
        'restored_feedbacks': 0,
        'deleted_feedbacks': 0,
        'unchanged_feedbacks': 0
    }

    # ОПТИМИЗАЦИЯ 2: Батчевые операции для обновлений
    to_delete = []
    to_restore = []
    
    # 1. Помечаем как удалённые отзывы, которых нет на WB
    logger.info("Проверяем отзывы для soft delete...")
    for wb_id, (feedback_id, is_deleted) in existing_feedback_map.items():
        if wb_id not in wb_ids and not is_deleted:
            to_delete.append(feedback_id)
            stats['deleted_feedbacks'] += 1
        elif wb_id in wb_ids and is_deleted:
            to_restore.append(feedback_id)
            stats['restored_feedbacks'] += 1
        elif wb_id in wb_ids and not is_deleted:
            stats['unchanged_feedbacks'] += 1

    # Батчевое обновление удаленных отзывов
    if to_delete:
        await db.execute(
            update(Feedback)
            .where(Feedback.id.in_(to_delete))
            .values(is_deleted=True, deleted_at=moscow_now())
        )
        logger.info(f"Помечено как удаленных: {len(to_delete)}")

    # Батчевое восстановление отзывов
    if to_restore:
        await db.execute(
            update(Feedback)
            .where(Feedback.id.in_(to_restore))
            .values(is_deleted=False, deleted_at=None)
        )
        logger.info(f"Восстановлено: {len(to_restore)}")

    logger.info("Статистика после soft delete:")
    logger.info(f"  Удаленных: {stats['deleted_feedbacks']}")
    logger.info(f"  Восстановленных: {stats['restored_feedbacks']}")
    logger.info(f"  Без изменений: {stats['unchanged_feedbacks']}")

    # 2. Добавляем новые отзывы
    logger.info("Добавляем новые отзывы...")
    
    # Логируем структуру первых 3 отзывов для отладки
    for i, fb_data in enumerate(feedbacks_from_wb[:3]):
        logger.info(f"ПРИМЕР ОТЗЫВА {i+1}: {fb_data}")
    
    new_feedbacks = []
    for fb_data in feedbacks_from_wb:
        if fb_data['id'] not in existing_wb_ids:
            # Обработка даты - используем поле 'date' из парсера
            date_obj = None
            date_str = fb_data.get('date', '')
            if date_str and isinstance(date_str, str) and date_str.strip():
                date_obj = parse_wb_date(date_str)
                if date_obj is None:
                    logger.warning(f"Не удалось распарсить дату: '{date_str}' для отзыва {fb_data['id']}")
            
            # Извлекаем имя пользователя - используем поле 'author' из парсера
            author_name = fb_data.get('author', 'Аноним')
            if not author_name or author_name.strip() == '':
                author_name = 'Аноним'
            
            # Извлекаем рейтинг - используем поле 'rating' из парсера
            rating = fb_data.get('rating', 0)
            
            # Определяем негативность по рейтингу (1-2 = негативный, 3 = нейтральный, 4-5 = позитивный)
            is_negative = 1 if rating <= 2 else 0
            
            # Детальное логирование для отладки
            logger.info(f"Обрабатываем отзыв {fb_data['id']}: rating={rating}, is_negative={is_negative}, author='{author_name}', date='{date_str}' -> {date_obj}")
            
            # Аспекты будут анализироваться отдельно через планировщик
            aspects = None  # Убираем анализ аспектов из синхронизации

            new_feedback = Feedback(
                wb_id=str(fb_data['id']),  # Конвертируем в строку
                article=str(fb_data.get('article', '')),  # Конвертируем артикул в строку
                brand=brand,
                author=author_name,
                rating=rating,
                date=date_obj,
                status=fb_data.get('status', 'Без подтверждения'),  # Используем поле 'status' из парсера
                text=fb_data.get('text', ''),
                main_text=fb_data.get('text', ''),
                pros_text=fb_data.get('pros', ''),
                cons_text=fb_data.get('cons', ''),
                user_id=user_id,
                history_id=history_id,
                is_negative=is_negative,
                is_deleted=False,
                deleted_at=None,
                aspects=aspects  # Добавляем проанализированные аспекты
            )
            new_feedbacks.append(new_feedback)
            stats['new_feedbacks'] += 1

    logger.info(f"Новых отзывов для добавления: {len(new_feedbacks)}")

    # ОПТИМИЗАЦИЯ 3: Батчевое добавление новых отзывов
    BATCH_SIZE = 1000
    if new_feedbacks:
        for i in range(0, len(new_feedbacks), BATCH_SIZE):
            batch = new_feedbacks[i:i + BATCH_SIZE]
            db.add_all(batch)
            await db.commit()
            logger.info(f"Добавлен батч {i//BATCH_SIZE + 1}: {len(batch)} отзывов")

    stats['total_after_sync'] = len(existing_feedbacks_data) + len(new_feedbacks)
    logger.info(f"Статистика оптимизированной синхронизации для {brand}: {stats}")
    
    logger.info("ИТОГОВАЯ СТАТИСТИКА ОПТИМИЗИРОВАННОЙ СИНХРОНИЗАЦИИ:")
    logger.info(f"  Всего отзывов из WB: {stats['total_wb_feedbacks']}")
    logger.info(f"  Существующих в БД: {stats['total_existing_feedbacks']}")
    logger.info(f"  Новых: {stats['new_feedbacks']}")
    logger.info(f"  Восстановленных: {stats['restored_feedbacks']}")
    logger.info(f"  Удаленных: {stats['deleted_feedbacks']}")
    logger.info(f"  Без изменений: {stats['unchanged_feedbacks']}")
    logger.info(f"  Всего после синхронизации: {stats['total_after_sync']}")
    
    return stats