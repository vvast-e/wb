#!/usr/bin/env python3
"""
🧪 ТЕСТ OZON FLARESOLVERR ПАРСЕРА 🧪

Тестирование нового стабильного парсера Ozon через FlareSolverr
"""

import asyncio
import json
import os
from datetime import datetime

# Импортируем новый парсер
from utils.ozon_flaresolverr_parser import OzonFlareSolverrParser, parse_ozon_flaresolverr_full

# Настройки прокси
PROXY_CONFIG = {
    'scheme': 'http',
    'host': 'p15184.ltespace.net',
    'port': 15184,
    'username': 'uek7t66y',
    'password': 'zbygddap'
}

# URL товара для тестирования
TEST_PRODUCT_URL = "https://www.ozon.ru/product/termozashchitnyy-sprey-dlya-volos-uvlazhnyayushchiy-nesmyvaemyy-uhod-dlya-legkogo-2128381166/?__rr=3&at=EqtkV5nBRhyWXGM9iY1OEWVhDKJLXvsrZVAMkFZK70J2"

async def test_flaresolverr_connection():
    """Тест подключения к FlareSolverr"""
    print("🔥 ТЕСТ ПОДКЛЮЧЕНИЯ К FLARESOLVERR")
    print("-" * 50)
    
    try:
        async with OzonFlareSolverrParser(PROXY_CONFIG) as parser:
            print("✅ FlareSolverr парсер инициализирован успешно")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к FlareSolverr: {e}")
        return False

async def test_price_parsing():
    """Тест парсинга цены"""
    print("\n💰 ТЕСТ ПАРСИНГА ЦЕНЫ")
    print("-" * 50)
    
    try:
        async with OzonFlareSolverrParser(PROXY_CONFIG) as parser:
            price_info = await parser.get_product_price(TEST_PRODUCT_URL)
            
            if price_info:
                print("✅ Цена получена успешно!")
                print(f"💰 Текущая цена: {price_info['current_price']} {price_info['currency']}")
                if price_info.get('original_price'):
                    print(f"💸 Старая цена: {price_info['original_price']} {price_info['currency']}")
                    print(f"🎯 Скидка: {price_info['discount_percent']}%")
                return True, price_info
            else:
                print("❌ Цена не получена")
                return False, None
                
    except Exception as e:
        print(f"❌ Ошибка парсинга цены: {e}")
        return False, None

async def test_reviews_parsing():
    """Тест парсинга отзывов"""
    print("\n📝 ТЕСТ ПАРСИНГА ОТЗЫВОВ")
    print("-" * 50)
    
    try:
        async with OzonFlareSolverrParser(PROXY_CONFIG) as parser:
            reviews = await parser.get_product_reviews(TEST_PRODUCT_URL, max_pages=2)
            
            if reviews:
                print(f"✅ Получено отзывов: {len(reviews)}")
                
                # Показываем первые 3 отзыва
                for i, review in enumerate(reviews[:3], 1):
                    print(f"\n📄 Отзыв {i}:")
                    print(f"   Автор: {review['author']}")
                    print(f"   Рейтинг: {review['rating']}/5")
                    print(f"   Текст: {review['text'][:100]}...")
                
                return True, reviews
            else:
                print("❌ Отзывы не получены")
                return False, []
                
    except Exception as e:
        print(f"❌ Ошибка парсинга отзывов: {e}")
        return False, []

async def test_full_parsing():
    """Тест полного парсинга"""
    print("\n🔍 ТЕСТ ПОЛНОГО ПАРСИНГА")
    print("-" * 50)
    
    try:
        result = await parse_ozon_flaresolverr_full(TEST_PRODUCT_URL, PROXY_CONFIG)
        
        print("✅ Полный парсинг выполнен!")
        print(f"🆔 ID товара: {result['product_id']}")
        print(f"🌐 URL: {result['url']}")
        print(f"⏰ Время парсинга: {result['parsed_at']}")
        
        if result['price_info']:
            price = result['price_info']
            print(f"💰 Цена: {price['current_price']} {price['currency']}")
            if price.get('original_price'):
                print(f"💸 Старая цена: {price['original_price']} {price['currency']}")
                print(f"🎯 Скидка: {price['discount_percent']}%")
        
        print(f"📝 Отзывов: {result['reviews_count']}")
        if result['average_rating']:
            print(f"⭐ Средний рейтинг: {result['average_rating']}/5")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Ошибка полного парсинга: {e}")
        return False, None

