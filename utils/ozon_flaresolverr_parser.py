#!/usr/bin/env python3
"""
🚀 OZON FLARESOLVERR ПАРСЕР - СТАБИЛЬНЫЙ ОБХОД АНТИБОТА 🚀

Специально разработан для стабильного парсинга Ozon через FlareSolverr.
Включает:
- Интеграцию с FlareSolverr для обхода 403 антибота
- Парсинг цен и отзывов из HTML
- Поддержку резидентных мобильных прокси
- Стабильную работу с обработкой ошибок
- Кэширование результатов
"""

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin, urlparse
import uuid

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("❌ requests не установлен! Установите: pip install requests")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    print("❌ BeautifulSoup не установлен! Установите: pip install beautifulsoup4")

class OzonFlareSolverrParser:
    """Стабильный парсер Ozon через FlareSolverr"""
    
    def __init__(self, proxy_config: Optional[Dict] = None, flaresolverr_url: str = "http://localhost:8191/v1"):
        """
        proxy_config = {
            'scheme': 'http',
            'host': 'your.proxy.host',
            'port': 8080,
            'username': 'user',
            'password': 'pass'
        }
        """
        self.proxy_config = proxy_config
        self.flaresolverr_url = flaresolverr_url
        self.session = None
        self.cookies = {}
        self.device_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        # Кэш для HTML страниц
        self.html_cache = {}
        self.cache_timeout = 300  # 5 минут
        
        # Мобильные заголовки для FlareSolverr
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Cache-Control': 'max-age=0',
        }
        
    def _build_proxy_url(self) -> Optional[str]:
        """Собирает URL прокси из конфига"""
        if not self.proxy_config:
            return None
        
        config = self.proxy_config
        auth = ""
        if config.get('username') and config.get('password'):
            auth = f"{config['username']}:{config['password']}@"
        
        return f"{config.get('scheme', 'http')}://{auth}{config['host']}:{config['port']}"
    
    async def __aenter__(self):
        """Инициализация парсера"""
        if not HAS_REQUESTS:
            raise ImportError("requests обязателен для работы парсера!")
        
        if not HAS_BS4:
            raise ImportError("BeautifulSoup обязателен для работы парсера!")
        
        self.session = requests.Session()
        print("🚀 Инициализация FlareSolverr парсера...")
        await self._test_flaresolverr()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие парсера"""
        if self.session:
            self.session.close()
        self.session = None
    
    async def _test_flaresolverr(self):
        """Тестирование подключения к FlareSolverr"""
        try:
            test_payload = {
                "cmd": "request.get",
                "url": "https://httpbin.org/ip",
                "maxTimeout": 30000
            }
            
            response = await asyncio.to_thread(
                self.session.post, 
                self.flaresolverr_url, 
                json=test_payload, 
                timeout=35
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    print("✅ FlareSolverr подключен успешно")
                    return True
                else:
                    print(f"⚠️ FlareSolverr предупреждение: {result.get('message', 'Unknown')}")
                    return True
            else:
                print(f"⚠️ FlareSolverr статус: {response.status_code}")
                return True
                
        except requests.exceptions.ConnectionError:
            print("❌ FlareSolverr не запущен!")
            print("💡 Запустите: docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest")
            raise ConnectionError("FlareSolverr недоступен")
        except Exception as e:
            print(f"⚠️ Ошибка тестирования FlareSolverr: {e}")
            return True
    
    async def _get_page_via_flaresolverr(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Получение HTML страницы через FlareSolverr"""
        
        # Проверяем кэш
        if use_cache and url in self.html_cache:
            cached_data = self.html_cache[url]
            if time.time() - cached_data['timestamp'] < self.cache_timeout:
                print("📋 Используем кэшированную страницу")
                return cached_data['html']
        
        print(f"🌐 Получение страницы через FlareSolverr: {url}")
        
        try:
            # Подготавливаем payload для FlareSolverr
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000,
                "userAgent": self.mobile_headers['User-Agent']
            }
            
            # Добавляем прокси если настроен
            proxy_url = self._build_proxy_url()
            if proxy_url:
                payload["proxy"] = {"url": proxy_url}
                print(f"🌐 Используем прокси: {self.proxy_config['host']}:{self.proxy_config['port']}")
            
            # Отправляем запрос
            response = await asyncio.to_thread(
                self.session.post,
                self.flaresolverr_url,
                json=payload,
                timeout=70
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'ok':
                    solution = result.get('solution', {})
                    status_code = solution.get('status', 0)
                    html = solution.get('response', '')
                    
                    print(f"✅ FlareSolverr статус: {status_code}")
                    print(f"📏 Размер HTML: {len(html)} символов")
                    
                    if status_code == 200 and html:
                        # Проверяем что это действительно Ozon страница
                        if "ozon" in html.lower() and ("product" in html.lower() or "товар" in html.lower()):
                            print("✅ Ozon страница получена успешно!")
                            
                            # Сохраняем HTML для отладки
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            debug_file = f"ozon_debug_{timestamp}.html"
                            try:
                                with open(debug_file, "w", encoding="utf-8") as f:
                                    f.write(html)
                                print(f"💾 HTML сохранен для отладки: {debug_file}")
                            except Exception as e:
                                print(f"⚠️ Не удалось сохранить HTML: {e}")
                            
                            # Кэшируем результат
                            if use_cache:
                                self.html_cache[url] = {
                                    'html': html,
                                    'timestamp': time.time()
                                }
                            
                            return html
                        else:
                            print("⚠️ HTML получен, но не похож на Ozon страницу")
                            return None
                    else:
                        print(f"❌ HTTP ошибка: {status_code}")
                        return None
                else:
                    print(f"❌ FlareSolverr ошибка: {result.get('message', 'Unknown error')}")
                    return None
            else:
                print(f"❌ FlareSolverr сервер ошибка: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка получения страницы: {e}")
            return None
    
    def _extract_product_id(self, product_url: str) -> Optional[str]:
        """Извлекает ID товара из URL"""
        if '/product/' in product_url:
            parts = product_url.split('/product/')
            if len(parts) > 1:
                product_part = parts[1].rstrip('/')
                # Ищем числовой ID в конце URL
                match = re.search(r'(\d+)/?$', product_part)
                if match:
                    return match.group(1)
        return None
    
    def _extract_price_from_html(self, html: str) -> Optional[Dict]:
        """Извлекает цену из HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем цену в различных селекторах Ozon
            price_selectors = [
                # Основные селекторы цен
                'span[data-testid="price"]',
                '.price',
                '.product-price',
                '[class*="price"]',
                '[class*="kz1"]',  # Ozon специфичные классы
                '[class*="kz2"]',
                '[class*="kz6"]',
                '[class*="kz7"]',
                # Дополнительные селекторы
                'span[class*="tsBodyNumeric"]',
                'span[class*="tsHeadlineNumeric"]',
                '[data-widget="webPrice"]',
                '[data-widget="price"]',
                # Новые селекторы для Ozon
                'span[class*="kz8"]',
                'span[class*="kz9"]',
                'span[class*="kz10"]',
                'span[class*="kz11"]',
                'span[class*="kz12"]',
                'span[class*="kz13"]',
                'span[class*="kz14"]',
                'span[class*="kz15"]',
                'span[class*="kz16"]',
                'span[class*="kz17"]',
                'span[class*="kz18"]',
                'span[class*="kz19"]',
                'span[class*="kz20"]',
                # Селекторы с числами
                'span[class*="numeric"]',
                'span[class*="amount"]',
                'span[class*="cost"]',
                'span[class*="value"]',
                # Селекторы с рублями
                'span:contains("₽")',
                'span:contains("руб")',
                'span:contains("рублей")',
                # Общие селекторы
                'span[class*="ts"]',
                'div[class*="price"]',
                'div[class*="cost"]',
                'div[class*="amount"]'
            ]
            
            current_price = None
            original_price = None
            
            # Ищем текущую цену
            for selector in price_selectors:
                try:
                    elements = soup.select(selector)
                    for elem in elements:
                        text = elem.get_text().strip()
                        if text and re.search(r'\d', text):
                            # Очищаем цену от лишних символов
                            price_clean = re.sub(r'[^\d]', '', text)
                            if price_clean and len(price_clean) >= 3:  # Минимум 3 цифры
                                try:
                                    price_num = int(price_clean)
                                    # Берем самую маленькую цену как текущую
                                    if not current_price or price_num < current_price:
                                        current_price = price_num
                                        print(f"🔍 Найдена цена через селектор '{selector}': {price_num}")
                                except ValueError:
                                    continue
                except Exception as e:
                    continue
            
            # Дополнительный поиск через регулярные выражения
            if not current_price:
                print("🔍 Поиск цены через регулярные выражения...")
                # Ищем цены в тексте HTML
                price_patterns = [
                    r'(\d{3,})\s*₽',  # 1234 ₽
                    r'(\d{3,})\s*руб',  # 1234 руб
                    r'(\d{3,})\s*рублей',  # 1234 рублей
                    r'₽\s*(\d{3,})',  # ₽ 1234
                    r'руб\s*(\d{3,})',  # руб 1234
                    r'"price":\s*(\d{3,})',  # "price": 1234
                    r'"amount":\s*(\d{3,})',  # "amount": 1234
                    r'"value":\s*(\d{3,})',  # "value": 1234
                    r'"cost":\s*(\d{3,})',  # "cost": 1234
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for match in matches:
                        try:
                            price_num = int(match)
                            if 100 <= price_num <= 1000000:  # Разумный диапазон цен
                                if not current_price or price_num < current_price:
                                    current_price = price_num
                                    print(f"🔍 Найдена цена через regex '{pattern}': {price_num}")
                        except ValueError:
                            continue
            
            # Ищем старую цену (зачеркнутую)
            old_price_selectors = [
                'span[class*="old"]',
                'span[class*="cross"]',
                'del',
                's',
                '[class*="strikethrough"]',
                '[class*="original"]',
                '[class*="base"]'
            ]
            
            for selector in old_price_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text().strip()
                    if text and re.search(r'\d', text):
                        price_clean = re.sub(r'[^\d]', '', text)
                        if price_clean and len(price_clean) >= 3:
                            try:
                                price_num = int(price_clean)
                                # Берем самую большую цену как старую
                                if not original_price or price_num > original_price:
                                    original_price = price_num
                            except ValueError:
                                continue
            
            if current_price:
                result = {
                    'current_price': current_price,
                    'currency': 'RUB'
                }
                
                if original_price and original_price > current_price:
                    result['original_price'] = original_price
                    discount = ((original_price - current_price) / original_price) * 100
                    result['discount_percent'] = round(discount, 2)
                
                print(f"💰 Найдена цена: {current_price} RUB")
                if original_price:
                    print(f"💸 Старая цена: {original_price} RUB (скидка {result['discount_percent']}%)")
                
                return result
            
            print("⚠️ Цена не найдена в HTML")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка извлечения цены: {e}")
            return None
    
    def _extract_reviews_from_html(self, html: str) -> List[Dict]:
        """Извлекает отзывы из HTML"""
        reviews = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем JSON данные в script тегах
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and ('review' in script.string.lower() or 'отзыв' in script.string.lower()):
                    try:
                        script_text = script.string
                        
                        # Ищем паттерны с отзывами в JSON
                        review_patterns = [
                            r'"reviews"\s*:\s*(\[.*?\])',
                            r'"feedback"\s*:\s*(\[.*?\])',
                            r'"comments"\s*:\s*(\[.*?\])',
                            r'"items"\s*:\s*(\[.*?\])',
                            r'"data"\s*:\s*(\[.*?\])'
                        ]
                        
                        for pattern in review_patterns:
                            matches = re.findall(pattern, script_text, re.DOTALL)
                            for match in matches:
                                try:
                                    reviews_data = json.loads(match)
                                    if isinstance(reviews_data, list):
                                        for review_data in reviews_data:
                                            parsed_review = self._parse_single_review_from_data(review_data)
                                            if parsed_review:
                                                reviews.append(parsed_review)
                                except json.JSONDecodeError:
                                    continue
                    except Exception:
                        continue
            
            # Если не нашли в JSON, ищем в HTML структуре
            if not reviews:
                print("🔍 Поиск отзывов в HTML структуре...")
                review_selectors = [
                    '[class*="review"]',
                    '[class*="feedback"]',
                    '[class*="comment"]',
                    '[class*="отзыв"]',
                    '[class*="отзывы"]',
                    '[class*="reviews"]',
                    '[class*="rating"]',
                    '[class*="оценка"]',
                    '[class*="оценки"]',
                    '[data-testid*="review"]',
                    '[data-testid*="feedback"]',
                    '[data-testid*="comment"]',
                    '[data-widget*="review"]',
                    '[data-widget*="feedback"]',
                    '[data-widget*="comment"]',
                    'div[class*="item"]',
                    'div[class*="card"]',
                    'div[class*="block"]'
                ]
                
                for selector in review_selectors:
                    try:
                        review_elements = soup.select(selector)
                        for elem in review_elements[:10]:  # Ограничиваем количество
                            review = self._parse_review_from_element(elem)
                            if review and review['text'] and len(review['text']) > 20:
                                reviews.append(review)
                                print(f"🔍 Найден отзыв через селектор '{selector}': {review['author']}")
                    except Exception as e:
                        continue
            
            # Дополнительный поиск в widgetStates
            if not reviews:
                reviews.extend(self._extract_reviews_from_widget_states(html))
            
            # Дополнительный поиск через регулярные выражения
            if not reviews:
                print("🔍 Поиск отзывов через регулярные выражения...")
                review_patterns = [
                    r'"text":\s*"([^"]{20,})"',  # "text": "отзыв"
                    r'"comment":\s*"([^"]{20,})"',  # "comment": "отзыв"
                    r'"content":\s*"([^"]{20,})"',  # "content": "отзыв"
                    r'"review":\s*"([^"]{20,})"',  # "review": "отзыв"
                    r'"feedback":\s*"([^"]{20,})"',  # "feedback": "отзыв"
                    r'"message":\s*"([^"]{20,})"',  # "message": "отзыв"
                ]
                
                for pattern in review_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                    for i, match in enumerate(matches[:10]):  # Ограничиваем количество
                        if len(match) > 20:  # Минимальная длина отзыва
                            review = {
                                'id': f'regex_{i}',
                                'author': 'Аноним',
                                'text': match,
                                'rating': 0,
                                'date': '',
                                'pros': '',
                                'cons': '',
                                'useful_count': 0,
                                'is_anonymous': True,
                                'status': 'regex_found'
                            }
                            reviews.append(review)
                            print(f"🔍 Найден отзыв через regex '{pattern}': {match[:50]}...")
            
            print(f"📝 Найдено отзывов: {len(reviews)}")
            return reviews
            
        except Exception as e:
            print(f"❌ Ошибка извлечения отзывов: {e}")
            return []
    
    def _extract_reviews_from_widget_states(self, html: str) -> List[Dict]:
        """Извлекает отзывы из widgetStates в HTML"""
        reviews = []
        
        try:
            # Ищем widgetStates в HTML
            widget_states_match = re.search(r'window\.__NUXT__\s*=\s*({.*?});', html, re.DOTALL)
            if widget_states_match:
                nuxt_data = json.loads(widget_states_match.group(1))
                
                # Ищем отзывы в различных структурах
                if 'data' in nuxt_data:
                    data = nuxt_data['data']
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and 'reviews' in item:
                                reviews_data = item['reviews']
                                if isinstance(reviews_data, list):
                                    for review_data in reviews_data:
                                        parsed_review = self._parse_single_review_from_data(review_data)
                                        if parsed_review:
                                            reviews.append(parsed_review)
        
        except Exception as e:
            print(f"⚠️ Ошибка извлечения отзывов из widgetStates: {e}")
        
        return reviews
    
    def _parse_single_review_from_data(self, review_data: Dict) -> Optional[Dict]:
        """Парсинг одного отзыва из JSON данных"""
        try:
            # Извлекаем данные из различных структур
            author = 'Аноним'
            if isinstance(review_data.get('author'), dict):
                author = review_data['author'].get('firstName', 'Аноним')
            elif isinstance(review_data.get('author'), str):
                author = review_data['author']
            
            text = review_data.get('text', '') or review_data.get('comment', '') or review_data.get('content', '')
            if isinstance(text, dict):
                text = text.get('comment', '') or text.get('text', '')
            
            rating = review_data.get('rating', 0) or review_data.get('score', 0) or review_data.get('stars', 0)
            if isinstance(rating, dict):
                rating = rating.get('value', 0)
            
            date = review_data.get('date', '') or review_data.get('created_at', '') or review_data.get('publishedAt', '')
            
            pros = review_data.get('pros', '') or review_data.get('advantages', '')
            cons = review_data.get('cons', '') or review_data.get('disadvantages', '')
            
            useful_count = review_data.get('useful', 0) or review_data.get('likes', 0) or review_data.get('helpful', 0)
            if isinstance(useful_count, dict):
                useful_count = useful_count.get('count', 0)
            
            return {
                'id': review_data.get('id', '') or review_data.get('uuid', ''),
                'author': author,
                'text': str(text),
                'rating': int(rating) if rating else 0,
                'date': str(date),
                'pros': str(pros),
                'cons': str(cons),
                'useful_count': int(useful_count) if useful_count else 0,
                'is_anonymous': review_data.get('isAnonymous', False) or review_data.get('anonymous', False),
                'status': review_data.get('status', '') or review_data.get('state', '')
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга отзыва из данных: {e}")
            return None
    
    def _parse_review_from_element(self, element) -> Optional[Dict]:
        """Парсинг отзыва из HTML элемента"""
        try:
            # Ищем автора
            author_elem = element.select_one('[class*="author"], [class*="user"], [class*="name"], [class*="автор"]')
            author = author_elem.get_text().strip() if author_elem else 'Аноним'
            
            # Ищем текст
            text_elem = element.select_one('[class*="text"], [class*="content"], [class*="comment"], [class*="отзыв"]')
            text = text_elem.get_text().strip() if text_elem else ''
            
            # Ищем рейтинг
            rating_elem = element.select_one('[class*="rating"], [class*="star"], [class*="score"], [class*="рейтинг"]')
            rating = 0
            if rating_elem:
                rating_text = rating_elem.get_text().strip()
                rating_match = re.search(r'(\d+)', rating_text)
                if rating_match:
                    rating = int(rating_match.group(1))
            
            # Ищем дату
            date_elem = element.select_one('[class*="date"], [class*="time"], [class*="дата"]')
            date = date_elem.get_text().strip() if date_elem else ''
            
            if text and len(text) > 10:  # Только если есть достаточно текста
                return {
                    'id': '',
                    'author': author,
                    'text': text,
                    'rating': rating,
                    'date': date,
                    'pros': '',
                    'cons': '',
                    'useful_count': 0,
                    'is_anonymous': False,
                    'status': ''
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга отзыва из элемента: {e}")
            return None
    
    async def get_product_price(self, product_url: str) -> Optional[Dict]:
        """Получение цены товара"""
        print(f"💰 Парсинг цены: {product_url}")
        
        html = await self._get_page_via_flaresolverr(product_url)
        if not html:
            print("❌ HTML страница не получена")
            return None
        
        price_info = self._extract_price_from_html(html)
        if price_info:
            price_info['product_id'] = self._extract_product_id(product_url)
        
        return price_info
    
    async def get_product_reviews(self, product_url: str, max_pages: int = 3) -> List[Dict]:
        """Получение отзывов товара"""
        print(f"📝 Парсинг отзывов: {product_url}")
        
        all_reviews = []
        
        # Получаем основную страницу товара
        html = await self._get_page_via_flaresolverr(product_url)
        if not html:
            print("❌ HTML страница не получена")
            return []
        
        # Извлекаем отзывы с основной страницы
        reviews = self._extract_reviews_from_html(html)
        all_reviews.extend(reviews)
        
        # Пытаемся получить дополнительные страницы отзывов
        product_id = self._extract_product_id(product_url)
        if product_id and max_pages > 1:
            for page in range(2, max_pages + 1):
                try:
                    # URL для страницы отзывов
                    reviews_url = f"https://www.ozon.ru/product/{product_id}/reviews/?page={page}"
                    
                    print(f"📄 Получение страницы отзывов {page}")
                    page_html = await self._get_page_via_flaresolverr(reviews_url)
                    
                    if page_html:
                        page_reviews = self._extract_reviews_from_html(page_html)
                        if page_reviews:
                            all_reviews.extend(page_reviews)
                            print(f"✅ Найдено {len(page_reviews)} отзывов на странице {page}")
                        else:
                            print(f"✅ Отзывы закончились на странице {page}")
                            break
                    else:
                        print(f"❌ Не удалось получить страницу {page}")
                        break
                    
                    # Пауза между запросами
                    await asyncio.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    print(f"⚠️ Ошибка получения страницы {page}: {e}")
                    break
        
        # Удаляем дубликаты по ID
        unique_reviews = []
        seen_ids = set()
        for review in all_reviews:
            review_id = review.get('id', '')
            if review_id and review_id in seen_ids:
                continue
            if review_id:
                seen_ids.add(review_id)
            unique_reviews.append(review)
        
        print(f"🎉 Всего собрано уникальных отзывов: {len(unique_reviews)}")
        return unique_reviews
    
    async def get_product_full_info(self, product_url: str) -> Dict:
        """Получение полной информации о товаре"""
        print(f"🔍 Полный анализ товара: {product_url}")
        
        result = {
            'url': product_url,
            'product_id': self._extract_product_id(product_url),
            'price_info': None,
            'reviews': [],
            'reviews_count': 0,
            'average_rating': 0,
            'parsed_at': datetime.now().isoformat()
        }
        
        # Параллельно получаем цену и отзывы
        price_task = self.get_product_price(product_url)
        reviews_task = self.get_product_reviews(product_url)
        
        price_info, reviews = await asyncio.gather(price_task, reviews_task, return_exceptions=True)
        
        if not isinstance(price_info, Exception) and price_info:
            result['price_info'] = price_info
        
        if not isinstance(reviews, Exception) and reviews:
            result['reviews'] = reviews
            result['reviews_count'] = len(reviews)
            
            # Вычисляем средний рейтинг
            ratings = [r['rating'] for r in reviews if r.get('rating') and r['rating'] > 0]
            if ratings:
                result['average_rating'] = round(sum(ratings) / len(ratings), 2)
        
        return result
    
    async def parse_products_bulk(self, product_urls: List[str]) -> List[Dict]:
        """Массовый парсинг списка товаров"""
        print(f"🚀 Массовый парсинг {len(product_urls)} товаров")
        
        results = []
        
        for i, url in enumerate(product_urls, 1):
            print(f"\n📦 Товар {i}/{len(product_urls)}")
            
            try:
                result = await self.get_product_full_info(url)
                results.append(result)
                
                print(f"✅ Товар {i} обработан успешно")
                
                # Пауза между товарами для избежания блокировки
                if i < len(product_urls):
                    delay = random.uniform(5, 10)
                    print(f"⏳ Пауза {delay:.1f}с...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                print(f"❌ Ошибка обработки товара {i}: {e}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'parsed_at': datetime.now().isoformat()
                })
        
        print(f"\n🎉 Массовый парсинг завершен: {len(results)} результатов")
        return results


# Функции для быстрого использования
async def parse_ozon_flaresolverr_price(product_url: str, proxy_config: Optional[Dict] = None) -> Optional[Dict]:
    """Быстрая функция для парсинга цены через FlareSolverr"""
    async with OzonFlareSolverrParser(proxy_config) as parser:
        return await parser.get_product_price(product_url)

async def parse_ozon_flaresolverr_reviews(product_url: str, proxy_config: Optional[Dict] = None) -> List[Dict]:
    """Быстрая функция для парсинга отзывов через FlareSolverr"""
    async with OzonFlareSolverrParser(proxy_config) as parser:
        return await parser.get_product_reviews(product_url)

async def parse_ozon_flaresolverr_full(product_url: str, proxy_config: Optional[Dict] = None) -> Dict:
    """Быстрая функция для полного парсинга через FlareSolverr"""
    async with OzonFlareSolverrParser(proxy_config) as parser:
        return await parser.get_product_full_info(product_url)


# Пример использования
async def main():
    """Демонстрация работы FlareSolverr парсера"""
    
    # Конфигурация прокси
    proxy_config = {
        'scheme': 'http',
        'host': os.getenv('OZON_PROXY_HOST', 'p15184.ltespace.net'),
        'port': int(os.getenv('OZON_PROXY_PORT', '15184')),
        'username': os.getenv('OZON_PROXY_USERNAME', 'uek7t66y'),
        'password': os.getenv('OZON_PROXY_PASSWORD', 'zbygddap')
    }
    
    # Пример URL товара
    product_url = "https://www.ozon.ru/product/termozashchitnyy-sprey-dlya-volos-uvlazhnyayushchiy-nesmyvaemyy-uhod-dlya-legkogo-2128381166/?__rr=3&at=EqtkV5nBRhyWXGM9iY1OEWVhDKJLXvsrZVAMkFZK70J2"
    
    print("🚀 Демонстрация работы Ozon FlareSolverr Parser")
    
    async with OzonFlareSolverrParser(proxy_config) as parser:
        # Полный анализ товара
        result = await parser.get_product_full_info(product_url)
        
        print("\n📊 РЕЗУЛЬТАТ ПАРСИНГА:")
        print(f"Товар: {result['url']}")
        print(f"ID: {result['product_id']}")
        
        if result['price_info']:
            price = result['price_info']
            print(f"💰 Цена: {price['current_price']} {price['currency']}")
            if price.get('original_price'):
                print(f"💸 Старая цена: {price['original_price']} {price['currency']}")
                print(f"🎯 Скидка: {price['discount_percent']}%")
        
        print(f"📝 Отзывов: {result['reviews_count']}")
        if result['average_rating']:
            print(f"⭐ Средний рейтинг: {result['average_rating']}/5")
        
        # Показываем первые 3 отзыва
        for i, review in enumerate(result['reviews'][:3], 1):
            print(f"\n📄 Отзыв {i}:")
            print(f"   Автор: {review['author']}")
            print(f"   Рейтинг: {review['rating']}/5")
            print(f"   Текст: {review['text'][:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
