#!/usr/bin/env python3
"""
Ozon HTML Parser - парсинг через HTML страницы вместо API
Обходит 403 ошибки, парся данные прямо из HTML
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse
import uuid

try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from bs4 import BeautifulSoup

class OzonHTMLParser:
    """Парсер Ozon через HTML страницы"""
    
    def __init__(self, proxy_config: Optional[Dict] = None):
        self.proxy_config = proxy_config
        self.session = None
        self.cookies = {}
        self.device_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        # Мобильные заголовки
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
        if not HAS_CURL_CFFI:
            raise ImportError("curl_cffi обязателен для работы парсера!")
        
        proxy_url = self._build_proxy_url()
        proxies = None
        if proxy_url:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # Создаем сессию
        impersonate_id = os.getenv("OZON_CURL_IMPERSONATE", "chrome120")
        self.session = curl_requests.Session(
            impersonate=impersonate_id,
            headers=self.mobile_headers,
            proxies=proxies,
            timeout=30,
            verify=True
        )
        
        print("🚀 Инициализация HTML парсера...")
        await self._warmup_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие парсера"""
        self.session = None
    
    async def _warmup_session(self):
        """Прогрев сессии"""
        print("🔥 Прогрев сессии...")
        
        try:
            # Простой прогрев - только главная страница
            await self._safe_request('GET', 'https://www.ozon.ru/')
            await asyncio.sleep(random.uniform(2, 4))
            print("✅ Сессия прогрета успешно")
        except Exception as e:
            print(f"⚠️ Предупреждение при прогреве: {e}")
    
    async def _safe_request(self, method: str, url: str, **kwargs) -> Optional[object]:
        """Безопасный запрос с фолбэком на httpx"""
        try:
            if method.upper() == 'GET':
                response = await asyncio.to_thread(self.session.get, url, **kwargs)
            elif method.upper() == 'POST':
                response = await asyncio.to_thread(self.session.post, url, **kwargs)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")

            if hasattr(response, 'cookies'):
                self.cookies.update(response.cookies)
            return response
        except Exception as e:
            print(f"❌ curl_cffi ошибка {method} {url}: {e}")
            # Фолбэк на httpx
            if HAS_HTTPX:
                try:
                    proxy_url = self._build_proxy_url()
                    httpx_proxies = None
                    if proxy_url:
                        httpx_proxies = {"http://": proxy_url, "https://": proxy_url}
                    async with httpx.AsyncClient(timeout=30.0, proxies=httpx_proxies) as client:
                        resp = await client.request(
                            method=method.upper(),
                            url=url,
                            headers=kwargs.get('headers') or self.mobile_headers,
                            params=kwargs.get('params'),
                            json=kwargs.get('json'),
                            data=kwargs.get('data')
                        )
                        # Имитируем объект Response
                        class _Shim:
                            def __init__(self, r):
                                self.status_code = r.status_code
                                self.text = r.text
                                self.headers = r.headers
                                self._json = None
                                try:
                                    self._json = r.json()
                                except Exception:
                                    self._json = None
                                self.cookies = r.cookies
                            def json(self):
                                if self._json is not None:
                                    return self._json
                                raise ValueError("No JSON")
                        return _Shim(resp)
                except Exception as e2:
                    print(f"❌ httpx фолбэк тоже упал: {e2}")
                    return None
            return None
    
    def _extract_product_id(self, product_url: str) -> Optional[str]:
        """Извлекает ID товара из URL"""
        if '/product/' in product_url:
            parts = product_url.split('/product/')
            if len(parts) > 1:
                product_part = parts[1].rstrip('/')
                match = re.search(r'(\d+)/?$', product_part)
                if match:
                    return match.group(1)
        return None
    
    async def get_product_page(self, product_url: str) -> Optional[str]:
        """Получает HTML страницу товара"""
        print(f"📄 Получение страницы товара: {product_url}")
        
        # Очищаем URL от параметров для лучшей совместимости
        clean_url = product_url.split('?')[0]
        
        headers = self.mobile_headers.copy()
        headers['Referer'] = 'https://www.ozon.ru/'
        
        response = await self._safe_request('GET', clean_url, headers=headers)
        
        if not response:
            print("❌ Нет ответа от сервера")
            return None
        
        if response.status_code == 200:
            print(f"✅ Страница получена успешно ({len(response.text)} символов)")
            return response.text
        elif response.status_code == 403:
            print("❌ 403 Forbidden - антибот заблокировал запрос")
            return None
        else:
            print(f"❌ Ошибка {response.status_code}")
            return None
    
    def _extract_price_from_html(self, html: str) -> Optional[Dict]:
        """Извлекает цену из HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Ищем цену в различных селекторах
            price_selectors = [
                'span[data-testid="price"]',
                '.price',
                '.product-price',
                '[class*="price"]',
                'span[class*="kz1"]',  # Ozon специфичные классы
                'span[class*="kz2"]',
                'span[class*="kz6"]',
                'span[class*="kz7"]',
            ]
            
            current_price = None
            original_price = None
            
            for selector in price_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text().strip()
                    if text and re.search(r'\d', text):
                        # Очищаем цену
                        price_clean = re.sub(r'[^\d]', '', text)
                        if price_clean and len(price_clean) >= 3:  # Минимум 3 цифры
                            price_num = int(price_clean)
                            if not current_price or price_num < current_price:
                                current_price = price_num
            
            # Ищем старую цену (зачеркнутую)
            old_price_selectors = [
                'span[class*="old"]',
                'span[class*="cross"]',
                'del',
                's',
                '[class*="strikethrough"]'
            ]
            
            for selector in old_price_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text().strip()
                    if text and re.search(r'\d', text):
                        price_clean = re.sub(r'[^\d]', '', text)
                        if price_clean and len(price_clean) >= 3:
                            price_num = int(price_clean)
                            if not original_price or price_num > original_price:
                                original_price = price_num
            
            if current_price:
                result = {
                    'current_price': current_price,
                    'currency': 'RUB'
                }
                
                if original_price and original_price > current_price:
                    result['original_price'] = original_price
                    discount = ((original_price - current_price) / original_price) * 100
                    result['discount_percent'] = round(discount, 2)
                
                return result
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка извлечения цены: {e}")
            return None
    
    def _extract_reviews_from_html(self, html: str) -> List[Dict]:
        """Извлекает отзывы из HTML"""
        reviews = []
        
        try:
            # Ищем JSON данные в script тегах
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and 'reviews' in script.string.lower():
                    try:
                        # Ищем JSON с отзывами
                        script_text = script.string
                        
                        # Ищем паттерны типа "reviews": [...]
                        review_patterns = [
                            r'"reviews"\s*:\s*(\[.*?\])',
                            r'"feedback"\s*:\s*(\[.*?\])',
                            r'"comments"\s*:\s*(\[.*?\])'
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
                                except:
                                    continue
                    except:
                        continue
            
            # Если не нашли в JSON, ищем в HTML структуре
            if not reviews:
                review_elements = soup.select('[class*="review"], [class*="feedback"], [class*="comment"]')
                for elem in review_elements[:10]:  # Ограничиваем количество
                    review = self._parse_review_from_element(elem)
                    if review:
                        reviews.append(review)
            
            return reviews
            
        except Exception as e:
            print(f"❌ Ошибка извлечения отзывов: {e}")
            return []
    
    def _parse_single_review_from_data(self, review_data: Dict) -> Optional[Dict]:
        """Парсинг одного отзыва из JSON данных"""
        try:
            return {
                'id': review_data.get('id', ''),
                'author': review_data.get('author', {}).get('name', 'Аноним') if isinstance(review_data.get('author'), dict) else str(review_data.get('author', 'Аноним')),
                'text': review_data.get('text', '') or review_data.get('comment', ''),
                'rating': review_data.get('rating', 0) or review_data.get('score', 0),
                'date': review_data.get('date', '') or review_data.get('created_at', ''),
                'pros': review_data.get('pros', ''),
                'cons': review_data.get('cons', ''),
                'useful_count': review_data.get('useful', 0) or review_data.get('likes', 0),
                'is_anonymous': review_data.get('anonymous', False),
                'status': review_data.get('status', '')
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга отзыва из данных: {e}")
            return None
    
    def _parse_review_from_element(self, element) -> Optional[Dict]:
        """Парсинг отзыва из HTML элемента"""
        try:
            # Ищем автора
            author_elem = element.select_one('[class*="author"], [class*="user"], [class*="name"]')
            author = author_elem.get_text().strip() if author_elem else 'Аноним'
            
            # Ищем текст
            text_elem = element.select_one('[class*="text"], [class*="content"], [class*="comment"]')
            text = text_elem.get_text().strip() if text_elem else ''
            
            # Ищем рейтинг
            rating_elem = element.select_one('[class*="rating"], [class*="star"], [class*="score"]')
            rating = 0
            if rating_elem:
                rating_text = rating_elem.get_text().strip()
                rating_match = re.search(r'(\d+)', rating_text)
                if rating_match:
                    rating = int(rating_match.group(1))
            
            if text:  # Только если есть текст
                return {
                    'id': '',
                    'author': author,
                    'text': text,
                    'rating': rating,
                    'date': '',
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
        
        html = await self.get_product_page(product_url)
        if not html:
            return None
        
        price_info = self._extract_price_from_html(html)
        if price_info:
            price_info['product_id'] = self._extract_product_id(product_url)
        
        return price_info
    
    async def get_product_reviews(self, product_url: str, max_pages: int = 3) -> List[Dict]:
        """Получение отзывов товара"""
        print(f"📝 Парсинг отзывов: {product_url}")
        
        html = await self.get_product_page(product_url)
        if not html:
            return []
        
        reviews = self._extract_reviews_from_html(html)
        print(f"🎉 Найдено отзывов: {len(reviews)}")
        
        return reviews
    
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
        
        # Получаем HTML страницы
        html = await self.get_product_page(product_url)
        if not html:
            return result
        
        # Извлекаем цену
        price_info = self._extract_price_from_html(html)
        if price_info:
            price_info['product_id'] = result['product_id']
            result['price_info'] = price_info
        
        # Извлекаем отзывы
        reviews = self._extract_reviews_from_html(html)
        result['reviews'] = reviews
        result['reviews_count'] = len(reviews)
        
        # Вычисляем средний рейтинг
        if reviews:
            ratings = [r['rating'] for r in reviews if r.get('rating')]
            if ratings:
                result['average_rating'] = round(sum(ratings) / len(ratings), 2)
        
        return result


# Функции для быстрого использования
async def parse_ozon_html_price(product_url: str, proxy_config: Optional[Dict] = None) -> Optional[Dict]:
    """Быстрая функция для парсинга цены через HTML"""
    async with OzonHTMLParser(proxy_config) as parser:
        return await parser.get_product_price(product_url)

async def parse_ozon_html_reviews(product_url: str, proxy_config: Optional[Dict] = None) -> List[Dict]:
    """Быстрая функция для парсинга отзывов через HTML"""
    async with OzonHTMLParser(proxy_config) as parser:
        return await parser.get_product_reviews(product_url)

async def parse_ozon_html_full(product_url: str, proxy_config: Optional[Dict] = None) -> Dict:
    """Быстрая функция для полного парсинга через HTML"""
    async with OzonHTMLParser(proxy_config) as parser:
        return await parser.get_product_full_info(product_url)


# Пример использования
async def main():
    """Демонстрация работы HTML парсера"""
    
    proxy_config = {
        'scheme': 'http',
        'host': os.getenv('OZON_PROXY_HOST', 'your.proxy.host'),
        'port': int(os.getenv('OZON_PROXY_PORT', '8080')),
        'username': os.getenv('OZON_PROXY_USERNAME', 'user'),
        'password': os.getenv('OZON_PROXY_PASSWORD', 'pass')
    }
    
    product_url = "https://www.ozon.ru/product/your-product-123456/"
    
    print("🚀 Демонстрация работы Ozon HTML Parser")
    
    async with OzonHTMLParser(proxy_config) as parser:
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
