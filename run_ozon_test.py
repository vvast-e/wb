#!/usr/bin/env python3
"""
Быстрый запуск тестов Ozon парсера
"""

import asyncio
import sys
import os

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    try:
        import curl_cffi
        print("✅ curl_cffi установлен")
    except ImportError:
        print("❌ curl_cffi НЕ УСТАНОВЛЕН!")
        print("💡 Установите: pip install curl-cffi")
        return False
    
    try:
        import httpx
        print("✅ httpx установлен")
    except ImportError:
        print("❌ httpx НЕ УСТАНОВЛЕН!")
        print("💡 Установите: pip install httpx")
        return False
    
    # Проверяем наличие файлов парсера
    parser_file = "utils/ozon_mobile_stealth_parser.py"
    if os.path.exists(parser_file):
        print("✅ Файл парсера найден")
    else:
        print(f"❌ Файл парсера НЕ НАЙДЕН: {parser_file}")
        return False
    
    return True

async def main():
    """Основная функция"""
    print("🚀 ЗАПУСК ТЕСТОВ OZON ПАРСЕРА")
    print("=" * 50)
    
    # Проверяем зависимости
    if not check_dependencies():
        print("\n❌ Не все зависимости установлены!")
        print("💡 Установите недостающие пакеты и попробуйте снова")
        return
    
    print("\n📋 Доступные тесты:")
    print("1. Полный тест парсера (рекомендуется)")
    print("2. Тест дампа страницы")
    print("3. Быстрый тест")
    print("4. HTML парсер (обход 403)")
    print("5. Проверка IP прокси")
    print("6. FlareSolverr + Selenium (обход антибота)")
    print("7. Все тесты")
    
    choice = input("\nВыберите тест (1-7): ").strip()
    
    if choice == "1":
        print("\n🧪 Запуск полного теста парсера...")
        from test_new_ozon_parser import main as test_main
        await test_main()
        
    elif choice == "2":
        print("\n🌐 Запуск теста дампа страницы...")
        from test_page_dump import main as dump_main
        await dump_main()
        
    elif choice == "3":
        print("\n⚡ Запуск быстрого теста...")
        from test_new_ozon_parser import quick_test
        await quick_test()
        
    elif choice == "4":
        print("\n🌐 Запуск HTML парсера...")
        from test_html_parser import main as html_main
        await html_main()
        
    elif choice == "5":
        print("\n🌐 Запуск проверки IP прокси...")
        from test_proxy_ip import main as ip_main
        await ip_main()
        
    elif choice == "6":
        print("\n🔥 Запуск FlareSolverr + Selenium теста...")
        from test_flaresolverr import main as flaresolverr_main
        await flaresolverr_main()
        
    elif choice == "7":
        print("\n🔄 Запуск всех тестов...")
        
        print("\n1️⃣ Полный тест парсера:")
        from test_new_ozon_parser import main as test_main
        await test_main()
        
        print("\n2️⃣ Тест дампа страницы:")
        from test_page_dump import main as dump_main
        await dump_main()
        
        print("\n3️⃣ HTML парсер:")
        from test_html_parser import main as html_main
        await html_main()
        
        print("\n4️⃣ Проверка IP прокси:")
        from test_proxy_ip import main as ip_main
        await ip_main()
        
        print("\n5️⃣ FlareSolverr + Selenium:")
        from test_flaresolverr import main as flaresolverr_main
        await flaresolverr_main()
        
    else:
        print("❌ Неверный выбор!")
        return
    
    print("\n🏁 Тестирование завершено!")
    print("💡 Проверьте созданные файлы с результатами")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
