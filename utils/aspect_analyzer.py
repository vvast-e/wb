import re
import logging
from typing import List, Dict, Set
from collections import Counter
import asyncio

logger = logging.getLogger(__name__)

class AspectAnalyzer:
    """Анализатор аспектов товаров на основе правил и простого ИИ"""

    def __init__(self):
        self.aspect_keywords = {
            "Эффективность": ["эффект", "результат", "действие", "работает", "помогает", "лечит"],
            "Качество": ["качество", "хороший", "плохой", "отличный", "ужасный"],
            "Цена": ["цена", "стоимость", "дорого", "дешево", "стоит", "платить"],
            "Упаковка": ["упаковка", "банка", "флакон", "тюбик", "коробка", "дозатор"],
            "Состав": ["состав", "ингредиенты", "компоненты", "вещества", "химия"],
            "Запах": ["запах", "аромат", "духи", "пахнет", "ароматный"],
            "Консистенция": ["консистенция", "густой", "жидкий", "крем", "гель", "масло"],
            "Объем": ["объем", "количество", "мл", "грамм", "размер"],
            "Доставка": ["доставка", "привезли", "получил", "курьер", "почта"],
            "Эмоция": ["нравится", "люблю", "ненавижу", "доволен", "разочарован"],
            "Ожидания": ["ожидал", "надеялся", "думал", "предполагал"],
            "Безопасность": ["безопасно", "аллергия", "раздражение", "побочные эффекты"],
            "Удобство": ["удобно", "просто", "легко", "сложно", "неудобно"],
            "Внешний вид": ["красивый", "дизайн", "цвет", "форма", "стильный"],
            "Долговечность": ["долго", "быстро", "изнашивается", "прочный", "хрупкий"]
        }

        self.standard_aspects = [
            "Эффект", "Эмоция", "Ожидания", "Консистенция",
            "Состав", "Объём", "Упаковка", "Цена", "Доставка"
        ]

        self.synonym_journal = [
            "Реакции кожи = Аллергические реакции = Аллергия",
            "Упаковка = Дозатор = Флакон = Банка",
            "Густота волос = Плотность волос = Объем волос",
            "Эффективность = Результат = Результаты = Эффект = Действие",
            "Качество = Уровень = Стандарт",
            "Цена = Стоимость = Стоит",
            "Запах = Аромат = Духи",
            "Консистенция = Текстура = Структура",
            "Доставка = Получение = Привоз",
            "Эмоция = Чувства = Отношение"
        ]

        # Словари для определения тональности аспектов
        self.positive_indicators = [
            "хороший", "отличный", "прекрасный", "великолепный", "замечательный",
            "эффективный", "действенный", "результативный", "помогает", "лечит",
            "нравится", "люблю", "доволен", "рад", "счастлив", "приятный",
            "удобный", "простой", "легкий", "быстрый", "качественный",
            "красивый", "стильный", "модный", "современный", "прочный"
        ]
        
        self.negative_indicators = [
            "плохой", "ужасный", "отвратительный", "неэффективный", "бесполезный",
            "не помогает", "не лечит", "не нравится", "ненавижу", "разочарован",
            "неудобный", "сложный", "трудный", "медленный", "некачественный",
            "уродливый", "старомодный", "хрупкий", "ломается", "аллергия",
            "раздражение", "побочные эффекты", "дорого", "переплата"
        ]

    async def analyze_reviews(self, reviews: List[str], product_name: str = "") -> Dict[str, List[str]]:
        """Анализ отзывов и формирование словарей аспектов"""
        try:
            # Извлекаем аспекты из отзывов
            general_dict = await self._extract_aspects_from_reviews(reviews)
            
            # Убираем дубли
            no_duplicates_dict = await self._remove_duplicates(general_dict)
            
            # Убираем синонимы
            no_synonyms_dict = await self._remove_synonyms(no_duplicates_dict)
            
            return {
                "general_dictionary": general_dict,
                "no_duplicates_dictionary": no_duplicates_dict,
                "no_synonyms_dictionary": no_synonyms_dict
            }
        except Exception as e:
            logger.error(f"Ошибка при анализе отзывов: {e}")
            raise

    async def analyze_single_review(self, review_text: str, rating: int) -> Dict[str, List[str]]:
        """Анализ одного отзыва для определения аспектов с тональностью"""
        try:
            # Извлекаем аспекты из одного отзыва
            aspects = await self._extract_aspects_from_reviews([review_text])
            
            # Определяем тональность аспектов на основе рейтинга и текста
            positive_aspects = []
            negative_aspects = []
            
            for aspect in aspects:
                sentiment = self._determine_aspect_sentiment(aspect, review_text, rating)
                if sentiment == "positive":
                    positive_aspects.append(aspect)
                elif sentiment == "negative":
                    negative_aspects.append(aspect)
            
            # Ограничиваем количество аспектов до 3 положительных и 3 отрицательных
            positive_aspects = positive_aspects[:3]
            negative_aspects = negative_aspects[:3]
            
            return {
                "positive": positive_aspects,
                "negative": negative_aspects
            }
        except Exception as e:
            logger.error(f"Ошибка при анализе одного отзыва: {e}")
            return {"positive": [], "negative": []}

    def _determine_aspect_sentiment(self, aspect: str, review_text: str, rating: int) -> str:
        """Определение тональности аспекта на основе рейтинга и текста"""
        # Базовое определение по рейтингу
        if rating <= 2:
            base_sentiment = "negative"
        elif rating >= 4:
            base_sentiment = "positive"
        else:
            base_sentiment = "neutral"
        
        # Анализ текста для уточнения тональности
        text_lower = review_text.lower()
        aspect_lower = aspect.lower()
        
        # Ищем ключевые слова для аспекта
        aspect_keywords = self.aspect_keywords.get(aspect, [])
        
        # Проверяем позитивные и негативные индикаторы рядом с аспектами
        positive_count = 0
        negative_count = 0
        
        for keyword in aspect_keywords:
            if keyword in text_lower:
                keyword_idx = text_lower.find(keyword)
                
                # Ищем позитивные слова рядом с ключевым словом аспекта
                for positive_indicator in self.positive_indicators:
                    if positive_indicator in text_lower:
                        pos_idx = text_lower.find(positive_indicator)
                        if abs(pos_idx - keyword_idx) <= 20:  # В пределах 20 символов
                            positive_count += 1
                
                # Ищем негативные слова рядом с ключевым словом аспекта
                for negative_indicator in self.negative_indicators:
                    if negative_indicator in text_lower:
                        neg_idx = text_lower.find(negative_indicator)
                        if abs(neg_idx - keyword_idx) <= 20:  # В пределах 20 символов
                            negative_count += 1
                
                # Также проверяем отрицания (не, неэффективный, неприятный и т.д.)
                # Ищем слова с отрицанием рядом с ключевым словом
                words_around = text_lower[max(0, keyword_idx-30):keyword_idx+30].split()
                for i, word in enumerate(words_around):
                    if word in aspect_keywords and i > 0:
                        prev_word = words_around[i-1]
                        if prev_word.startswith('не') or prev_word in ['плохой', 'ужасный', 'отвратительный']:
                            negative_count += 1
                        elif prev_word in ['хороший', 'отличный', 'прекрасный']:
                            positive_count += 1
        
        # Если есть явные индикаторы рядом с аспектами, используем их
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        
        # Иначе используем базовую тональность по рейтингу
        return base_sentiment

    async def _extract_aspects_from_reviews(self, reviews: List[str]) -> List[str]:
        """Извлечение аспектов из отзывов на основе ключевых слов"""
        all_aspects = []
        
        for review in reviews:
            review_lower = review.lower()
            
            # Ищем аспекты по ключевым словам
            for aspect, keywords in self.aspect_keywords.items():
                if any(keyword in review_lower for keyword in keywords):
                    all_aspects.append(aspect)
            
            # Добавляем стандартные аспекты только если они найдены в тексте
            for standard_aspect in self.standard_aspects:
                if any(keyword in review_lower for keyword in self.aspect_keywords.get(standard_aspect, [])):
                    all_aspects.append(standard_aspect)
        
        # Убираем дубли и возвращаем уникальные аспекты
        unique_aspects = list(set(all_aspects))
        return unique_aspects[:30]  # Ограничиваем до 30 аспектов

    async def _remove_duplicates(self, aspects: List[str]) -> List[str]:
        """Удаление дублирующихся и похожих аспектов"""
        if not aspects:
            return []
        
        # Группируем похожие аспекты
        aspect_groups = []
        used_aspects = set()
        
        for aspect in aspects:
            if aspect in used_aspects:
                continue
                
            group = [aspect]
            used_aspects.add(aspect)
            
            # Ищем похожие аспекты
            for other_aspect in aspects:
                if other_aspect not in used_aspects and self._are_aspects_similar(aspect, other_aspect):
                    group.append(other_aspect)
                    used_aspects.add(other_aspect)
            
            if group:
                aspect_groups.append(group)
        
        # Выбираем лучший аспект из каждой группы
        result = []
        for group in aspect_groups:
            best_aspect = self._select_best_aspect(group)
            result.append(best_aspect)
        
        return result[:30]  # Ограничиваем до 30 аспектов

    async def _remove_synonyms(self, aspects: List[str]) -> List[str]:
        """Удаление синонимов на основе журнала синонимов"""
        if not aspects:
            return []
        
        # Создаем словарь замен
        synonym_map = {}
        for synonym_entry in self.synonym_journal:
            parts = synonym_entry.split("=")
            if len(parts) >= 2:
                main_aspect = parts[0].strip()
                for synonym in parts[1:]:
                    synonym_map[synonym.strip()] = main_aspect
        
        # Заменяем синонимы
        result = []
        for aspect in aspects:
            if aspect in synonym_map:
                main_aspect = synonym_map[aspect]
                if main_aspect not in result:
                    result.append(main_aspect)
            else:
                result.append(aspect)
        
        return result[:30]  # Ограничиваем до 30 аспектов

    def _are_aspects_similar(self, aspect1: str, aspect2: str) -> bool:
        """Проверка схожести аспектов"""
        # Простая проверка на основе общих слов
        words1 = set(aspect1.lower().split())
        words2 = set(aspect2.lower().split())
        
        # Если есть общие слова, считаем аспекты похожими
        common_words = words1.intersection(words2)
        return len(common_words) > 0

    def _select_best_aspect(self, aspects: List[str]) -> str:
        """Выбор лучшего аспекта из группы похожих"""
        if not aspects:
            return ""
        
        # Приоритет стандартным аспектам
        for aspect in aspects:
            if aspect in self.standard_aspects:
                return aspect
        
        # Возвращаем первый аспект
        return aspects[0]

    async def generate_custom_dictionary(self, aspects: List[str], synonym_journal: List[str] = None) -> List[str]:
        """Генерация кастомного словаря аспектов"""
        if synonym_journal:
            self.synonym_journal = synonym_journal
        
        return await self._remove_synonyms(aspects)

# Создаем глобальный экземпляр анализатора
aspect_analyzer = AspectAnalyzer()
