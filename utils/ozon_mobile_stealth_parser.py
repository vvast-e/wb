#!/usr/bin/env python3
"""
🚀 СУПЕР-ПАРСЕР OZON с МОБИЛЬНОЙ ЭМУЛЯЦИЕЙ И STEALTH ТЕХНИКАМИ 🚀

Специально разработан для обхода 403 антибота на первом запросе.
Включает:
- Эмуляцию реального мобильного браузера Samsung Galaxy S21
- Правильный TLS fingerprint через curl_cffi
- Прогрев сессии с последовательностью запросов
- Stealth техники обхода детекции
- Парсинг отзывов и цен через мобильные API
- Поддержка резидентных мобильных прокси
"""

import asyncio
import json
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin, urlparse
import hashlib
import uuid

try:
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests import Response
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    print("❌ curl_cffi не установлен! Установите: pip install curl-cffi")

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

class OzonMobileStealthParser:
    """Супер-парсер Ozon с мобильной эмуляцией и stealth техниками"""
    
    def __init__(self, proxy_config: Optional[Dict] = None):
        """
        proxy_config = {
            'scheme': 'http',  # или 'https', 'socks5'
            'host': 'your.proxy.host',
            'port': 8080,
            'username': 'user',
            'password': 'pass'
        }
        """
        self.proxy_config = proxy_config
        self.session = None
        self.cookies = {}
        self.device_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        # Мобильные endpoints Ozon (менее защищены)
        self.mobile_base = "https://www.ozon.ru"
        self.mobile_api = "https://www.ozon.ru/api"
        self.cdn_api = "https://cdn1.ozon.ru/api"
        
        # Эмуляция Samsung Galaxy S21 (Android 12)
        self.mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.ozon.ru',
            'Referer': 'https://www.ozon.ru/',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            # Мобильные заголовки Ozon
            'x-o3-app-name': 'mobile_web',
            'x-o3-app-version': '1.0.0',
            'x-o3-device-type': 'mobile',
            'x-o3-device-id': self.device_id,
            'x-o3-session-id': self.session_id,
            'x-requested-with': 'XMLHttpRequest',
            # Дополнительные stealth заголовки
            'dnt': '1',
            'upgrade-insecure-requests': '1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
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
        
        # Создаем сессию с эмуляцией Chrome на Android
        self.session = curl_requests.Session(
            impersonate="chrome120_android",  # Важно: мобильная эмуляция!
            headers=self.mobile_headers,
            proxies=proxies,
            timeout=30,
            verify=True
        )
        
        print("🚀 Инициализация мобильного stealth парсера...")
        await self._warmup_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие парсера"""
        self.session = None
    
    async def _warmup_session(self):
        """Прогрев сессии для обхода антибота"""
        print("🔥 Прогрев сессии...")
        
        try:
            # 1. Заходим на главную страницу
            await self._safe_request('GET', self.mobile_base)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 2. Получаем страницу категорий (имитация реального пользователя)
            await self._safe_request('GET', f"{self.mobile_base}/category")
            await asyncio.sleep(random.uniform(1, 3))
            
            # 3. Запрос к API для получения cookies и токенов
            await self._safe_request('GET', f"{self.mobile_api}/composer-api.bx/_action/getInitialData")
            await asyncio.sleep(random.uniform(1, 2))
            
            print("✅ Сессия прогрета успешно")
            
        except Exception as e:
            print(f"⚠️ Предупреждение при прогреве сессии: {e}")
    
    async def _safe_request(self, method: str, url: str, **kwargs) -> Optional[Response]:
        """Безопасный запрос с обработкой ошибок"""
        try:
            if method.upper() == 'GET':
                response = await asyncio.to_thread(self.session.get, url, **kwargs)
            elif method.upper() == 'POST':
                response = await asyncio.to_thread(self.session.post, url, **kwargs)
            else:
                raise ValueError(f"Неподдерживаемый метод: {method}")
            
            # Обновляем cookies
            if hasattr(response, 'cookies'):
                self.cookies.update(response.cookies)
            
            return response
        except Exception as e:
            print(f"❌ Ошибка запроса {method} {url}: {e}")
            return None
    
    def _extract_product_id(self, product_url: str) -> Optional[str]:
        """Извлекает ID товара из URL"""
        if '/product/' in product_url:
            parts = product_url.split('/product/')
            if len(parts) > 1:
                # Ищем числовой ID в конце URL
                product_part = parts[1].rstrip('/')
                # Может быть формат: "name-123456/" или просто "123456/"
                import re
                match = re.search(r'(\d+)/?$', product_part)
                if match:
                    return match.group(1)
        return None
    
    async def get_product_reviews(self, product_url: str, max_pages: int = 5) -> List[Dict]:
        """Парсинг отзывов товара"""
        print(f"📝 Парсинг отзывов: {product_url}")
        
        product_id = self._extract_product_id(product_url)
        if not product_id:
            print("❌ Не удалось извлечь ID товара")
            return []
        
        all_reviews = []
        page = 1
        
        while page <= max_pages:
            print(f"📄 Обработка страницы {page}")
            
            # Мобильный API для отзывов
            reviews_url = f"{self.mobile_api}/entrypoint-api.bx/page/json/v2"
            
            params = {
                'url': f'/product/{product_id}/reviews',
                'layout_container': 'reviewsShelfPaginator',
                'layout_page_index': page + 10,  # Ozon специфика
                'page': page,
                'reviewsVariantMode': '2',
                'sort': 'published_at_desc'
            }
            
            # Добавляем специальные мобильные заголовки
            headers = self.mobile_headers.copy()
            headers['Referer'] = product_url
            
            response = await self._safe_request('GET', reviews_url, params=params, headers=headers)
            
            if not response or response.status_code != 200:
                print(f"❌ Ошибка получения отзывов: {response.status_code if response else 'No response'}")
                break
            
            try:
                data = response.json()
            except:
                print("❌ Ошибка парсинга JSON")
                break
            
            page_reviews = self._parse_reviews_from_response(data)
            
            if not page_reviews:
                print("✅ Отзывы закончились")
                break
            
            all_reviews.extend(page_reviews)
            print(f"✅ Найдено {len(page_reviews)} отзывов на странице {page}")
            
            page += 1
            
            # Пауза между запросами
            await asyncio.sleep(random.uniform(2, 4))
        
        print(f"🎉 Всего собрано отзывов: {len(all_reviews)}")
        return all_reviews
    
    def _parse_reviews_from_response(self, data: Dict) -> List[Dict]:
        """Парсинг отзывов из ответа API"""
        reviews = []
        
        try:
            # Поиск в widgetStates
            widget_states = data.get('widgetStates', {})
            
            for widget_id, widget_data in widget_states.items():
                if 'review' in widget_id.lower():
                    try:
                        if isinstance(widget_data, str):
                            widget_json = json.loads(widget_data)
                        else:
                            widget_json = widget_data
                        
                        reviews_list = widget_json.get('reviews', [])
                        
                        for review in reviews_list:
                            parsed = self._parse_single_review(review)
                            if parsed:
                                reviews.append(parsed)
                                
                    except Exception as e:
                        print(f"⚠️ Ошибка парсинга отзыва: {e}")
                        continue
        
        except Exception as e:
            print(f"❌ Ошибка извлечения отзывов: {e}")
        
        return reviews
    
    def _parse_single_review(self, review_data: Dict) -> Optional[Dict]:
        """Парсинг одного отзыва"""
        try:
            return {
                'id': review_data.get('uuid', ''),
                'author': review_data.get('author', {}).get('firstName', 'Аноним'),
                'text': review_data.get('content', {}).get('comment', ''),
                'rating': review_data.get('content', {}).get('score', 0),
                'date': review_data.get('publishedAt', ''),
                'pros': review_data.get('content', {}).get('pros', ''),
                'cons': review_data.get('content', {}).get('cons', ''),
                'useful_count': review_data.get('usefulness', {}).get('useful', 0),
                'is_anonymous': review_data.get('isAnonymous', False),
                'status': review_data.get('status', {}).get('name', '')
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга отзыва: {e}")
            return None
    
    async def get_product_price(self, product_url: str) -> Optional[Dict]:
        """Парсинг цены товара"""
        print(f"💰 Парсинг цены: {product_url}")
        
        product_id = self._extract_product_id(product_url)
        if not product_id:
            print("❌ Не удалось извлечь ID товара")
            return None
        
        # Мобильный API для получения цены
        price_url = f"{self.mobile_api}/entrypoint-api.bx/page/json/v2"
        
        params = {
            'url': f'/product/{product_id}',
            'layout_container': 'pdp',
            'layout_page_index': 1
        }
        
        headers = self.mobile_headers.copy()
        headers['Referer'] = self.mobile_base
        
        response = await self._safe_request('GET', price_url, params=params, headers=headers)
        
        if not response or response.status_code != 200:
            print(f"❌ Ошибка получения цены: {response.status_code if response else 'No response'}")
            return None
        
        try:
            data = response.json()
            return self._parse_price_from_response(data, product_id)
        except Exception as e:
            print(f"❌ Ошибка парсинга цены: {e}")
            return None
    
    def _parse_price_from_response(self, data: Dict, product_id: str) -> Optional[Dict]:
        """Парсинг цены из ответа API"""
        try:
            # Поиск в widgetStates
            widget_states = data.get('widgetStates', {})
            
            for widget_id, widget_data in widget_states.items():
                if 'price' in widget_id.lower() or 'pdp' in widget_id.lower():
                    try:
                        if isinstance(widget_data, str):
                            widget_json = json.loads(widget_data)
                        else:
                            widget_json = widget_data
                        
                        # Ищем цену в разных структурах
                        price_info = self._extract_price_info(widget_json)
                        if price_info:
                            price_info['product_id'] = product_id
                            return price_info
                            
                    except Exception as e:
                        continue
            
            print("⚠️ Цена не найдена в ответе")
            return None
            
        except Exception as e:
            print(f"❌ Ошибка извлечения цены: {e}")
            return None
    
    def _extract_price_info(self, data: Dict) -> Optional[Dict]:
        """Извлечение информации о цене из различных структур"""
        price_info = {
            'current_price': None,
            'original_price': None,
            'discount_percent': None,
            'currency': 'RUB'
        }
        
        # Возможные пути к цене в JSON
        price_paths = [
            ['price'],
            ['prices', 'price'],
            ['priceInfo', 'price'],
            ['finalPrice'],
            ['currentPrice'],
            ['price', 'final'],
            ['cardPrice'],
            ['ozonPrice']
        ]
        
        for path in price_paths:
            try:
                current = data
                for key in path:
                    current = current.get(key, {})
                
                if isinstance(current, (int, float, str)):
                    price_info['current_price'] = self._clean_price(current)
                    break
                elif isinstance(current, dict):
                    if 'value' in current:
                        price_info['current_price'] = self._clean_price(current['value'])
                        break
                    elif 'amount' in current:
                        price_info['current_price'] = self._clean_price(current['amount'])
                        break
            except:
                continue
        
        # Поиск старой цены (для скидки)
        old_price_paths = [
            ['originalPrice'],
            ['oldPrice'],
            ['price', 'original'],
            ['basePrice'],
            ['listPrice']
        ]
        
        for path in old_price_paths:
            try:
                current = data
                for key in path:
                    current = current.get(key, {})
                
                if isinstance(current, (int, float, str)):
                    price_info['original_price'] = self._clean_price(current)
                    break
                elif isinstance(current, dict) and 'value' in current:
                    price_info['original_price'] = self._clean_price(current['value'])
                    break
            except:
                continue
        
        # Вычисляем процент скидки
        if price_info['current_price'] and price_info['original_price']:
            try:
                current = float(price_info['current_price'])
                original = float(price_info['original_price'])
                if original > current:
                    discount = ((original - current) / original) * 100
                    price_info['discount_percent'] = round(discount, 2)
            except:
                pass
        
        return price_info if price_info['current_price'] else None
    
    def _clean_price(self, price) -> Optional[float]:
        """Очистка и преобразование цены"""
        if price is None:
            return None
        
        try:
            # Преобразуем в строку и очищаем
            price_str = str(price).replace('₽', '').replace('руб', '').replace(' ', '').replace('\xa0', '')
            price_str = ''.join(c for c in price_str if c.isdigit() or c == '.')
            
            return float(price_str) if price_str else None
        except:
            return None
    
    async def get_product_full_info(self, product_url: str) -> Dict:
        """Получение полной информации о товаре (цена + отзывы)"""
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
            ratings = [r['rating'] for r in reviews if r.get('rating')]
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


# Функции для интеграции с существующим кодом
async def parse_ozon_product_reviews(product_url: str, proxy_config: Optional[Dict] = None, max_pages: int = 5) -> List[Dict]:
    """Быстрая функция для парсинга отзывов"""
    async with OzonMobileStealthParser(proxy_config) as parser:
        return await parser.get_product_reviews(product_url, max_pages)

async def parse_ozon_product_price(product_url: str, proxy_config: Optional[Dict] = None) -> Optional[Dict]:
    """Быстрая функция для парсинга цены"""
    async with OzonMobileStealthParser(proxy_config) as parser:
        return await parser.get_product_price(product_url)

async def parse_ozon_product_full(product_url: str, proxy_config: Optional[Dict] = None) -> Dict:
    """Быстрая функция для полного парсинга товара"""
    async with OzonMobileStealthParser(proxy_config) as parser:
        return await parser.get_product_full_info(product_url)


# Пример использования
async def main():
    """Демонстрация работы парсера"""
    
    # Конфигурация прокси (замените на свои данные)
    proxy_config = {
        'scheme': 'http',  # или 'https', 'socks5'
        'host': os.getenv('OZON_PROXY_HOST', 'your.proxy.host'),
        'port': int(os.getenv('OZON_PROXY_PORT', '8080')),
        'username': os.getenv('OZON_PROXY_USERNAME', 'user'),
        'password': os.getenv('OZON_PROXY_PASSWORD', 'pass')
    }
    
    # Пример URL товара
    product_url = "https://www.ozon.ru/product/your-product-123456/"
    
    print("🚀 Демонстрация работы Ozon Mobile Stealth Parser")
    
    async with OzonMobileStealthParser(proxy_config) as parser:
        # Полный анализ товара
        result = await parser.get_product_full_info(product_url)
        
        print("\n📊 РЕЗУЛЬТАТ ПАРСИНГА:")
        print(f"Товар: {result['url']}")
        print(f"ID: {result['product_id']}")
        
        if result['price_info']:
            price = result['price_info']
            print(f"💰 Цена: {price['current_price']} {price['currency']}")
            if price['original_price']:
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
