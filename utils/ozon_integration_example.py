#!/usr/bin/env python3
"""
Пример интеграции Ozon Mobile Stealth Parser с проектом WB_API

Показывает как использовать новый парсер для получения отзывов и цен Ozon
в рамках существующей архитектуры проекта
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from utils.ozon_mobile_stealth_parser import OzonMobileStealthParser
from utils.ozon_mobile_config import get_regional_profile, OzonMobileConfig


class OzonDataCollector:
    """Интеграционный класс для сбора данных с Ozon"""
    
    def __init__(self, proxy_config: Optional[Dict] = None, region: str = 'moscow'):
        """
        proxy_config: Конфигурация прокси
        region: Регион для эмуляции (moscow, spb, ekaterinburg, novosibirsk)
        """
        self.proxy_config = proxy_config or self._load_proxy_from_env()
        self.region = region
        self.results_cache = {}
    
    def _load_proxy_from_env(self) -> Optional[Dict]:
        """Загружает конфигурацию прокси из переменных окружения"""
        host = os.getenv('OZON_PROXY_HOST')
        port = os.getenv('OZON_PROXY_PORT')
        username = os.getenv('OZON_PROXY_USERNAME')
        password = os.getenv('OZON_PROXY_PASSWORD')
        scheme = os.getenv('OZON_PROXY_SCHEME', 'http')
        
        if host and port:
            return {
                'scheme': scheme,
                'host': host,
                'port': int(port),
                'username': username,
                'password': password
            }
        return None
    
    async def collect_product_data(self, product_urls: List[str], 
                                 include_reviews: bool = True,
                                 include_prices: bool = True,
                                 max_review_pages: int = 3) -> List[Dict]:
        """
        Собирает данные по списку товаров Ozon
        
        Args:
            product_urls: Список URL товаров
            include_reviews: Собирать ли отзывы
            include_prices: Собирать ли цены
            max_review_pages: Максимум страниц отзывов
        
        Returns:
            Список словарей с данными товаров
        """
        print(f"🚀 Запуск сбора данных для {len(product_urls)} товаров Ozon")
        print(f"📊 Настройки: отзывы={include_reviews}, цены={include_prices}")
        
        results = []
        
        async with OzonMobileStealthParser(self.proxy_config) as parser:
            for i, url in enumerate(product_urls, 1):
                print(f"\n📦 Обработка товара {i}/{len(product_urls)}: {url}")
                
                try:
                    # Базовая информация
                    product_data = {
                        'url': url,
                        'product_id': parser._extract_product_id(url),
                        'collected_at': datetime.now().isoformat(),
                        'region': self.region,
                        'success': True,
                        'error': None
                    }
                    
                    # Собираем цену
                    if include_prices:
                        print("💰 Сбор информации о цене...")
                        price_info = await parser.get_product_price(url)
                        product_data['price_info'] = price_info
                        
                        if price_info:
                            print(f"✅ Цена: {price_info.get('current_price')} руб.")
                        else:
                            print("⚠️ Цена не найдена")
                    
                    # Собираем отзывы
                    if include_reviews:
                        print(f"📝 Сбор отзывов (до {max_review_pages} страниц)...")
                        reviews = await parser.get_product_reviews(url, max_review_pages)
                        product_data['reviews'] = reviews
                        product_data['reviews_count'] = len(reviews)
                        
                        if reviews:
                            # Вычисляем статистику
                            ratings = [r['rating'] for r in reviews if r.get('rating')]
                            if ratings:
                                product_data['average_rating'] = round(sum(ratings) / len(ratings), 2)
                                product_data['rating_distribution'] = self._calculate_rating_distribution(ratings)
                            
                            print(f"✅ Собрано {len(reviews)} отзывов, средний рейтинг: {product_data.get('average_rating', 'N/A')}")
                        else:
                            print("⚠️ Отзывы не найдены")
                    
                    results.append(product_data)
                    
                    # Пауза между товарами
                    if i < len(product_urls):
                        delay = self._calculate_delay(i, len(product_urls))
                        print(f"⏳ Пауза {delay}с перед следующим товаром...")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    print(f"❌ Ошибка обработки товара {url}: {e}")
                    results.append({
                        'url': url,
                        'success': False,
                        'error': str(e),
                        'collected_at': datetime.now().isoformat()
                    })
        
        print(f"\n🎉 Сбор данных завершен: {len(results)} товаров обработано")
        return results
    
    def _calculate_rating_distribution(self, ratings: List[int]) -> Dict[str, int]:
        """Вычисляет распределение рейтингов"""
        distribution = {str(i): 0 for i in range(1, 6)}
        for rating in ratings:
            if 1 <= rating <= 5:
                distribution[str(rating)] += 1
        return distribution
    
    def _calculate_delay(self, current: int, total: int) -> float:
        """Вычисляет задержку между запросами"""
        import random
        
        # Базовая задержка
        base_delay = random.uniform(3.0, 6.0)
        
        # Увеличиваем задержку каждые 10 товаров
        if current % 10 == 0:
            base_delay += random.uniform(5.0, 10.0)
        
        # Увеличиваем к концу для снижения подозрений
        if current > total * 0.7:
            base_delay += random.uniform(2.0, 5.0)
        
        return base_delay
    
    def save_results_to_json(self, results: List[Dict], filename: str = None):
        """Сохраняет результаты в JSON файл"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ozon_data_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Результаты сохранены в {filename}")
    
    def generate_summary_report(self, results: List[Dict]) -> Dict:
        """Генерирует сводный отчет по собранным данным"""
        total_products = len(results)
        successful = len([r for r in results if r.get('success', False)])
        failed = total_products - successful
        
        # Статистика по ценам
        prices = [r.get('price_info', {}).get('current_price') for r in results if r.get('price_info')]
        prices = [p for p in prices if p is not None]
        
        price_stats = {}
        if prices:
            price_stats = {
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': round(sum(prices) / len(prices), 2),
                'count': len(prices)
            }
        
        # Статистика по отзывам
        all_reviews = []
        for result in results:
            if result.get('reviews'):
                all_reviews.extend(result['reviews'])
        
        review_stats = {
            'total_reviews': len(all_reviews),
            'products_with_reviews': len([r for r in results if r.get('reviews_count', 0) > 0])
        }
        
        if all_reviews:
            ratings = [r['rating'] for r in all_reviews if r.get('rating')]
            if ratings:
                review_stats.update({
                    'avg_rating': round(sum(ratings) / len(ratings), 2),
                    'rating_distribution': self._calculate_rating_distribution(ratings)
                })
        
        return {
            'collection_summary': {
                'total_products': total_products,
                'successful': successful,
                'failed': failed,
                'success_rate': round(successful / total_products * 100, 2) if total_products > 0 else 0,
                'collected_at': datetime.now().isoformat(),
                'region': self.region
            },
            'price_statistics': price_stats,
            'review_statistics': review_stats
        }


