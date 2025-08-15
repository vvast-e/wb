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
        
        # Ограничения для стабильной работы
        self.MAX_REVIEWS_PER_PROMPT = 50  # Уменьшаем для стабильности
        self.MAX_TOKENS_PER_REVIEW = 100  # Уменьшаем для экономии
        self.MAX_TOTAL_TOKENS = 6000      # Оптимизируем для стабильности
        
        # Доступные модели
        self.available_models = {
            "deepseek": "deepseek/deepseek-r1-0528-qwen3-8b:free",
            "qwen": "qwen/qwen-3-8b-chat",
            "gemma": "google/gemma-7b-it"
        }
        
        # Упрощенные промпты для стабильной работы
        self.prompts = {
            "creative_batch_analysis": """Проанализируй {batch_size} отзывов и создай аспекты.

ПРАВИЛА:
- Используй базовые аспекты: Цена, Качество, Эффективность, Упаковка, Запах
- Создавай новые для уникальных случаев
- Каждый аспект: название, тональность (positive/negative), уверенность (0.1-1.0), категория

ФОРМАТ:
```json
[
  {{
    "review_index": 0,
    "aspects": {{
      "Эффективность": {{
        "sentiment": "positive",
        "confidence": 0.9,
        "evidence": ["волосы растут"],
        "category": "Эффективность",
        "is_new_aspect": false
      }}
    }}
  }}
]```

ОТЗЫВЫ:
{reviews_batch}"""
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
        """Ждет до следующего доступного слота для запроса, возвращает время ожидания"""
        current_time = time.time()
        
        # Если превышен минутный лимит, ждем до освобождения слота
        if len(self.request_timestamps) >= self.MAX_REQUESTS_PER_MINUTE:
            oldest_timestamp = min(self.request_timestamps)
            wait_time = self.MINUTE_WINDOW - (current_time - oldest_timestamp) + 1
            logger.info(f"Ждем {wait_time:.1f} секунд до освобождения минутного слота")
            return wait_time
        
        # Если превышен дневной лимит для текущего ключа, ищем следующий доступный
        if self.daily_request_counts[self.current_key_index] >= self.MAX_REQUESTS_PER_DAY:
            # Ищем ключ с доступными запросами
            for i in range(len(self.api_keys)):
                if self.daily_request_counts[i] < self.MAX_REQUESTS_PER_DAY:
                    logger.info(f"Переключаемся на ключ {i + 1} (запросов: {self.daily_request_counts[i]})")
                    self.current_key_index = i
                    self._init_client()
                    return 0
            
            # Если все ключи исчерпаны, ждем до следующего дня
            wait_time = self.DAY_WINDOW - (current_time % self.DAY_WINDOW)
            logger.warning(f"Все ключи исчерпаны, ждем {wait_time/3600:.1f} часов до следующего дня")
            return wait_time
        
        return 0
    
    def _update_request_counters(self):
        """Обновляет счетчики запросов"""
        current_time = time.time()
        
        # Добавляем текущую временную метку
        self.request_timestamps.append(current_time)
        
        # Увеличиваем счетчик дневных запросов для текущего ключа
        self.daily_request_counts[self.current_key_index] += 1
        
        # Обновляем дату последнего запроса
        self.last_request_dates[self.current_key_index] = current_time
        
        logger.debug(f"Ключ {self.current_key_index + 1}: запросов сегодня {self.daily_request_counts[self.current_key_index]}")
    
    def _reset_daily_counters_if_needed(self):
        """Сбрасывает дневные счетчики если прошел день"""
        current_time = time.time()
        
        for key_index in range(len(self.api_keys)):
            last_date = self.last_request_dates[key_index]
            if last_date and (current_time - last_date) >= self.DAY_WINDOW:
                self.daily_request_counts[key_index] = 0
                logger.info(f"Сброшен дневной счетчик для ключа {key_index + 1}")
    
    def get_rate_limit_status(self) -> Dict:
        """Возвращает текущий статус лимитов API"""
        current_time = time.time()
        
        # Очищаем старые временные метки
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                 if current_time - ts < self.MINUTE_WINDOW]
        
        return {
            "current_key": self.current_key_index + 1,
            "requests_last_minute": len(self.request_timestamps),
            "max_requests_per_minute": self.MAX_REQUESTS_PER_MINUTE,
            "daily_counts": {f"key_{i+1}": count for i, count in self.daily_request_counts.items()},
            "max_requests_per_day": self.MAX_REQUESTS_PER_DAY,
            "can_make_request": self._check_rate_limits()
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

    async def analyze_reviews_with_dynamic_aspects(self, reviews: List[str], product_name: str = "") -> List[Dict]:
        """Анализ отзывов с созданием динамических аспектов"""
        try:
            # Разбиваем отзывы на оптимальные батчи
            review_batches = self._split_reviews_into_batches(reviews)
            
            all_results = []
            for batch in review_batches:
                # Анализируем батч с созданием новых аспектов
                batch_results = await self._analyze_batch_with_dynamic_aspects(batch, product_name, len(batch))
                all_results.extend(batch_results)
            
            return all_results
        except Exception as e:
            logger.error(f"Ошибка при анализе отзывов с динамическими аспектами: {e}")
            raise

    async def analyze_reviews_safely_with_scheduler(self, reviews: List[str], product_name: str = "", 
                                                  max_batches_per_hour: int = 20) -> List[Dict]:
        """Безопасный анализ больших объемов отзывов с планировщиком и контролем лимитов"""
        try:
            logger.info(f"🚀 Запуск безопасного анализа {len(reviews)} отзывов")
            
            # Разбиваем отзывы на оптимальные батчи
            review_batches = self._split_reviews_into_batches(reviews)
            total_batches = len(review_batches)
            
            logger.info(f"📊 Разбито на {total_batches} батчей по {self.MAX_REVIEWS_PER_PROMPT} отзывов")
            
            all_results = []
            processed_batches = 0
            start_time = time.time()
            
            for batch_index, batch in enumerate(review_batches, 1):
                try:
                    # Показываем статус лимитов
                    status = self.get_rate_limit_status()
                    current_key = status['current_key']
                    daily_count = status['daily_counts'][f'key_{current_key}']
                    logger.info(f"📈 Статус лимитов: ключ {current_key}, "
                              f"запросов за минуту: {status['requests_last_minute']}/{status['max_requests_per_minute']}, "
                              f"запросов за день: {daily_count}/{status['max_requests_per_day']}")
                    
                    # Проверяем лимиты перед обработкой батча
                    if not self._check_rate_limits():
                        wait_time = self._wait_for_rate_limit()
                        if wait_time > 0:
                            logger.info(f"⏳ Ожидание {wait_time:.1f} секунд для соблюдения лимитов...")
                            await asyncio.sleep(wait_time)
                    
                    # Анализируем батч
                    logger.info(f"🔄 Обработка батча {batch_index}/{total_batches} ({len(batch)} отзывов)")
                    batch_start_time = time.time()
                    
                    batch_results = await self._analyze_batch_with_dynamic_aspects(batch, product_name, len(batch))
                    all_results.extend(batch_results)
                    
                    batch_time = time.time() - batch_start_time
                    processed_batches += 1
                    
                    logger.info(f"✅ Батч {batch_index} обработан за {batch_time:.1f} секунд")
                    
                    # Планировщик: ограничиваем количество батчей в час
                    if processed_batches >= max_batches_per_hour:
                        elapsed_hours = (time.time() - start_time) / 3600
                        if elapsed_hours < 1.0:
                            wait_time = 3600 - (time.time() - start_time)
                            logger.info(f"⏰ Достигнут лимит {max_batches_per_hour} батчей в час, "
                                      f"ожидание {wait_time/60:.1f} минут...")
                            await asyncio.sleep(wait_time)
                            # Сбрасываем счетчики для нового часа
                            processed_batches = 0
                            start_time = time.time()
                    
                    # Небольшая пауза между батчами для стабильности
                    if batch_index < total_batches:
                        await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке батча {batch_index}: {e}")
                    # Продолжаем с следующим батчем
                    continue
            
            total_time = time.time() - start_time
            logger.info(f"🎉 Безопасный анализ завершен: {len(all_results)} результатов за {total_time/60:.1f} минут")
            
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
                
                # Парсим JSON
                result = json.loads(json_str)
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
                logger.error(f"Не удалось распарсить JSON ответ: {response}")
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
                        logger.info(f"⏳ Ожидание {wait_time:.1f} секунд для соблюдения лимитов...")
                        await asyncio.sleep(wait_time)
                        continue
                
                # Проверяем лимиты еще раз после ожидания
                if not self._check_rate_limits():
                    logger.error("Не удалось соблюсти лимиты API после ожидания")
                    continue
                
                model = self.available_models.get(model_name, self.available_models["deepseek"])
                
                logger.info(f"🚀 API запрос через ключ {self.current_key_index + 1} (попытка {attempt + 1})")
                
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000,  # Увеличиваем для анализа батчей
                    temperature=0.7
                )
                
                # Обновляем счетчики после успешного запроса
                self._update_request_counters()
                
                logger.info(f"✅ API запрос успешен через ключ {self.current_key_index + 1}")
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.warning(f"❌ Ошибка API ключа {self.current_key_index + 1}: {e}")
                
                # Проверяем тип ошибки для ротации ключа
                if any(keyword in error_msg for keyword in ['rate limit', '429', 'quota', 'limit', 'token']):
                    logger.info(f"🔄 Превышен лимит для ключа {self.current_key_index + 1}, переключаемся на следующий")
                    self._init_client()  # Ротация ключа
                else:
                    # Для других ошибок тоже пробуем следующий ключ
                    logger.info(f"🔄 Ошибка API, пробуем следующий ключ")
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
        """Разбивает отзывы на оптимальные батчи с учетом ограничений токенов"""
        if len(reviews) <= self.MAX_REVIEWS_PER_PROMPT:
            return [reviews]
        
        batches = []
        current_batch = []
        current_tokens = 0
        
        for review in reviews:
            # Примерная оценка токенов (1 слово ≈ 1.3 токена)
            review_tokens = len(review.split()) * 1.3
            
            if (current_tokens + review_tokens > self.MAX_TOTAL_TOKENS or 
                len(current_batch) >= self.MAX_REVIEWS_PER_PROMPT):
                if current_batch:
                    batches.append(current_batch)
                current_batch = [review]
                current_tokens = review_tokens
            else:
                current_batch.append(review)
                current_tokens += review_tokens
        
        if current_batch:
            batches.append(current_batch)
        
        logger.info(f"Разбито {len(reviews)} отзывов на {len(batches)} батчей")
        return batches

    def _init_client(self):
        """Инициализация клиента OpenAI с ротацией API ключей"""
        # Не увеличиваем индекс при инициализации, только при ротации
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.current_key_index = 0
        else:
            # Ротация на следующий ключ
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_keys[self.current_key_index]
        )
        logger.info(f"🔑 Используется API ключ: {self.current_key_index + 1} ({self.api_keys[self.current_key_index][:8]}...)")

# Создаем глобальный экземпляр ИИ-анализатора
try:
    ai_aspect_analyzer = AIAspectAnalyzer()
    logger.info("ИИ-анализатор с динамическими аспектами успешно инициализирован")
except Exception as e:
    logger.warning(f"Не удалось инициализировать ИИ-анализатор: {e}")
    ai_aspect_analyzer = None
