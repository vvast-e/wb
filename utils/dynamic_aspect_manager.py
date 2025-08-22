import logging
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
import json

logger = logging.getLogger(__name__)

class Aspect:
    """Модель для аспектов"""
    def __init__(self, name: str, category: str, description: str = "", is_base_aspect: bool = False, is_new_aspect: bool = False, usage_count: int = 0):
        self.name = name
        self.category = category
        self.description = description
        self.is_base_aspect = is_base_aspect
        self.is_new_aspect = is_new_aspect
        self.usage_count = usage_count

class AspectCategory:
    """Модель для категорий аспектов"""
    def __init__(self, name: str, description: str = "", color: str = "#3B82F6"):
        self.name = name
        self.description = description
        self.color = color

class DynamicAspectManager:
    """Менеджер для управления динамическими аспектами"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.base_aspects = self._get_base_aspects()
        self.aspect_categories = self._get_aspect_categories()
    
    def _get_base_aspects(self) -> List[str]:
        """Возвращает список базовых аспектов"""
        return [
            "Цена", "Качество", "Эффективность", "Упаковка", "Запах", 
            "Консистенция", "Объем", "Состав", "Доставка", "Эмоция", 
            "Ожидания", "Безопасность", "Удобство", "Внешний вид"
        ]
    
    def _get_aspect_categories(self) -> List[AspectCategory]:
        """Возвращает список категорий аспектов"""
        return [
            AspectCategory("Технические характеристики", "Качество и надежность механизмов", "#EF4444"),
            AspectCategory("Безопасность", "Биосовместимость и гипоаллергенность", "#10B981"),
            AspectCategory("Удобство", "Эргономика и практичность", "#F59E0B"),
            AspectCategory("Эффективность", "Результативность и действенность", "#8B5CF6"),
            AspectCategory("Практичность", "Экономичность и расход", "#06B6D4"),
            AspectCategory("Восприятие", "Аромат, вкус, внешний вид", "#EC4899"),
            AspectCategory("Качество", "Общее качество товара", "#6366F1"),
            AspectCategory("Цена", "Стоимость и ценность", "#84CC16"),
            AspectCategory("Общие", "Общие характеристики", "#6B7280")
        ]
    
    async def process_ai_response(self, ai_response: List[Dict]) -> Dict:
        """Обрабатывает ответ ИИ и создает новые аспекты"""
        processed_results = []
        new_aspects_created = []
        
        for review_data in ai_response:
            processed_review = await self._process_single_review(review_data)
            processed_results.append(processed_review)
            
            # Собираем новые аспекты
            for aspect_name, aspect_data in review_data.get("aspects", {}).items():
                if aspect_data.get("is_new_aspect", False):
                    new_aspect = await self._create_or_get_aspect(
                        name=aspect_name,
                        category=aspect_data.get("category", "Общие"),
                        description=aspect_data.get("description", "")
                    )
                    new_aspects_created.append(new_aspect)
        
        return {
            "processed_reviews": processed_results,
            "new_aspects": new_aspects_created
        }
    
    async def _process_single_review(self, review_data: Dict) -> Dict:
        """Обрабатывает данные одного отзыва"""
        processed_review = {
            "review_index": review_data.get("review_index", 0),
            "aspects": {}
        }
        
        for aspect_name, aspect_data in review_data.get("aspects", {}).items():
            # Нормализуем аспект
            normalized_aspect = await self._normalize_aspect(aspect_name, aspect_data)
            processed_review["aspects"][aspect_name] = normalized_aspect
        
        return processed_review
    
    async def _create_or_get_aspect(self, name: str, category: str, description: str) -> Aspect:
        """Создает новый аспект или возвращает существующий"""
        # В реальной реализации здесь был бы запрос к БД
        # Пока создаем объект в памяти
        
        # Проверяем, существует ли уже такой аспект
        existing_aspect = self._find_existing_aspect(name)
        
        if existing_aspect:
            # Обновляем счетчик использования
            existing_aspect.usage_count += 1
            logger.info(f"Обновлен счетчик использования для аспекта: {name}")
            return existing_aspect
        
        # Создаем новый аспект
        new_aspect = Aspect(
            name=name,
            category=category,
            description=description,
            is_new_aspect=True,
            usage_count=1
        )
        
        logger.info(f"Создан новый аспект: {name} в категории {category}")
        return new_aspect
    
    def _find_existing_aspect(self, name: str) -> Optional[Aspect]:
        """Ищет существующий аспект по имени"""
        # В реальной реализации здесь был бы запрос к БД
        # Пока возвращаем None для демонстрации
        return None
    
    async def _normalize_aspect(self, aspect_name: str, aspect_data: Dict) -> Dict:
        """Нормализует данные аспекта"""
        normalized = {
            "sentiment": aspect_data.get("sentiment", "neutral"),
            "confidence": aspect_data.get("confidence", 0.5),
            "evidence": aspect_data.get("evidence", []),
            "category": aspect_data.get("category", "Общие"),
            "is_new_aspect": aspect_data.get("is_new_aspect", False),
            "description": aspect_data.get("description", "")
        }
        
        # Добавляем дополнительные поля
        if "sub_aspects" in aspect_data:
            normalized["sub_aspects"] = aspect_data["sub_aspects"]
        
        if "related_aspects" in aspect_data:
            normalized["related_aspects"] = aspect_data["related_aspects"]
        
        if "medical" in aspect_data:
            normalized["medical"] = aspect_data["medical"]
        
        return normalized
    
    async def get_aspect_statistics(self) -> Dict:
        """Возвращает статистику по аспектам"""
        # В реальной реализации здесь был бы запрос к БД
        return {
            "total_aspects": len(self.base_aspects),
            "categories": [cat.name for cat in self.aspect_categories],
            "most_used_aspects": self._get_most_used_aspects()
        }
    
    def _get_most_used_aspects(self) -> List[Dict]:
        """Возвращает наиболее используемые аспекты"""
        # В реальной реализации здесь был бы запрос к БД
        return [
            {"name": "Цена", "usage_count": 150},
            {"name": "Качество", "usage_count": 120},
            {"name": "Эффективность", "usage_count": 100}
        ]
    
    async def suggest_category_for_aspect(self, aspect_name: str, evidence: List[str]) -> str:
        """Предлагает категорию для нового аспекта"""
        text = f"{aspect_name} {' '.join(evidence)}".lower()
        
        # Определяем категорию по ключевым словам
        category_keywords = {
            "Технические характеристики": ["сломался", "работает", "функция", "механизм", "дозатор", "флакон"],
            "Безопасность": ["аллергия", "раздражение", "безопасно", "риск", "реакция", "побочные"],
            "Удобство": ["удобно", "неудобно", "практично", "эргономично", "просто", "сложно"],
            "Эффективность": ["эффект", "результат", "действует", "помогает", "лечит"],
            "Практичность": ["закончился", "расход", "экономично", "достаточно", "быстро"],
            "Восприятие": ["запах", "вкус", "внешний вид", "ощущения", "нравится", "не нравится"]
        }
        
        best_category = "Общие"
        max_score = 0
        
        for category, keywords in category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > max_score:
                max_score = score
                best_category = category
        
        return best_category
    
    async def merge_similar_aspects(self, aspects: List[str]) -> List[str]:
        """Объединяет похожие аспекты"""
        # Простая логика объединения похожих аспектов
        merged = []
        used = set()
        
        for aspect in aspects:
            if aspect in used:
                continue
            
            # Ищем похожие аспекты
            similar = [aspect]
            for other in aspects:
                if other not in used and self._are_aspects_similar(aspect, other):
                    similar.append(other)
                    used.add(other)
            
            # Выбираем лучший аспект из группы
            best_aspect = self._select_best_aspect(similar)
            merged.append(best_aspect)
            used.add(aspect)
        
        return merged
    
    def _are_aspects_similar(self, aspect1: str, aspect2: str) -> bool:
        """Проверяет схожесть аспектов"""
        words1 = set(aspect1.lower().split())
        words2 = set(aspect2.lower().split())
        
        # Если есть общие слова, считаем аспекты похожими
        common_words = words1.intersection(words2)
        return len(common_words) > 0
    
    def _select_best_aspect(self, aspects: List[str]) -> str:
        """Выбирает лучший аспект из группы"""
        if not aspects:
            return ""
        
        # Приоритет базовым аспектам
        for aspect in aspects:
            if aspect in self.base_aspects:
                return aspect
        
        # Возвращаем первый аспект
        return aspects[0]

# Создаем глобальный экземпляр менеджера
dynamic_aspect_manager = None

def get_dynamic_aspect_manager(db_session: AsyncSession) -> DynamicAspectManager:
    """Возвращает экземпляр менеджера динамических аспектов"""
    global dynamic_aspect_manager
    if dynamic_aspect_manager is None:
        dynamic_aspect_manager = DynamicAspectManager(db_session)
    return dynamic_aspect_manager








