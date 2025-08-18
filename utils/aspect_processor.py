import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from models.feedback import Feedback
from models.aspect import Aspect, FeedbackAspect
from utils.ai_aspect_analyzer import ai_aspect_analyzer
import json

logger = logging.getLogger(__name__)

class AspectProcessor:
    """Обработчик аспектов для отзывов"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def process_feedbacks_batch(self, feedbacks: List[Feedback], product_name: str = "") -> Dict:
        """Обрабатывает батч отзывов и создает аспекты"""
        
        if not feedbacks:
            return {"processed": 0, "new_aspects": 0, "errors": []}
        
        try:
            # Фильтруем отзывы - оставляем только те, где есть текст для анализа
            # И НЕ анализируем уже проанализированные отзывы
            feedbacks_with_text = []
            skipped_already_analyzed = 0
            
            for feedback in feedbacks:
                # Проверяем, не анализировался ли уже этот отзыв
                # Более строгая проверка для исключения повторного анализа
                if feedback.aspects:
                    # Проверяем различные варианты "пустых" аспектов
                    if (feedback.aspects != [] and 
                        feedback.aspects != '[]' and 
                        feedback.aspects != '{}' and
                        feedback.aspects != 'null' and
                        feedback.aspects != '[""]' and
                        feedback.aspects != '{}'):
                        
                        # Проверяем, есть ли реальные аспекты (не пустые строки)
                        has_real_aspects = False
                        if isinstance(feedback.aspects, list):
                            has_real_aspects = any(aspect and str(aspect).strip() for aspect in feedback.aspects)
                        elif isinstance(feedback.aspects, str):
                            # Парсим JSON строку если это возможно
                            try:
                                import json
                                parsed = json.loads(feedback.aspects)
                                if isinstance(parsed, list):
                                    has_real_aspects = any(aspect and str(aspect).strip() for aspect in parsed)
                                elif isinstance(parsed, dict):
                                    has_real_aspects = bool(parsed)
                            except:
                                has_real_aspects = bool(feedback.aspects.strip())
                        
                        if has_real_aspects:
                            skipped_already_analyzed += 1
                            continue
                
                has_text = False
                if feedback.text and feedback.text.strip():
                    has_text = True
                if feedback.main_text and feedback.main_text.strip():
                    has_text = True
                if feedback.pros_text and feedback.pros_text.strip():
                    has_text = True
                if feedback.cons_text and feedback.cons_text.strip():
                    has_text = True
                
                if has_text:
                    feedbacks_with_text.append(feedback)
            
            if not feedbacks_with_text:
                return {
                    "processed": 0, 
                    "new_aspects": 0, 
                    "errors": ["Нет отзывов для анализа"],
                    "skipped_already_analyzed": skipped_already_analyzed
                }
            
            # 1. Подготавливаем тексты отзывов для ИИ
            reviews_texts = []
            for feedback in feedbacks_with_text:
                # Объединяем все текстовые поля отзыва
                text_parts = []
                if feedback.text:
                    text_parts.append(feedback.text)
                if feedback.main_text:
                    text_parts.append(feedback.main_text)
                if feedback.pros_text:
                    text_parts.append(f"Достоинства: {feedback.pros_text}")
                if feedback.cons_text:
                    text_parts.append(f"Недостатки: {feedback.cons_text}")
                
                if text_parts:
                    full_text = " ".join(text_parts)
                    reviews_texts.append(full_text)
                else:
                    reviews_texts.append("")  # Пустой текст для отзывов без текста
            
            # 2. Анализируем через ИИ
            if ai_aspect_analyzer:
                # Используем безопасный батчевый анализатор с планировщиком
                ai_results = await ai_aspect_analyzer.analyze_reviews_safely_with_scheduler(
                    reviews_texts, product_name, max_batches_per_hour=20
                )
            else:
                ai_results = await self._basic_aspect_analysis(reviews_texts, feedbacks_with_text)
            
            # 3. Сохраняем результаты в БД
            save_results = await self._save_aspects_to_database(ai_results, feedbacks_with_text)
            
            # Добавляем информацию о пропущенных отзывах
            save_results["skipped_already_analyzed"] = skipped_already_analyzed
            
            return save_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке отзывов: {e}")
            raise
    
    async def process_feedbacks_safely_with_scheduler(self, feedbacks: List[Feedback], product_name: str = "", 
                                                    max_batches_per_hour: int = 20) -> Dict:
        """Безопасная обработка больших объемов отзывов с планировщиком и контролем лимитов"""
        
        if not feedbacks:
            return {"processed": 0, "new_aspects": 0, "errors": []}
        
        try:
            # Фильтруем отзывы - оставляем только те, где есть текст для анализа
            # И НЕ анализируем уже проанализированные отзывы
            feedbacks_with_text = []
            skipped_already_analyzed = 0
            
            for feedback in feedbacks:
                # Проверяем, не анализировался ли уже этот отзыв
                if feedback.aspects and feedback.aspects != [] and feedback.aspects != '[]' and feedback.aspects != '{}':
                    skipped_already_analyzed += 1
                    continue
                
                has_text = False
                if feedback.text and feedback.text.strip():
                    has_text = True
                if feedback.main_text and feedback.main_text.strip():
                    has_text = True
                if feedback.pros_text and feedback.pros_text.strip():
                    has_text = True
                if feedback.cons_text and feedback.cons_text.strip():
                    has_text = True
                
                if has_text:
                    feedbacks_with_text.append(feedback)
            
            if not feedbacks_with_text:
                return {
                    "processed": 0, 
                    "new_aspects": 0, 
                    "errors": ["Нет отзывов для анализа"],
                    "skipped_already_analyzed": skipped_already_analyzed
                }
            
            # 1. Подготавливаем тексты отзывов для ИИ
            reviews_texts = []
            for feedback in feedbacks_with_text:
                # Объединяем все текстовые поля отзыва
                text_parts = []
                if feedback.text:
                    text_parts.append(feedback.text)
                if feedback.main_text:
                    text_parts.append(feedback.main_text)
                if feedback.pros_text:
                    text_parts.append(f"Достоинства: {feedback.pros_text}")
                if feedback.cons_text:
                    text_parts.append(f"Недостатки: {feedback.cons_text}")
                
                if text_parts:
                    full_text = " ".join(text_parts)
                    reviews_texts.append(full_text)
                else:
                    reviews_texts.append("")  # Пустой текст для отзывов без текста
            
            # 2. Анализируем через ИИ с безопасным планировщиком
            if ai_aspect_analyzer:
                ai_results = await ai_aspect_analyzer.analyze_reviews_safely_with_scheduler(
                    reviews_texts, product_name, max_batches_per_hour
                )
            else:
                ai_results = await self._basic_aspect_analysis(reviews_texts, feedbacks_with_text)
            
            # 3. Сохраняем результаты в БД
            save_results = await self._save_aspects_to_database(ai_results, feedbacks_with_text)
            
            # Добавляем информацию о пропущенных отзывах
            save_results["skipped_already_analyzed"] = skipped_already_analyzed
            
            return save_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка при безопасной обработке отзывов: {e}")
            raise
    
    async def _basic_aspect_analysis(self, reviews_texts: List[str], feedbacks: List[Feedback]) -> List[Dict]:
        """Базовый анализ аспектов без ИИ (fallback)"""
        results = []
        
        for i, (text, feedback) in enumerate(zip(reviews_texts, feedbacks)):
            if not text.strip():
                continue
                
            # Простой анализ на основе рейтинга и ключевых слов
            aspects = {}
            
            # Анализируем рейтинг
            if feedback.rating <= 2:
                aspects["Качество"] = {
                    "sentiment": "negative",
                    "confidence": 0.7,
                    "evidence": ["низкий рейтинг"],
                    "category": "Качество",
                    "is_new_aspect": False
                }
            elif feedback.rating >= 4:
                aspects["Качество"] = {
                    "sentiment": "positive",
                    "confidence": 0.7,
                    "evidence": ["высокий рейтинг"],
                    "category": "Качество",
                    "is_new_aspect": False
                }
            
            # Анализируем текст на ключевые слова
            text_lower = text.lower()
            
            if any(word in text_lower for word in ["цена", "стоимость", "дорого", "дешево"]):
                aspects["Цена"] = {
                    "sentiment": "negative" if any(word in text_lower for word in ["дорого", "завышена"]) else "positive",
                    "confidence": 0.6,
                    "evidence": ["упоминание цены"],
                    "category": "Цена",
                    "is_new_aspect": False
                }
            
            if any(word in text_lower for word in ["эффект", "результат", "помогает", "действует"]):
                aspects["Эффективность"] = {
                    "sentiment": "positive" if any(word in text_lower for word in ["помогает", "действует"]) else "negative",
                    "confidence": 0.6,
                    "evidence": ["упоминание эффективности"],
                    "category": "Эффективность",
                    "is_new_aspect": False
                }
            
            results.append({
                "review_index": i,
                "aspects": aspects
            })
        
        return results
    
    async def _save_aspects_to_database(self, ai_results: List[Dict], feedbacks: List[Feedback]) -> Dict:
        """Сохраняет аспекты в БД и связывает с отзывами"""
        
        processed_count = 0
        new_aspects_count = 0
        errors = []
        
        for ai_review in ai_results:
            try:
                review_index = ai_review["review_index"]
                if review_index >= len(feedbacks):
                    logger.warning(f"Индекс отзыва {review_index} превышает количество отзывов")
                    continue
                
                feedback = feedbacks[review_index]
                aspects_data = []
                
                # Обрабатываем каждый аспект
                for aspect_name, aspect_data in ai_review.get("aspects", {}).items():
                    try:
                        # Создаем или получаем аспект
                        aspect = await self._create_or_get_aspect(aspect_name, aspect_data)
                        if aspect.is_new_aspect:
                            new_aspects_count += 1
                        
                        # Формируем данные для поля aspects в feedbacks
                        aspect_info = {
                            "name": aspect_name,
                            "sentiment": aspect_data["sentiment"],
                            "confidence": aspect_data["confidence"],
                            "evidence": aspect_data["evidence"],
                            "category": aspect_data["category"],
                            "is_new": aspect_data.get("is_new_aspect", False)
                        }
                        aspects_data.append(aspect_info)
                        
                        # Сохраняем связь в таблице feedback_aspects только для сохраненных отзывов
                        if feedback.id is not None:
                            await self._save_feedback_aspect_relation(
                                feedback.id, aspect_name, aspect_data
                            )
                        
                    except Exception as e:
                        logger.error(f"Ошибка при обработке аспекта {aspect_name}: {e}")
                        errors.append(f"Аспект {aspect_name}: {str(e)}")
                
                # Обновляем поле aspects в таблице feedbacks
                if aspects_data:
                    feedback.aspects = aspects_data
                    processed_count += 1
                
            except Exception as e:
                logger.error(f"Ошибка при обработке отзыва {review_index}: {e}")
                errors.append(f"Отзыв {review_index}: {str(e)}")
        
        # Сохраняем все изменения
        try:
            await self.db.commit()
            logger.info(f"💾 Сохранено в БД: {processed_count} отзывов")
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении в БД: {e}")
            await self.db.rollback()
            raise
        
        return {
            "processed": processed_count,
            "new_aspects": new_aspects_count,
            "errors": errors
        }
    
    async def _create_or_get_aspect(self, name: str, aspect_data: Dict) -> Aspect:
        """Создает новый аспект или возвращает существующий"""
        
        # Проверяем, существует ли уже такой аспект
        existing = await self.db.execute(
            select(Aspect).where(Aspect.name == name)
        )
        existing_aspect = existing.scalar_one_or_none()
        
        if existing_aspect:
            # Обновляем счетчик использования
            await self.db.execute(
                update(Aspect)
                .where(Aspect.id == existing_aspect.id)
                .values(usage_count=Aspect.usage_count + 1, last_used=func.now())
            )
            logger.debug(f"Обновлен счетчик использования для аспекта: {name}")
            return existing_aspect
        
        # Создаем новый аспект
        new_aspect = Aspect(
            name=name,
            category=aspect_data.get("category", "Общие"),
            description=aspect_data.get("description", ""),
            is_base_aspect=False,
            is_new_aspect=aspect_data.get("is_new_aspect", False),
            usage_count=1
        )
        
        self.db.add(new_aspect)
        logger.info(f"Создан новый аспект: {name} в категории {aspect_data.get('category', 'Общие')}")
        return new_aspect
    
    async def _save_feedback_aspect_relation(self, feedback_id: int, aspect_name: str, aspect_data: Dict):
        """Сохраняет связь аспекта с отзывом"""
        
        # Создаем связь в таблице feedback_aspects
        relation = FeedbackAspect(
            feedback_id=feedback_id,
            aspect_name=aspect_name,
            sentiment=aspect_data["sentiment"],
            confidence=int(aspect_data["confidence"] * 100),  # Конвертируем в 0-100
            evidence_words=json.dumps(aspect_data["evidence"], ensure_ascii=False)
        )
        
        self.db.add(relation)
    
    async def get_aspect_statistics(self) -> Dict:
        """Возвращает статистику по аспектам"""
        try:
            # Общее количество аспектов
            total_result = await self.db.execute(select(func.count(Aspect.id)))
            total_aspects = total_result.scalar()
            
            # Количество новых аспектов
            new_result = await self.db.execute(
                select(func.count(Aspect.id)).where(Aspect.is_new_aspect == True)
            )
            new_aspects = new_result.scalar()
            
            # Топ аспектов по использованию
            top_result = await self.db.execute(
                select(Aspect.name, Aspect.usage_count, Aspect.category)
                .order_by(Aspect.usage_count.desc())
                .limit(10)
            )
            top_aspects = [{"name": name, "usage": usage, "category": category} 
                          for name, usage, category in top_result]
            
            # Статистика по категориям
            category_result = await self.db.execute(
                select(Aspect.category, func.count(Aspect.id))
                .group_by(Aspect.category)
                .order_by(func.count(Aspect.id).desc())
            )
            categories = [{"name": category, "count": count} 
                         for category, count in category_result]
            
            return {
                "total_aspects": total_aspects,
                "new_aspects": new_aspects,
                "top_aspects": top_aspects,
                "categories": categories
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики аспектов: {e}")
            return {}
    
    async def process_existing_feedbacks(self, brand: str = None, limit: int = 100) -> Dict:
        """Обрабатывает существующие отзывы без аспектов"""
        
        try:
            # Получаем отзывы без аспектов (только те, которые еще не анализировались)
            # Более точный поиск для исключения уже проанализированных отзывов
            query = select(Feedback).where(
                (Feedback.aspects.is_(None)) |      # NULL значения
                (Feedback.aspects == []) |          # Пустые списки
                (Feedback.aspects == '[]') |        # Пустые JSON массивы
                (Feedback.aspects == '{}') |        # Пустые JSON объекты
                (Feedback.aspects == 'null') |      # Строка "null"
                (Feedback.aspects == '[""]')        # Массив с пустой строкой
            )
            
            if brand:
                query = query.where(Feedback.brand == brand)
            
            query = query.limit(limit)
            
            result = await self.db.execute(query)
            feedbacks = result.scalars().all()
            
            if not feedbacks:
                return {"processed": 0, "new_aspects": 0, "errors": ["Нет отзывов для анализа"]}
            
            # Обрабатываем отзывы батчем
            return await self.process_feedbacks_batch(feedbacks)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обработке существующих отзывов: {e}")
            raise
