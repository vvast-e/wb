#!/usr/bin/env python3
"""
Тест HTML парсера Ozon - обход 403 через парсинг HTML страниц
"""

import asyncio
import json
from datetime import datetime

# Настройки прокси
PROXY_CONFIG = {
    'scheme': 'http',
    'host': 'p15184.ltespace.net',
    'port': 15184,
    'username': 'uek7t66y',
    'password': 'zbygddap'
}

# URL товара
TEST_PRODUCT_URL = "https://www.ozon.ru/product/termozashchitnyy-sprey-dlya-volos-uvlazhnyayushchiy-nesmyvaemyy-uhod-dlya-legkogo-2128381166/?__rr=3&at=EqtkV5nBRhyWXGM9iY1OEWVhDKJLXvsrZVAMkFZK70J2"

async def test_html_parser():
    """Тестирует HTML парсер"""
    print("🌐 ТЕСТ HTML ПАРСЕРА OZON")
    print("=" * 50)
    print(f"📦 URL: {TEST_PRODUCT_URL}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print("=" * 50)
    
    try:
        from utils.ozon_html_parser import OzonHTMLParser
        
        print("✅ HTML парсер импортирован")
        
        async with OzonHTMLParser(PROXY_CONFIG) as parser:
            print("✅ HTML парсер инициализирован")
            
            # Тест 1: Получение HTML страницы
            print("\n📄 ТЕСТ 1: Получение HTML страницы")
            print("-" * 40)
            
            html = await parser.get_product_page(TEST_PRODUCT_URL)
            
            if html:
                print("✅ HTML страница получена успешно!")
                print(f"📏 Размер: {len(html)} символов")
                
                # Сохраняем HTML для анализа
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = f"ozon_html_page_{timestamp}.html"
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"💾 HTML сохранен в: {html_file}")
                
                # Анализируем содержимое
                if "отзыв" in html.lower() or "review" in html.lower():
                    print("✅ Найдены упоминания отзывов в HTML")
                else:
                    print("⚠️ Отзывы в HTML не найдены")
                
                if "цена" in html.lower() or "price" in html.lower() or "₽" in html:
                    print("✅ Найдены упоминания цен в HTML")
                else:
                    print("⚠️ Цены в HTML не найдены")
                
                html_success = True
            else:
                print("❌ HTML страница не получена")
                html_success = False
            
            # Тест 2: Парсинг цены
            print("\n💰 ТЕСТ 2: Парсинг цены из HTML")
            print("-" * 40)
            
            price_info = await parser.get_product_price(TEST_PRODUCT_URL)
            
            if price_info and price_info.get('current_price'):
                print("✅ ЦЕНА ИЗВЛЕЧЕНА ИЗ HTML!")
                print(f"   💰 Текущая цена: {price_info['current_price']} {price_info.get('currency', 'RUB')}")
                
                if price_info.get('original_price'):
                    print(f"   💸 Старая цена: {price_info['original_price']} {price_info.get('currency', 'RUB')}")
                
                if price_info.get('discount_percent'):
                    print(f"   🎯 Скидка: {price_info['discount_percent']}%")
                
                price_success = True
            else:
                print("❌ ЦЕНА НЕ ИЗВЛЕЧЕНА")
                print(f"   Ответ: {price_info}")
                price_success = False
            
            # Тест 3: Парсинг отзывов
            print("\n📝 ТЕСТ 3: Парсинг отзывов из HTML")
            print("-" * 40)
            
            reviews = await parser.get_product_reviews(TEST_PRODUCT_URL)
            
            if reviews and len(reviews) > 0:
                print(f"✅ ОТЗЫВЫ ИЗВЛЕЧЕНЫ ИЗ HTML!")
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
                print("❌ ОТЗЫВЫ НЕ ИЗВЛЕЧЕНЫ")
                print(f"   Ответ: {reviews}")
                reviews_success = False
            
            # Тест 4: Полный анализ
            print("\n🔍 ТЕСТ 4: Полный анализ товара")
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
            result_file = f"ozon_html_result_{timestamp}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(full_result, f, ensure_ascii=False, indent=2)
            print(f"✅ Полный результат сохранен в: {result_file}")
            
            # Сохраняем только отзывы
            if reviews:
                reviews_file = f"ozon_html_reviews_{timestamp}.json"
                with open(reviews_file, "w", encoding="utf-8") as f:
                    json.dump(reviews, f, ensure_ascii=False, indent=2)
                print(f"✅ Отзывы сохранены в: {reviews_file}")
            
            # Итоговый отчет
            print("\n" + "=" * 50)
            print("📊 ИТОГОВЫЙ ОТЧЕТ HTML ПАРСЕРА")
            print("=" * 50)
            
            print(f"✅ Получение HTML: {'УСПЕШНО' if html_success else 'НЕУДАЧНО'}")
            print(f"✅ Парсинг цены: {'УСПЕШНО' if price_success else 'НЕУДАЧНО'}")
            print(f"✅ Парсинг отзывов: {'УСПЕШНО' if reviews_success else 'НЕУДАЧНО'}")
            print(f"✅ Полный анализ: {'УСПЕШНО' if full_success else 'НЕУДАЧНО'}")
            
            success_count = sum([html_success, price_success, reviews_success, full_success])
            total_tests = 4
            
            print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ: {success_count}/{total_tests} тестов пройдено")
            
            if success_count == total_tests:
                print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! HTML парсер работает отлично!")
                print("✅ 403 антибот успешно обойден через HTML парсинг!")
            elif success_count > 2:
                print("✅ ХОРОШИЙ РЕЗУЛЬТАТ! HTML парсер работает!")
                print("💡 Большинство функций работают корректно")
            elif success_count > 0:
                print("⚠️ ЧАСТИЧНЫЙ УСПЕХ! Некоторые функции работают")
                print("💡 HTML получен, но парсинг требует доработки")
            else:
                print("❌ ВСЕ ТЕСТЫ ПРОВАЛЕНЫ! HTML парсер не работает")
                print("💡 Рекомендации:")
                print("   - Проверьте подключение к прокси")
                print("   - Убедитесь что товар доступен")
                print("   - Проверьте HTML структуру страницы")
            
            return {
                'html_success': html_success,
                'price_success': price_success,
                'reviews_success': reviews_success,
                'full_success': full_success,
                'total_success': success_count,
                'result': full_result
            }
            
    except ImportError as e:
        print(f"❌ ОШИБКА ИМПОРТА: {e}")
        print("💡 Убедитесь что файл utils/ozon_html_parser.py существует")
        return None
        
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        print("\n🔍 ДЕТАЛИ ОШИБКИ:")
        traceback.print_exc()
        return None

async def main():
    """Основная функция"""
    print("🧪 ТЕСТИРОВАНИЕ HTML ПАРСЕРА OZON")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Проверяем зависимости
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup установлен")
    except ImportError:
        print("❌ BeautifulSoup НЕ УСТАНОВЛЕН!")
        print("💡 Установите: pip install beautifulsoup4")
        return
    
    # Запускаем тест
    result = await test_html_parser()
    
    if result:
        print(f"\n🏁 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print(f"📊 Успешность: {result['total_success']}/4")
        
        if result['total_success'] >= 3:
            print("\n🎉 HTML ПАРСЕР РАБОТАЕТ!")
            print("💡 Этот подход обходит 403 антибот!")
        else:
            print("\n⚠️ HTML парсер требует доработки")
    else:
        print(f"\n❌ ТЕСТИРОВАНИЕ ПРОВАЛЕНО")

if __name__ == "__main__":
    asyncio.run(main())
