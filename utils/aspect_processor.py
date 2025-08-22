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
                    reviews_texts.append("")
            
            # 2. Анализируем тексты через ИИ
            logger.info(f"Анализируем {len(reviews_texts)} отзывов через ИИ...")
            analysis_results = await ai_aspect_analyzer.analyze_batch(reviews_texts)
            
            if not analysis_results:
                return {
                    "processed": 0, 
                    "new_aspects": 0, 
                    "errors": ["Ошибка анализа через ИИ"]
                }
            
            # 3. Обрабатываем результаты анализа
            processed_count = 0
            new_aspects_count = 0
            errors = []
            
            for i, (feedback, analysis_result) in enumerate(zip(feedbacks_with_text, analysis_results)):
                try:
                    if analysis_result and "aspects" in analysis_result:
                        # Сохраняем аспекты в отзыв
                        feedback.aspects = analysis_result["aspects"]
                        
                        # Создаем новые аспекты в базе
                        for aspect_name, aspect_data in analysis_result["aspects"].items():
                            await self._create_or_update_aspect(aspect_name, aspect_data)
                            await self._save_feedback_aspect_relation(feedback.id, aspect_name, aspect_data)
                        
                        processed_count += 1
                        new_aspects_count += len(analysis_result["aspects"])
                        
                        logger.info(f"Обработан отзыв {feedback.id}: {len(analysis_result['aspects'])} аспектов")
                    else:
                        # Если анализ не удался, помечаем как пустой массив
                        feedback.aspects = []
                        processed_count += 1
                        
                except Exception as e:
                    error_msg = f"Ошибка при обработке отзыва {feedback.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 4. Сохраняем изменения в БД
            await self.db.commit()
            
            logger.info(f"Обработано отзывов: {processed_count}, новых аспектов: {new_aspects_count}")
            
            return {
                "processed": processed_count,
                "new_aspects": new_aspects_count,
                "errors": errors,
                "skipped_already_analyzed": skipped_already_analyzed
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке батча отзывов: {e}")
            await self.db.rollback()
            raise
    
    async def _create_or_update_aspect(self, name: str, aspect_data: Dict) -> Aspect:
        """Создает новый аспект или обновляет существующий"""
        
        # Проверяем, существует ли уже аспект
        existing_query = select(Aspect).where(Aspect.name == name)
        existing_result = await self.db.execute(existing_query)
        existing_aspect = existing_result.scalars().first()
        
        if existing_aspect:
            # Обновляем существующий аспект
            existing_aspect.usage_count += 1
            existing_aspect.description = aspect_data.get("description", existing_aspect.description)
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
            # Используем правильные PostgreSQL JSON функции
            query = select(Feedback).where(
                (Feedback.aspects.is_(None)) |      # NULL значения
                (func.json_typeof(Feedback.aspects) == 'null') |  # JSON null
                (func.json_typeof(Feedback.aspects) == 'array' & func.json_array_length(Feedback.aspects) == 0) |  # Пустые массивы
                (func.json_typeof(Feedback.aspects) == 'object' & func.json_object_keys(Feedback.aspects).is_(None))  # Пустые объекты
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
