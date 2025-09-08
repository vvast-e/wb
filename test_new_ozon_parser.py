#!/usr/bin/env python3
"""
Тестовый файл для проверки работы нового Ozon Mobile Stealth Parser
Использует реальные настройки прокси и товар для тестирования
"""

import asyncio
import json
import os
from datetime import datetime

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

async def test_new_parser():
    """Тестирует новый Ozon Mobile Stealth Parser"""
    print("🚀 ТЕСТИРОВАНИЕ НОВОГО OZON MOBILE STEALTH PARSER")
    print("=" * 60)
    print(f"📦 Товар: {TEST_PRODUCT_URL}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print("=" * 60)
    
    try:
        # Импортируем наш новый парсер
        from utils.ozon_mobile_stealth_parser import OzonMobileStealthParser
        
        print("✅ Парсер импортирован успешно")
        
        # Создаем экземпляр парсера
        async with OzonMobileStealthParser(PROXY_CONFIG) as parser:
            print("✅ Парсер инициализирован успешно")
            print("🔥 Прогрев сессии выполнен")
            
            # Тест 1: Получение цены
            print("\n💰 ТЕСТ 1: Получение цены товара")
            print("-" * 40)
            
            price_info = await parser.get_product_price(TEST_PRODUCT_URL)
            
            if price_info and price_info.get('current_price'):
                print("✅ ЦЕНА ПОЛУЧЕНА УСПЕШНО!")
                print(f"   💰 Текущая цена: {price_info['current_price']} {price_info.get('currency', 'RUB')}")
                
                if price_info.get('original_price'):
                    print(f"   💸 Старая цена: {price_info['original_price']} {price_info.get('currency', 'RUB')}")
                
                if price_info.get('discount_percent'):
                    print(f"   🎯 Скидка: {price_info['discount_percent']}%")
                
                price_success = True
            else:
                print("❌ ЦЕНА НЕ ПОЛУЧЕНА")
                print(f"   Ответ: {price_info}")
                price_success = False
            
            # Тест 2: Получение отзывов
            print("\n📝 ТЕСТ 2: Получение отзывов товара")
            print("-" * 40)
            
            reviews = await parser.get_product_reviews(TEST_PRODUCT_URL, max_pages=2)
            
            if reviews and len(reviews) > 0:
                print(f"✅ ОТЗЫВЫ ПОЛУЧЕНЫ УСПЕШНО!")
                print(f"   📊 Количество отзывов: {len(reviews)}")
                
                # Показываем первые 3 отзыва
                print("\n   📄 ПРИМЕРЫ ОТЗЫВОВ:")
                for i, review in enumerate(reviews[:3], 1):
                    print(f"\n   Отзыв {i}:")
                    print(f"     👤 Автор: {review.get('author', 'N/A')}")
                    print(f"     ⭐ Рейтинг: {review.get('rating', 'N/A')}/5")
                    print(f"     📝 Текст: {review.get('text', 'N/A')[:80]}...")
                    
                    if review.get('pros'):
                        print(f"     ✅ Плюсы: {review.get('pros', 'N/A')[:50]}...")
                    
                    if review.get('cons'):
                        print(f"     ❌ Минусы: {review.get('cons', 'N/A')[:50]}...")
                
                # Статистика по рейтингам
                ratings = [r['rating'] for r in reviews if r.get('rating')]
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    print(f"\n   📊 СТАТИСТИКА:")
                    print(f"     ⭐ Средний рейтинг: {avg_rating:.2f}/5")
                    print(f"     📈 Всего оценок: {len(ratings)}")
                
                reviews_success = True
            else:
                print("❌ ОТЗЫВЫ НЕ ПОЛУЧЕНЫ")
                print(f"   Ответ: {reviews}")
                reviews_success = False
            
            # Тест 3: Полный анализ товара
            print("\n🔍 ТЕСТ 3: Полный анализ товара")
            print("-" * 40)
            
            full_result = await parser.get_product_full_info(TEST_PRODUCT_URL)
            
            if full_result:
                print("✅ ПОЛНЫЙ АНАЛИЗ ВЫПОЛНЕН!")
                print(f"   🆔 ID товара: {full_result.get('product_id', 'N/A')}")
                print(f"   🌐 URL: {full_result.get('url', 'N/A')}")
                print(f"   ⏰ Время парсинга: {full_result.get('parsed_at', 'N/A')}")
                
                if full_result.get('price_info'):
                    price = full_result['price_info']
                    print(f"   💰 Цена: {price.get('current_price', 'N/A')} {price.get('currency', 'RUB')}")
                
                if full_result.get('reviews_count', 0) > 0:
                    print(f"   📝 Отзывов: {full_result['reviews_count']}")
                    print(f"   ⭐ Средний рейтинг: {full_result.get('average_rating', 'N/A')}/5")
                
                full_success = True
            else:
                print("❌ ПОЛНЫЙ АНАЛИЗ НЕ ВЫПОЛНЕН")
                full_success = False
            
            # Сохраняем результаты
            print("\n💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
            print("-" * 40)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Сохраняем полный результат
            result_file = f"ozon_test_result_{timestamp}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)
            print(f"✅ Полный результат сохранен в: {result_file}")
            
            # Сохраняем только отзывы
            if reviews:
                reviews_file = f"ozon_reviews_{timestamp}.json"
                with open(reviews_file, "w", encoding="utf-8") as f:
                    json.dump(reviews, f, ensure_ascii=False, indent=2)
                print(f"✅ Отзывы сохранены в: {reviews_file}")
            
            # Итоговый отчет
            print("\n" + "=" * 60)
            print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
            print("=" * 60)
            
            print(f"✅ Получение цены: {'УСПЕШНО' if price_success else 'НЕУДАЧНО'}")
            print(f"✅ Получение отзывов: {'УСПЕШНО' if reviews_success else 'НЕУДАЧНО'}")
            print(f"✅ Полный анализ: {'УСПЕШНО' if full_success else 'НЕУДАЧНО'}")
            
            success_count = sum([price_success, reviews_success, full_success])
            total_tests = 3
            
            print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ: {success_count}/{total_tests} тестов пройдено")
            
            if success_count == total_tests:
                print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Парсер работает отлично!")
                print("✅ Антибот успешно обойден!")
            elif success_count > 0:
                print("⚠️ ЧАСТИЧНЫЙ УСПЕХ! Некоторые функции работают")
                print("💡 Рекомендуется проверить настройки прокси")
            else:
                print("❌ ВСЕ ТЕСТЫ ПРОВАЛЕНЫ! Парсер не работает")
                print("💡 Рекомендации:")
                print("   - Проверьте подключение к прокси")
                print("   - Убедитесь что прокси резидентный мобильный")
                print("   - Проверьте URL товара")
                print("   - Попробуйте другой IP адрес")
            
            return {
                'price_success': price_success,
                'reviews_success': reviews_success,
                'full_success': full_success,
                'total_success': success_count,
                'result': full_result
            }
            
    except ImportError as e:
        print(f"❌ ОШИБКА ИМПОРТА: {e}")
        print("💡 Убедитесь что файл utils/ozon_mobile_stealth_parser.py существует")
        return None
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print("\n🔍 ДЕТАЛИ ОШИБКИ:")
        traceback.print_exc()
        return None

async def quick_test():
    """Быстрый тест для проверки базовой функциональности"""
    print("⚡ БЫСТРЫЙ ТЕСТ ПАРСЕРА")
    print("-" * 30)
    
    try:
        from utils.ozon_mobile_stealth_parser import parse_ozon_product_price, parse_ozon_product_reviews
        
        # Быстрый тест цены
        print("💰 Тест получения цены...")
        price = await parse_ozon_product_price(TEST_PRODUCT_URL, PROXY_CONFIG)
        
        if price and price.get('current_price'):
            print(f"✅ Цена: {price['current_price']} руб.")
        else:
            print("❌ Цена не получена")
        
        # Быстрый тест отзывов
        print("📝 Тест получения отзывов...")
        reviews = await parse_ozon_product_reviews(TEST_PRODUCT_URL, PROXY_CONFIG, max_pages=1)
        
        if reviews:
            print(f"✅ Отзывов: {len(reviews)}")
            if reviews:
                print(f"   Первый отзыв: {reviews[0].get('author', 'N/A')} - {reviews[0].get('rating', 'N/A')}/5")
        else:
            print("❌ Отзывы не получены")
            
    except Exception as e:
        print(f"❌ Ошибка быстрого теста: {e}")

async def main():
    """Основная функция"""
    print("🧪 ТЕСТИРОВАНИЕ НОВОГО OZON ПАРСЕРА")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем наличие curl_cffi
    try:
        import curl_cffi
        print("✅ curl_cffi установлен")
    except ImportError:
        print("❌ curl_cffi НЕ УСТАНОВЛЕН!")
        print("💡 Установите: pip install curl-cffi")
        return
    
    # Запускаем быстрый тест
    await quick_test()
    
    print("\n" + "=" * 60)
    
    # Запускаем полный тест
    result = await test_new_parser()
    
    if result:
        print(f"\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"📊 Успешность: {result['total_success']}/3")
    else:
        print(f"\n❌ ТЕСТИРОВАНИЕ ПРОВАЛЕНО")

if __name__ == "__main__":
    asyncio.run(main())
