#!/usr/bin/env python3
"""
Парсер отзывов Ozon на основе API entrypoint
Адаптирован под проект WB_API
"""

import json
import re
import time
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote, unquote

class OzonReviewsParser:
    """Парсер отзывов Ozon"""
    
    def __init__(self):
        self.base_url = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Referer': 'https://www.ozon.ru/',
                'Origin': 'https://www.ozon.ru'
            },
            timeout=30.0
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
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
        """Получает страницу отзывов"""
        try:
            url = self.build_reviews_url(product_url, page, page_key, start_page_id)
            print(f"[OZON REVIEWS] Запрос страницы {page}: {url}")
            
            response = await self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                print(f"[OZON REVIEWS] Ошибка {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"[OZON REVIEWS] Ошибка при получении страницы {page}: {e}")
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












