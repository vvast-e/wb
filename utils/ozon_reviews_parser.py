#!/usr/bin/env python3
"""
Парсер отзывов Ozon на основе API entrypoint
Адаптирован под проект WB_API
"""

import json
import re
import time
import os
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote, unquote

try:
    # curl_cffi даёт реальный TLS-отпечаток Chrome/Edge через impersonate
    from curl_cffi import requests as curl_requests  # type: ignore
except Exception:
    curl_requests = None

# Пытаемся реиспользовать уже готовый обход Cloudflare через FlareSolverr
try:
    from utils.ozon_playwright_parser import get_html_flaresolverr  # type: ignore
except Exception:
    get_html_flaresolverr = None

class OzonReviewsParser:
    """Парсер отзывов Ozon"""
    
    def __init__(self):
        self.base_url = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"
        self.session = None
        self.sync_session = None  # curl_cffi session
        # Прокси можно задать одной строкой (схема://user:pass@host:port)
        self.proxy_url = os.getenv("OZON_PROXY_URL")
        # или по частям
        self.proxy_host = os.getenv("OZON_PROXY_HOST")
        self.proxy_port = os.getenv("OZON_PROXY_PORT")
        self.proxy_user = os.getenv("OZON_PROXY_USERNAME")
        self.proxy_pass = os.getenv("OZON_PROXY_PASSWORD")
        self.proxy_scheme = os.getenv("OZON_PROXY_SCHEME", "http")
        # Настройки retry
        self.max_attempts = 4
        self.initial_backoff_seconds = 1.0
        
    async def __aenter__(self):
        # Базовые заголовки ближе к реальному браузеру/клиенту OZON
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Origin': 'https://www.ozon.ru',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-CH-UA': '"Chromium";v="124", "Not-A.Brand";v="24", "Google Chrome";v="124"',
            'Sec-CH-UA-Mobile': '?0',
            # dweb мета заголовки ozon
            'x-o3-app-name': 'dweb',
            'x-o3-app-version': 'release',
            'x-o3-language': 'ru'
        }
        self.base_headers = headers.copy()
        # httpx клиент (асинхронный) — прокси задаются на уровне клиента
        httpx_proxies = None
        if self.proxy_url:
            httpx_proxies = {"http://": self.proxy_url, "https://": self.proxy_url}
        else:
            if self.proxy_host and self.proxy_port:
                auth = f"{self.proxy_user}:{self.proxy_pass}@" if self.proxy_user and self.proxy_pass else ""
                proxy = f"{self.proxy_scheme}://{auth}{self.proxy_host}:{self.proxy_port}"
                httpx_proxies = {"http://": proxy, "https://": proxy}

        self.session = httpx.AsyncClient(headers=headers, timeout=30.0, proxies=httpx_proxies)

        # curl_cffi (синхронный), будет запускаться через asyncio.to_thread
        if curl_requests is not None:
            curl_proxies = None
            if self.proxy_url:
                curl_proxies = {"http": self.proxy_url, "https": self.proxy_url}
            else:
                if self.proxy_host and self.proxy_port:
                    auth = f"{self.proxy_user}:{self.proxy_pass}@" if self.proxy_user and self.proxy_pass else ""
                    curl_proxies = {
                        "http": f"{self.proxy_scheme}://{auth}{self.proxy_host}:{self.proxy_port}",
                        "https": f"{self.proxy_scheme}://{auth}{self.proxy_host}:{self.proxy_port}",
                    }
            # impersonate имитирует Chrome и корректный TLS fingerprint
            self.sync_session = curl_requests.Session(
                impersonate="chrome120",
                timeout=30.0,
                headers=headers,
                proxies=curl_proxies,
                verify=True,
            )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
        # curl_cffi сессия не требует async закрытия
        self.sync_session = None

    def _is_blocked_response(self, status_code: int, text: str, content_type: Optional[str]) -> bool:
        if status_code != 200:
            return True
        if content_type and "application/json" in content_type.lower():
            # Ожидаем JSON — ок
            return False
        # Частый случай блокировок — HTML/капча вместо JSON
        if "<html" in text.lower() or "captcha" in text.lower() or "attention required" in text.lower():
            return True
        # Если не JSON и выглядит как мусор
        try:
            _ = json.loads(text)
            return False
        except Exception:
            return True

    def _build_proxy_for_httpx(self) -> Optional[Dict[str, str]]:
        if self.proxy_url:
            return {"http://": self.proxy_url, "https://": self.proxy_url}
        if self.proxy_host and self.proxy_port:
            auth = f"{self.proxy_user}:{self.proxy_pass}@" if self.proxy_user and self.proxy_pass else ""
            proxy = f"{self.proxy_scheme}://{auth}{self.proxy_host}:{self.proxy_port}"
            return {"http://": proxy, "https://": proxy}
        return None

    async def _fetch_json_via_curl(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        if self.sync_session is None:
            return None
        def _do_get() -> Optional[Dict]:
            resp = self.sync_session.get(url, headers=headers or self.base_headers)
            ct = resp.headers.get("Content-Type")
            text = resp.text
            if self._is_blocked_response(resp.status_code, text, ct):
                return None
            try:
                return resp.json()
            except Exception:
                try:
                    return json.loads(text)
                except Exception:
                    return None
        return await asyncio.to_thread(_do_get)

    async def _fetch_json_via_httpx(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        # Прокси уже настроены на уровне AsyncClient в __aenter__
        resp = await self.session.get(url, headers=headers or self.base_headers)
        ct = resp.headers.get("Content-Type")
        text = resp.text
        if self._is_blocked_response(resp.status_code, text, ct):
            return None
        try:
            return resp.json()
        except Exception:
            try:
                return json.loads(text)
            except Exception:
                return None

    async def _fetch_json_via_flaresolverr(self, url: str) -> Optional[Dict]:
        if get_html_flaresolverr is None:
            return None
        try:
            raw = await get_html_flaresolverr(url)
            return json.loads(raw)
        except Exception:
            return None
    
    def build_reviews_url(self, product_url: str, page: int = 1, page_key: str = "", start_page_id: str = "") -> str:
        """Строит URL для получения отзывов"""
        # Базовые параметры
        params = {
            'layout_container': 'reviewshelfpaginator',
            'layout_page_index': page + 10,  # Ozon использует page_index = page + 10
            'page': page,
            'reviewsVariantMode': '2',
            'sort': 'published_at_desc'
        }
        
        if page_key:
            params['page_key'] = page_key
        if start_page_id:
            params['start_page_id'] = start_page_id
            
        # Кодируем URL товара
        encoded_url = quote(product_url, safe='')
        
        # Собираем финальный URL
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.base_url}?url={encoded_url}&{query_string}"
    
    async def get_reviews_page(self, product_url: str, page: int = 1, page_key: str = "", start_page_id: str = "") -> Optional[Dict]:
        """Получает страницу отзывов с многоступенчатым обходом антибота."""
        url = self.build_reviews_url(product_url, page, page_key, start_page_id)
        # Задаём реальный Referer на карточку товара
        full_product_url = product_url if product_url.startswith('http') else f"https://www.ozon.ru{product_url}"
        per_request_headers = getattr(self, 'base_headers', {}).copy() if hasattr(self, 'base_headers') else {}
        per_request_headers['Referer'] = full_product_url
        print(f"[OZON REVIEWS] Запрос страницы {page}: {url}")
        attempt = 1
        backoff = self.initial_backoff_seconds
        while attempt <= self.max_attempts:
            try:
                # 1) Пытаемся через curl_cffi (наиболее устойчивый TLS-отпечаток)
                data = await self._fetch_json_via_curl(url, headers=per_request_headers)
                if data:
                    return data
                # 2) Пробуем httpx с прокси (если задано)
                data = await self._fetch_json_via_httpx(url, headers=per_request_headers)
                if data:
                    return data
                # 3) Фолбэк: FlareSolverr (Cloudflare антибот)
                data = await self._fetch_json_via_flaresolverr(url)
                if data:
                    return data
            except Exception as e:
                print(f"[OZON REVIEWS] Попытка {attempt} — ошибка: {e}")
            # Экспоненциальная пауза с джиттером
            sleep_for = backoff + (0.2 * backoff * (0.5 - (time.time() % 1)))
            print(f"[OZON REVIEWS] Блок/ошибка, пауза {sleep_for:.2f}s и ретрай...")
            await asyncio.sleep(sleep_for)
            backoff *= 2
            attempt += 1
        print("[OZON REVIEWS] Все попытки исчерпаны")
        return None
    
    def extract_reviews_from_response(self, response_data: Dict) -> List[Dict]:
        """Извлекает отзывы из ответа API"""
        reviews = []
        
        try:
            # Ищем widgetStates с отзывами
            widget_states = response_data.get('widgetStates', {})
            
            for widget_id, widget_data in widget_states.items():
                if 'webListReviews' in widget_id:
                    try:
                        widget_json = json.loads(widget_data)
                        reviews_list = widget_json.get('reviews', [])
                        
                        for review in reviews_list:
                            parsed_review = self.parse_single_review(review)
                            if parsed_review:
                                reviews.append(parsed_review)
                                
                    except json.JSONDecodeError as e:
                        print(f"[OZON REVIEWS] Ошибка парсинга JSON отзывов: {e}")
                        continue
                        
        except Exception as e:
            print(f"[OZON REVIEWS] Ошибка при извлечении отзывов: {e}")
            
        return reviews
    
    def parse_single_review(self, review_data: Dict) -> Optional[Dict]:
        """Парсит один отзыв"""
        try:
            # Основные поля
            review = {
                'uuid': review_data.get('uuid', ''),
                'author_name': review_data.get('author', {}).get('firstName', ''),
                'author_lastname': review_data.get('author', {}).get('lastName', ''),
                'text': review_data.get('content', {}).get('comment', ''),
                'rating': review_data.get('content', {}).get('score', 0),
                'published_at': review_data.get('publishedAt', 0),
                'status': review_data.get('status', {}).get('name', ''),
                'item_id': review_data.get('itemId', ''),
                'is_anonymous': review_data.get('isAnonymous', False),
                'useful_count': review_data.get('usefulness', {}).get('useful', 0),
                'unuseful_count': review_data.get('usefulness', {}).get('unuseful', 0)
            }
            
            # Проверяем обязательные поля
            if not review['uuid'] or not review['text']:
                return None
                
            return review
            
        except Exception as e:
            print(f"[OZON REVIEWS] Ошибка при парсинге отзыва: {e}")
            return None
    
    def get_next_page_info(self, response_data: Dict) -> tuple:
        """Получает информацию для следующей страницы"""
        try:
            # Ищем nextPage в ответе
            next_page = response_data.get('nextPage', '')
            if next_page:
                # Извлекаем параметры из nextPage
                page_match = re.search(r'page=(\d+)', next_page)
                page_key_match = re.search(r'page_key=([^&]+)', next_page)
                start_page_id_match = re.search(r'start_page_id=([^&]+)', next_page)
                
                next_page_num = int(page_match.group(1)) if page_match else None
                next_page_key = page_key_match.group(1) if page_key_match else ""
                next_start_page_id = start_page_id_match.group(1) if start_page_id_match else ""
                
                return next_page_num, next_page_key, next_start_page_id
                
        except Exception as e:
            print(f"[OZON REVIEWS] Ошибка при получении информации о следующей странице: {e}")
            
        return None, "", ""
    
    async def parse_all_reviews(self, product_url: str, max_pages: int = 10) -> List[Dict]:
        """Парсит все отзывы товара"""
        all_reviews = []
        page = 1
        page_key = ""
        start_page_id = ""
        
        print(f"[OZON REVIEWS] Начинаем парсинг отзывов для: {product_url}")
        
        while page <= max_pages:
            print(f"[OZON REVIEWS] Обрабатываем страницу {page}")
            
            # Получаем страницу отзывов
            response_data = await self.get_reviews_page(product_url, page, page_key, start_page_id)
            if not response_data:
                print(f"[OZON REVIEWS] Не удалось получить страницу {page}")
                break
            
            # Извлекаем отзывы
            page_reviews = self.extract_reviews_from_response(response_data)
            if not page_reviews:
                print(f"[OZON REVIEWS] На странице {page} отзывов не найдено")
                break
            
            all_reviews.extend(page_reviews)
            print(f"[OZON REVIEWS] Страница {page}: найдено {len(page_reviews)} отзывов")
            
            # Получаем информацию для следующей страницы
            next_page, next_page_key, next_start_page_id = self.get_next_page_info(response_data)
            
            if not next_page or next_page <= page:
                print(f"[OZON REVIEWS] Достигнут конец отзывов на странице {page}")
                break
            
            page = next_page
            page_key = next_page_key
            start_page_id = next_start_page_id
            
            # Пауза между запросами
            await asyncio.sleep(1)
        
        print(f"[OZON REVIEWS] Парсинг завершен. Всего отзывов: {len(all_reviews)}")
        return all_reviews

# Пример использования
async def main():
    """Тестовая функция"""
    product_url = "/product/termozashchitnyy-sprey-dlya-volos-uvlazhnyayushchiy-nesmyvaemyy-uhod-dlya-legkogo-2128381166/"
    
    async with OzonReviewsParser() as parser:
        reviews = await parser.parse_all_reviews(product_url, max_pages=3)
        
        print(f"\nНайдено отзывов: {len(reviews)}")
        for i, review in enumerate(reviews[:3], 1):
            print(f"\nОтзыв {i}:")
            print(f"Автор: {review['author_name']} {review['author_lastname']}")
            print(f"Оценка: {review['rating']}/5")
            print(f"Текст: {review['text'][:100]}...")
            print(f"Дата: {datetime.fromtimestamp(review['published_at'])}")

if __name__ == "__main__":
    asyncio.run(main())














