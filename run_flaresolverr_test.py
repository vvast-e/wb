#!/usr/bin/env python3
"""
🚀 ЗАПУСК ТЕСТА FLARESOLVERR ПАРСЕРА 🚀

Простой скрипт для запуска тестирования нового парсера
"""

import asyncio
import sys
import os

def check_dependencies():
    """Проверка зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    missing_deps = []
    
    try:
        import requests
        print("✅ requests установлен")
    except ImportError:
        missing_deps.append("requests")
    
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup установлен")
    except ImportError:
        missing_deps.append("beautifulsoup4")
    
    if missing_deps:
        print(f"❌ Отсутствуют зависимости: {', '.join(missing_deps)}")
        print("💡 Установите: pip install " + " ".join(missing_deps))
        return False
    
    return True

def check_flaresolverr():
    """Проверка доступности FlareSolverr"""
    print("\n🔥 Проверка FlareSolverr...")
    
    try:
        import requests
        response = requests.get("http://localhost:8191/v1", timeout=5)
        print("✅ FlareSolverr доступен")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ FlareSolverr не запущен!")
        print("💡 Запустите FlareSolverr:")
        print("   docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest")
        return False
    except Exception as e:
        print(f"⚠️ Ошибка проверки FlareSolverr: {e}")
        return False

async def main():
    """Основная функция"""
    print("🚀 ЗАПУСК ТЕСТА OZON FLARESOLVERR ПАРСЕРА")
    print("=" * 50)
    
    # Проверяем зависимости
    if not check_dependencies():
        sys.exit(1)
    
    # Проверяем FlareSolverr
    if not check_flaresolverr():
        print("\n❌ FlareSolverr недоступен!")
        print("💡 Запустите FlareSolverr и попробуйте снова")
        sys.exit(1)
    
    # Запускаем тест
    print("\n🧪 Запуск тестирования...")
    try:
        from test_ozon_flaresolverr_parser import main as test_main
        await test_main()
    except Exception as e:
        print(f"❌ Ошибка запуска теста: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