async def test_bulk_parsing():
    """Тест массового парсинга"""
    print("\n🚀 ТЕСТ МАССОВОГО ПАРСИНГА")
    print("-" * 50)
    
    # Список товаров для тестирования
    test_urls = [
        TEST_PRODUCT_URL,
        # Можно добавить еще URL для тестирования
    ]
    
    try:
        async with OzonFlareSolverrParser(PROXY_CONFIG) as parser:
            results = await parser.parse_products_bulk(test_urls)
            
            print(f"✅ Массовый парсинг завершен: {len(results)} результатов")
            
            for i, result in enumerate(results, 1):
                print(f"\n📦 Товар {i}:")
                if 'error' in result:
                    print(f"   ❌ Ошибка: {result['error']}")
                else:
                    print(f"   ✅ Успешно обработан")
                    if result.get('price_info'):
                        print(f"   💰 Цена: {result['price_info']['current_price']} RUB")
                    print(f"   📝 Отзывов: {result['reviews_count']}")
            
            return True, results
            
    except Exception as e:
        print(f"❌ Ошибка массового парсинга: {e}")
        return False, []

async def main():
    """Основная функция тестирования"""
    print("🧪 ТЕСТИРОВАНИЕ OZON FLARESOLVERR ПАРСЕРА")
    print("=" * 60)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print(f"📦 URL: {TEST_PRODUCT_URL}")
    print("=" * 60)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'connection_test': False,
        'price_test': False,
        'reviews_test': False,
        'full_test': False,
        'bulk_test': False,
        'price_data': None,
        'reviews_data': None,
        'full_data': None,
        'bulk_data': None
    }
    
    # Тест 1: Подключение к FlareSolverr
    results['connection_test'] = await test_flaresolverr_connection()
    
    if not results['connection_test']:
        print("\n❌ FlareSolverr недоступен! Запустите:")
        print("docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest")
        return
    
    # Тест 2: Парсинг цены
    price_success, price_data = await test_price_parsing()
    results['price_test'] = price_success
    results['price_data'] = price_data
    
    # Тест 3: Парсинг отзывов
    reviews_success, reviews_data = await test_reviews_parsing()
    results['reviews_test'] = reviews_success
    results['reviews_data'] = reviews_data
    
    # Тест 4: Полный парсинг
    full_success, full_data = await test_full_parsing()
    results['full_test'] = full_success
    results['full_data'] = full_data
    
    # Тест 5: Массовый парсинг
    bulk_success, bulk_data = await test_bulk_parsing()
    results['bulk_test'] = bulk_success
    results['bulk_data'] = bulk_data
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    tests = [
        ("Подключение к FlareSolverr", results['connection_test']),
        ("Парсинг цены", results['price_test']),
        ("Парсинг отзывов", results['reviews_test']),
        ("Полный парсинг", results['full_test']),
        ("Массовый парсинг", results['bulk_test'])
    ]
    
    success_count = 0
    for test_name, success in tests:
        status = "✅ УСПЕШНО" if success else "❌ НЕУДАЧНО"
        print(f"{test_name}: {status}")
        if success:
            success_count += 1
    
    print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ: {success_count}/{len(tests)} тестов пройдено")
    
    if success_count == len(tests):
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("💡 FlareSolverr парсер работает стабильно!")
    elif success_count > 0:
        print("⚠️ ЧАСТИЧНЫЙ УСПЕХ!")
        print("💡 Некоторые функции работают, но есть проблемы")
    else:
        print("❌ ВСЕ ТЕСТЫ ПРОВАЛЕНЫ!")
        print("💡 Проверьте настройки FlareSolverr и прокси")
    
    # Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"flaresolverr_parser_test_result_{timestamp}.json"
    
    # Очищаем данные от больших объектов для сохранения
    save_results = results.copy()
    if save_results.get('full_data'):
        save_results['full_data'] = {
            'url': save_results['full_data']['url'],
            'product_id': save_results['full_data']['product_id'],
            'price_info': save_results['full_data']['price_info'],
            'reviews_count': save_results['full_data']['reviews_count'],
            'average_rating': save_results['full_data']['average_rating'],
            'parsed_at': save_results['full_data']['parsed_at']
        }
    
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(save_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в: {result_file}")
    
    # Показываем пример использования
    if results['full_test']:
        print("\n" + "=" * 60)
        print("💡 ПРИМЕР ИСПОЛЬЗОВАНИЯ")
        print("=" * 60)
        print("""
# Быстрый парсинг цены
from utils.ozon_flaresolverr_parser import parse_ozon_flaresolverr_price

price = await parse_ozon_flaresolverr_price(product_url, proxy_config)

# Быстрый парсинг отзывов
from utils.ozon_flaresolverr_parser import parse_ozon_flaresolverr_reviews

reviews = await parse_ozon_flaresolverr_reviews(product_url, proxy_config)

# Полный парсинг
from utils.ozon_flaresolverr_parser import parse_ozon_flaresolverr_full

result = await parse_ozon_flaresolverr_full(product_url, proxy_config)
        """)

if __name__ == "__main__":
    asyncio.run(main())
