#!/usr/bin/env python3
"""
Простой тест для получения дампа страницы Ozon
Проверяет обход защиты и сохраняет HTML для анализа
"""

import asyncio
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

# URL товара
TEST_PRODUCT_URL = "https://www.ozon.ru/product/termozashchitnyy-sprey-dlya-volos-uvlazhnyayushchiy-nesmyvaemyy-uhod-dlya-legkogo-2128381166/?__rr=3&at=EqtkV5nBRhyWXGM9iY1OEWVhDKJLXvsrZVAMkFZK70J2"

async def test_page_dump():
    """Тестирует получение дампа страницы"""
    print("🌐 ТЕСТ ПОЛУЧЕНИЯ ДАМПА СТРАНИЦЫ OZON")
    print("=" * 50)
    print(f"📦 URL: {TEST_PRODUCT_URL}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print("=" * 50)
    
    try:
        # Импортируем наш парсер
        from utils.ozon_mobile_stealth_parser import OzonMobileStealthParser
        
        print("✅ Парсер импортирован")
        
        # Создаем парсер
        async with OzonMobileStealthParser(PROXY_CONFIG) as parser:
            print("✅ Парсер инициализирован")
            print("🔥 Прогрев сессии выполнен")
            
            # Получаем дамп страницы через внутренние методы парсера
            print("\n📄 Получение дампа страницы...")
            
            # Используем внутренний метод для получения HTML
            response = await parser._safe_request('GET', TEST_PRODUCT_URL)
            
            if response and response.status_code == 200:
                print("✅ СТРАНИЦА ПОЛУЧЕНА УСПЕШНО!")
                print(f"📊 Статус: {response.status_code}")
                print(f"📏 Размер: {len(response.text)} символов")
                
                # Сохраняем дамп
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dump_file = f"ozon_page_dump_{timestamp}.html"
                
                with open(dump_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                print(f"💾 Дамп сохранен в: {dump_file}")
                
                # Анализируем содержимое
                content = response.text
                
                print("\n🔍 АНАЛИЗ СОДЕРЖИМОГО:")
                print("-" * 30)
                
                # Проверяем наличие ключевых элементов
                checks = [
                    ("отзыв", "отзыв" in content.lower()),
                    ("review", "review" in content.lower()),
                    ("цена", "цена" in content.lower()),
                    ("price", "price" in content.lower()),
                    ("₽", "₽" in content),
                    ("руб", "руб" in content.lower()),
                    ("рейтинг", "рейтинг" in content.lower()),
                    ("rating", "rating" in content.lower()),
                    ("товар", "товар" in content.lower()),
                    ("product", "product" in content.lower()),
                ]
                
                for check_name, found in checks:
                    status = "✅" if found else "❌"
                    print(f"   {status} {check_name}: {'найден' if found else 'не найден'}")
                
                # Проверяем на блокировку
                if "captcha" in content.lower() or "blocked" in content.lower():
                    print("\n⚠️ ВОЗМОЖНАЯ БЛОКИРОВКА ОБНАРУЖЕНА!")
                elif "403" in content or "forbidden" in content.lower():
                    print("\n❌ 403 FORBIDDEN ОБНАРУЖЕН!")
                else:
                    print("\n✅ БЛОКИРОВКА НЕ ОБНАРУЖЕНА!")
                
                # Проверяем наличие JSON данных
                if '"reviews"' in content or '"price"' in content:
                    print("✅ JSON данные найдены в HTML")
                else:
                    print("⚠️ JSON данные не найдены в HTML")
                
                return True
                
            elif response:
                print(f"❌ ОШИБКА: Статус {response.status_code}")
                print(f"📄 Ответ: {response.text[:500]}...")
                return False
            else:
                print("❌ НЕТ ОТВЕТА ОТ СЕРВЕРА")
                return False
                
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_with_curl_cffi():
    """Тест с прямым использованием curl_cffi"""
    print("\n🔧 ТЕСТ С ПРЯМЫМ CURL_CFFI")
    print("-" * 40)
    
    try:
        from curl_cffi import requests as curl_requests
        
        # Настройка прокси
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        
        # Мобильные заголовки
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Создаем сессию
        session = curl_requests.Session(
            impersonate="chrome120_android",
            headers=headers,
            proxies={'http': proxy_url, 'https': proxy_url},
            timeout=30
        )
        
        print("✅ curl_cffi сессия создана")
        
        # Делаем запрос
        response = session.get(TEST_PRODUCT_URL)
        
        print(f"📊 Статус: {response.status_code}")
        print(f"📏 Размер: {len(response.text)} символов")
        
        if response.status_code == 200:
            print("✅ УСПЕШНО! Страница получена через curl_cffi")
            
            # Сохраняем дамп
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = f"ozon_curl_dump_{timestamp}.html"
            
            with open(dump_file, "w", encoding="utf-8") as f:
                f.write(response.text)
            
            print(f"💾 Дамп сохранен в: {dump_file}")
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка curl_cffi: {e}")
        return False

async def main():
    """Основная функция"""
    print("🧪 ТЕСТИРОВАНИЕ ДАМПА СТРАНИЦЫ OZON")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Тест 1: Через наш парсер
    success1 = await test_page_dump()
    
    # Тест 2: Через прямой curl_cffi
    success2 = await test_with_curl_cffi()
    
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(f"✅ Наш парсер: {'УСПЕШНО' if success1 else 'НЕУДАЧНО'}")
    print(f"✅ curl_cffi: {'УСПЕШНО' if success2 else 'НЕУДАЧНО'}")
    
    if success1 or success2:
        print("\n🎉 ЗАЩИТА ОБОЙДЕНА!")
        print("💡 Проверьте сохраненные HTML файлы для анализа")
    else:
        print("\n❌ ЗАЩИТА НЕ ОБОЙДЕНА")
        print("💡 Рекомендации:")
        print("   - Проверьте настройки прокси")
        print("   - Убедитесь что прокси резидентный мобильный")
        print("   - Попробуйте другой IP адрес")

if __name__ == "__main__":
    asyncio.run(main())