async def example_usage():
    """Пример использования интеграции"""
    
    # Конфигурация прокси (замените на свои данные)
    proxy_config = {
        'scheme': 'http',
        'host': 'your.mobile.proxy.host',
        'port': 8080,
        'username': 'your_username',
        'password': 'your_password'
    }
    
    # Список товаров для парсинга (замените на реальные URL)
    product_urls = [
        "https://www.ozon.ru/product/example-product-1-123456/",
        "https://www.ozon.ru/product/example-product-2-789012/",
        "https://www.ozon.ru/product/example-product-3-345678/",
    ]
    
    # Создаем коллектор данных
    collector = OzonDataCollector(proxy_config, region='moscow')
    
    # Собираем данные
    results = await collector.collect_product_data(
        product_urls=product_urls,
        include_reviews=True,
        include_prices=True,
        max_review_pages=3
    )
    
    # Сохраняем результаты
    collector.save_results_to_json(results)
    
    # Генерируем отчет
    report = collector.generate_summary_report(results)
    
    print("\n📊 СВОДНЫЙ ОТЧЕТ:")
    print(f"✅ Успешно обработано: {report['collection_summary']['successful']}")
    print(f"❌ Ошибок: {report['collection_summary']['failed']}")
    print(f"📈 Процент успеха: {report['collection_summary']['success_rate']}%")
    
    if report['price_statistics']:
        ps = report['price_statistics']
        print(f"💰 Цены: от {ps['min_price']} до {ps['max_price']} руб. (средняя: {ps['avg_price']})")
    
    if report['review_statistics']['total_reviews'] > 0:
        rs = report['review_statistics']
        print(f"📝 Отзывов собрано: {rs['total_reviews']}")
        if 'avg_rating' in rs:
            print(f"⭐ Средний рейтинг: {rs['avg_rating']}/5")


# Функции для интеграции с существующим проектом

async def parse_ozon_for_brand(brand_name: str, product_urls: List[str], 
                              proxy_config: Optional[Dict] = None) -> Dict:
    """
    Парсинг товаров Ozon для конкретного бренда
    (аналогично функциям для WB в проекте)
    """
    collector = OzonDataCollector(proxy_config)
    
    results = await collector.collect_product_data(
        product_urls=product_urls,
        include_reviews=True,
        include_prices=True
    )
    
    # Адаптируем под формат проекта WB_API
    adapted_results = {
        'brand': brand_name,
        'platform': 'ozon',
        'products': results,
        'summary': collector.generate_summary_report(results),
        'collected_at': datetime.now().isoformat()
    }
    
    return adapted_results


async def get_ozon_competitor_prices(competitor_urls: List[str],
                                   proxy_config: Optional[Dict] = None) -> List[Dict]:
    """
    Получение цен конкурентов с Ozon
    (для аналитики конкурентов)
    """
    collector = OzonDataCollector(proxy_config)
    
    results = await collector.collect_product_data(
        product_urls=competitor_urls,
        include_reviews=False,
        include_prices=True
    )
    
    # Возвращаем только информацию о ценах
    price_data = []
    for result in results:
        if result.get('success') and result.get('price_info'):
            price_data.append({
                'url': result['url'],
                'product_id': result['product_id'],
                'price_info': result['price_info'],
                'collected_at': result['collected_at']
            })
    
    return price_data


if __name__ == "__main__":
    print("🚀 Демонстрация интеграции Ozon парсера")
    asyncio.run(example_usage())
