import re
import logging
from typing import List, Dict, Optional
import asyncio
import httpx
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

class AIAspectAnalyzer:
    """Анализатор аспектов товаров с использованием ИИ через OpenRouter API с поддержкой динамических аспектов"""
    
    def __init__(self):
        # Поддержка ротации API ключей OpenRouter из .env файла
        self.api_keys = [
            os.getenv('DEEPSEEK_TOKEN1'),
            os.getenv('DEEPSEEK_TOKEN2'),
            os.getenv('DEEPSEEK_TOKEN3'),
            os.getenv('DEEPSEEK_TOKEN4'),
            os.getenv('DEEPSEEK_TOKEN5')
        ]
        
        # Фильтруем None значения
        self.api_keys = [key for key in self.api_keys if key]
        
        if not self.api_keys:
            raise ValueError("Не найдены API ключи для OpenRouter")
        
        self.current_key_index = 0
        self.client = None
        
        # Система контроля лимитов
        self.request_timestamps = []  # Временные метки запросов для контроля минутных лимитов
        self.daily_request_counts = {i: 0 for i in range(len(self.api_keys))}  # Счетчики дневных запросов по ключам
        self.last_request_dates = {i: None for i in range(len(self.api_keys))}  # Даты последних запросов по ключам
        
        # Лимиты API
        self.MAX_REQUESTS_PER_MINUTE = 10  # Общий лимит запросов в минуту
        self.MAX_REQUESTS_PER_DAY = 250     # Общий лимит запросов в день
        self.MINUTE_WINDOW = 60             # Окно в секундах для минутного лимита
        self.DAY_WINDOW = 86400             # Окно в секундах для дневного лимита
        
        # Константы для контроля размера промптов
        self.MAX_REVIEWS_PER_PROMPT = 50  # Максимум отзывов в одном промпте (оптимизировано под лимиты API)
        self.MAX_TOKENS_PER_REVIEW = 100   # Максимум токенов на отзыв
        self.MAX_TOTAL_TOKENS = 6000       # Максимум токенов в промпте (увеличено под 50 отзывов)
        
        # Доступные модели
        self.available_models = {
            "deepseek": "deepseek/deepseek-r1-0528-qwen3-8b:free",
            "qwen": "qwen/qwen-3-8b-chat",
            "gemma": "google/gemma-7b-it"
        }
        
        # Упрощенные промпты для стабильной работы
        self.prompts = {
            "creative_batch_analysis": """Проанализируй до 30 отзывов и создай аспекты.

ПРАВИЛА:
- Используй базовые аспекты: Цена, Качество, Эффективность, Упаковка, Запах
- Создавай новые для уникальных случаев
- Каждый аспект: название, тональность (positive/negative), уверенность (0.1-1.0), категория
- ВАЖНО: Всегда завершай JSON полностью, не обрезай ответ

ФОРМАТ:
```json
[
  {
    "review_index": 0,
    "aspects": {
      "Эффективность": {
        "sentiment": "positive",
        "confidence": 0.9,
        "evidence": ["волосы растут"],
        "category": "Эффективность",
        "is_new_aspect": false
      }
    }
  }
]```

ОТЗЫВЫ:
{reviews_batch}""",

            "single_review_enhanced": """Проанализируй один отзыв и определи аспекты.

ОТЗЫВ: {review_text}
РЕЙТИНГ: {rating}

ПРАВИЛА:
- Определи основные аспекты товара
- Укажи тональность каждого аспекта (positive/negative)
- Используй базовые аспекты: Цена, Качество, Эффективность, Упаковка, Запах
- Создавай новые для уникальных случаев

ФОРМАТ:
```json
{
  "aspects": {
    "Эффективность": {
      "sentiment": "positive",
      "confidence": 0.9,
      "evidence": ["конкретные фразы из отзыва"],
      "category": "Эффективность"
    }
  }
}```"""
        }
        
        self._init_client()

    def _check_rate_limits(self) -> bool:
        """Проверяет лимиты API и возвращает True если можно делать запрос"""
        current_time = time.time()
        
        # Очищаем старые временные метки (старше 1 минуты)
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                 if current_time - ts < self.MINUTE_WINDOW]
        
        # Проверяем минутный лимит
        if len(self.request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            logger.warning(f"Превышен минутный лимит: {len(self.request_timestamps)} запросов за минуту")
            return False
        
        # Проверяем дневной лимит для текущего ключа
        if self.daily_request_counts[self.current_key_index] >= self.MAX_REQUESTS_PER_DAY:
            logger.warning(f"Превышен дневной лимит для ключа {self.current_key_index + 1}")
            return False
        
        return True
    
    def _wait_for_rate_limit(self) -> float:
        """Вычисляет время ожидания для соблюдения лимитов"""
        current_time = time.time()
        
        # Ждем освобождения минутного слота
        if len(self.request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            oldest_request = min(self.request_timestamps)
            wait_time = self.MINUTE_WINDOW - (current_time - oldest_request)
            if wait_time > 0:
                return wait_time
        
        # Ждем освобождения дневного слота
        for i, daily_count in enumerate(self.daily_request_counts.items()):
            if daily_count[1] >= self.MAX_REQUESTS_PER_DAY:
                # Ждем до следующего дня
                if self.last_request_dates[i]:
                    next_day = self.last_request_dates[i] + timedelta(days=1)
                    wait_time = (next_day - datetime.now()).total_seconds()
                    if wait_time > 0:
                        return wait_time
        
        return 0.0

    def _update_request_counters(self):
        """Обновляет счетчики запросов"""
        current_time = time.time()
        self.request_timestamps.append(current_time)
        self.daily_request_counts[self.current_key_index] += 1
        self.last_request_dates[self.current_key_index] = datetime.now()

    def _reset_daily_counters_if_needed(self):
        """Сбрасывает дневные счетчики если нужно"""
        current_date = datetime.now().date()
        
        for key_index, last_date in self.last_request_dates.items():
            if last_date and last_date.date() < current_date:
                self.daily_request_counts[key_index] = 0
                self.last_request_dates[key_index] = None

    def get_rate_limit_status(self) -> Dict:
        """Возвращает текущий статус лимитов API"""
        current_time = time.time()
        requests_last_minute = len([ts for ts in self.request_timestamps 
                                  if current_time - ts < self.MINUTE_WINDOW])
        
        return {
            "current_key": self.current_key_index + 1,
            "requests_last_minute": requests_last_minute,
            "max_requests_per_minute": self.MAX_REQUESTS_PER_MINUTE,
            "daily_counts": {f"key_{i+1}": count for i, count in enumerate(self.daily_request_counts)},
            "max_requests_per_day": self.MAX_REQUESTS_PER_DAY
        }

    async def analyze_reviews(self, reviews: List[str], product_name: str = "") -> Dict[str, List[str]]:
        """Анализ отзывов и формирование словарей аспектов с помощью ИИ"""
        try:
            # Разбиваем отзывы на оптимальные батчи
            review_batches = self._split_reviews_into_batches(reviews)
            
            all_aspects = []
            for batch in review_batches:
                # Формируем адаптивный словарь для батча
                reviews_text = "\n".join(batch)
                batch_aspects = await self._generate_adaptive_dictionary(reviews_text, product_name, len(batch))
                all_aspects.extend(batch_aspects)
            
            # Убираем дубли из всех аспектов
            no_duplicates_dict = await self._remove_duplicates_ai(all_aspects, product_name)
            
            # Убираем синонимы
            no_synonyms_dict = await self._remove_synonyms_ai(no_duplicates_dict, product_name)
            
            return {
                "general_dictionary": all_aspects,
                "no_duplicates_dictionary": no_duplicates_dict,
                "no_synonyms_dictionary": no_synonyms_dict
            }
        except Exception as e:
            logger.error(f"Ошибка при анализе отзывов с ИИ: {e}")
            raise

    async def analyze_reviews_safely_with_scheduler(self, reviews: List[str], product_name: str = "", 
                                                  max_batches_per_hour: int = 20) -> List[Dict]:
        """Безопасный анализ отзывов с планировщиком и контролем лимитов"""
        try:
            if not reviews:
                return []
            
            # Разбиваем на батчи
            total_batches = (len(reviews) + self.MAX_REVIEWS_PER_PROMPT - 1) // self.MAX_REVIEWS_PER_PROMPT
            
            all_results = []
            batch_count = 0
            start_time = time.time()
            
            for i in range(0, len(reviews), self.MAX_REVIEWS_PER_PROMPT):
                batch = reviews[i:i + self.MAX_REVIEWS_PER_PROMPT]
                batch_index = i // self.MAX_REVIEWS_PER_PROMPT + 1
                
                # Проверяем лимиты
                if batch_count >= max_batches_per_hour:
                    wait_time = 3600  # Ждем час
                    await asyncio.sleep(wait_time)
                    batch_count = 0
                
                # Анализируем батч
                batch_start = time.time()
                batch_results = await self._analyze_batch_with_dynamic_aspects(batch, product_name, len(batch))
                batch_time = time.time() - batch_start
                
                all_results.extend(batch_results)
                batch_count += 1
                
                # Небольшая пауза между батчами
                if batch_index < total_batches:
                    await asyncio.sleep(1)
            
            total_time = time.time() - start_time
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при безопасном анализе: {e}")
            raise

    async def analyze_single_review(self, review_text: str, rating: int) -> Dict[str, List[str]]:
        """Анализ одного отзыва для определения аспектов с тональностью с помощью ИИ"""
        try:
            prompt = self.prompts["single_review_enhanced"].format(
                review_text=review_text,
                rating=rating
            )
            
            response = await self._call_ai_model(prompt, "deepseek")
            
            # Парсим JSON ответ
            try:
                import json
                import re
                
                # Убираем markdown блоки кода если они есть
                cleaned_response = response.strip()
                
                # Ищем JSON внутри markdown блоков кода
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Если нет markdown блоков, пробуем найти JSON напрямую
                    json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = cleaned_response
                
                # Пытаемся исправить неполный JSON
                if not json_str.endswith('}'):
                    # Ищем последнюю закрывающую скобку
                    last_brace = json_str.rfind('}')
                    if last_brace > 0:
                        json_str = json_str[:last_brace + 1]
                    else:
                        # Если нет закрывающей скобки, добавляем базовую структуру
                        json_str = json_str.rstrip(', \n\r\t') + '}'
                
                # Парсим JSON
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Если не удалось, пробуем исправить более агрессивно
                    logger.warning(f"Пытаемся исправить неполный JSON: {json_str[:100]}...")
                    
                    # Ищем поле "aspects" и создаем базовую структуру
                    if '"aspects"' in json_str:
                        # Создаем минимальный валидный JSON
                        fixed_json = '{"aspects": {}}'
                        result = json.loads(fixed_json)
                    else:
                        # Создаем пустой результат
                        result = {"aspects": {}}
                
                aspects = result.get("aspects", {})
                
                # Преобразуем в старый формат для совместимости
                positive_aspects = []
                negative_aspects = []
                
                for aspect_name, aspect_data in aspects.items():
                    sentiment = aspect_data.get("sentiment", "neutral")
                    if sentiment == "positive":
                        positive_aspects.append(aspect_name)
                    elif sentiment == "negative":
                        negative_aspects.append(aspect_name)
                
                return {
                    "positive": positive_aspects[:3],
                    "negative": negative_aspects[:3]
                }
            except json.JSONDecodeError as e:
                logger.error(f"Не удалось распарсить JSON ответ: {response[:200]}...")
                logger.error(f"Ошибка JSON: {e}")
                return {"positive": [], "negative": []}
                
        except Exception as e:
            logger.error(f"Ошибка при анализе одного отзыва с ИИ: {e}")
            return {"positive": [], "negative": []}

    async def generate_custom_dictionary(self, aspects: List[str], synonym_journal: List[str] = None) -> List[str]:
        """Генерация кастомного словаря аспектов с помощью ИИ"""
        try:
            if not synonym_journal:
                return aspects
            
            return await self._remove_synonyms_ai(aspects, "", synonym_journal)
        except Exception as e:
            logger.error(f"Ошибка при генерации кастомного словаря с ИИ: {e}")
            return aspects

    async def _generate_adaptive_dictionary(self, reviews_text: str, product_name: str, batch_size: int) -> List[str]:
        """Генерация адаптивного словаря аспектов"""
        prompt = self.prompts["creative_batch_analysis"].format(
            product_name=product_name or "товар",
            reviews=reviews_text,
            batch_size=batch_size
        )
        
        response = await self._call_ai_model(prompt, "deepseek")
        return self._parse_aspects_response(response)

    async def _analyze_batch_with_dynamic_aspects(self, reviews: List[str], product_name: str, batch_size: int) -> List[Dict]:
        """Анализ батча с созданием динамических аспектов"""
        prompt = self.prompts["creative_batch_analysis"].format(
            product_name=product_name or "товар",
            reviews_batch="\n".join(reviews),
            batch_size=batch_size
        )
        
        response = await self._call_ai_model(prompt, "deepseek")
        return self._parse_dynamic_aspects_response(response)

    async def _remove_duplicates_ai(self, aspects: List[str], product_name: str) -> List[str]:
        """Удаление дублирующихся аспектов с помощью ИИ"""
        if not aspects:
            return []
        
        aspects_text = "\n".join(aspects)
        prompt = f"""Убери дубликаты из списка аспектов для товара "{product_name}".
        
        Аспекты: {aspects_text}
        
        Верни только уникальные аспекты, разделенные переносами строк."""
        
        response = await self._call_ai_model(prompt, "deepseek")
        return self._parse_aspects_response(response)

    async def _remove_synonyms_ai(self, aspects: List[str], product_name: str, synonym_journal: List[str] = None) -> List[str]:
        """Удаление синонимов с помощью ИИ"""
        if not aspects:
            return []
        
        if not synonym_journal:
            return aspects
        
        aspects_text = "\n".join(aspects)
        journal_text = "\n".join(synonym_journal)
        
        prompt = f"""Убери синонимы из списка аспектов для товара "{product_name}".
        
        Журнал синонимов: {journal_text}
        Аспекты: {aspects_text}
        
        Верни только уникальные аспекты без синонимов."""
        
        response = await self._call_ai_model(prompt, "deepseek")
        return self._parse_aspects_response(response)

    async def _call_ai_model(self, prompt: str, model_name: str = "deepseek") -> str:
        """Вызов ИИ модели через OpenRouter API с умным контролем лимитов и ротацией ключей"""
        max_retries = len(self.api_keys)
        
        for attempt in range(max_retries):
            try:
                # Сбрасываем дневные счетчики если нужно
                self._reset_daily_counters_if_needed()
                
                # Проверяем лимиты перед запросом
                if not self._check_rate_limits():
                    wait_time = self._wait_for_rate_limit()
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        continue
                
                # Проверяем лимиты еще раз после ожидания
                if not self._check_rate_limits():
                    continue
                
                model = self.available_models.get(model_name, self.available_models["deepseek"])
                
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=6000,  # Увеличиваем для предотвращения обрезания JSON
                    temperature=0.7
                )
                
                # Обновляем счетчики после успешного запроса
                self._update_request_counters()
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Проверяем тип ошибки для ротации ключа
                if any(keyword in error_msg for keyword in ['rate limit', '429', 'quota', 'limit', 'token']):
                    self._init_client()  # Ротация ключа
                else:
                    # Для других ошибок тоже пробуем следующий ключ
                    self._init_client()
                
                if attempt == max_retries - 1:
                    raise Exception(f"Все API ключи исчерпаны. Последняя ошибка: {e}")
        
        raise Exception("Не удалось выполнить запрос после всех попыток")

    def _parse_aspects_response(self, response: str) -> List[str]:
        """Парсинг ответа ИИ в список аспектов"""
        try:
            import re
            
            # Убираем markdown блоки кода если они есть
            cleaned_response = response.strip()
            
            # Ищем содержимое внутри markdown блоков кода
            code_match = re.search(r'```(?:.*?)?\s*([\s\S]*?)\s*```', cleaned_response, re.DOTALL)
            if code_match:
                cleaned_response = code_match.group(1)
            
            # Разбиваем по строкам и очищаем
            aspects = []
            for line in cleaned_response.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('-'):
                    # Убираем нумерацию и лишние символы
                    line = re.sub(r'^\d+\.?\s*', '', line)
                    line = re.sub(r'^[-•*]\s*', '', line)
                    if line:
                        aspects.append(line)
            
            return aspects[:30]  # Ограничиваем до 30 аспектов
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа ИИ: {e}")
            return []

    def _parse_dynamic_aspects_response(self, response: str) -> List[Dict]:
        """Парсинг ответа ИИ с динамическими аспектами"""
        try:
            import json
            import re
            
            # Убираем markdown блоки кода если они есть
            cleaned_response = response.strip()
            
            # Ищем JSON внутри markdown блоков кода
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Если нет markdown блоков, пробуем найти JSON напрямую
                json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Пробуем найти начало JSON массива
                    start_match = re.search(r'\[', cleaned_response)
                    if start_match:
                        # Берем все что есть после открывающей скобки
                        json_str = cleaned_response[start_match.start():]
                        # Пытаемся найти закрывающую скобку
                        bracket_count = 0
                        for i, char in enumerate(json_str):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    json_str = json_str[:i+1]
                                    break
                    else:
                        json_str = cleaned_response
            
            # Парсим JSON
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                # Если не удалось распарсить, пробуем исправить обрезанный JSON
                logger.warning("JSON обрезан, пытаемся исправить...")
                fixed_json = self._fix_truncated_json(json_str)
                if fixed_json:
                    return json.loads(fixed_json)
                else:
                    raise json.JSONDecodeError("Не удалось исправить обрезанный JSON", json_str, 0)
            
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON ответ с динамическими аспектами: {response[:500]}...")
            logger.error(f"Ошибка JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа с динамическими аспектами: {e}")
            return []

    def _fix_truncated_json(self, json_str: str) -> Optional[str]:
        """Пытается исправить обрезанный JSON"""
        try:
            # Убираем лишние символы в конце
            json_str = json_str.rstrip(', \n\r\t')
            
            # Если JSON обрывается на объекте, закрываем его
            if json_str.endswith('"'):
                json_str += '}'
            elif json_str.endswith('"}'):
                pass  # уже закрыт
            elif json_str.endswith('"}}'):
                pass  # уже закрыт
            elif json_str.endswith('"}},'):
                json_str = json_str.rstrip(',') + '}'
            elif json_str.endswith('"}}'):
                pass  # уже закрыт
            else:
                # Пытаемся найти последний полный объект
                last_complete = re.search(r'\{[^{}]*"}[^{}]*$', json_str)
                if last_complete:
                    json_str = json_str[:last_complete.end()]
            
            # Закрываем массив если нужно
            if not json_str.endswith(']'):
                json_str += ']'
            
            # Проверяем валидность
            json.loads(json_str)
            return json_str
            
        except:
            return None

    def _split_reviews_into_batches(self, reviews: List[str]) -> List[List[str]]:
        """Разбивает отзывы на батчи оптимального размера"""
        if not reviews:
            return []
        
        batches = []
        for i in range(0, len(reviews), self.MAX_REVIEWS_PER_PROMPT):
            batch = reviews[i:i + self.MAX_REVIEWS_PER_PROMPT]
            batches.append(batch)
        
        return batches

    def _init_client(self):
        """Инициализирует клиент OpenRouter с ротацией ключей"""
        # Переключаемся на следующий ключ
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        # Создаем новый клиент с текущим ключом
        api_key = self.api_keys[self.current_key_index]
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

# Создаем глобальный экземпляр ИИ-анализатора
try:
    ai_aspect_analyzer = AIAspectAnalyzer()
except Exception as e:
    logger.error(f"Ошибка инициализации ИИ-анализатора: {e}")
    ai_aspect_analyzer = None
