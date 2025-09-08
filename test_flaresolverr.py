#!/usr/bin/env python3
"""
Тест FlareSolverr для обхода антибота Ozon
"""

import asyncio
import json
import requests
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

# FlareSolverr настройки
FLARESOLVERR_URL = "http://localhost:8191/v1"  # Стандартный URL FlareSolverr

async def test_flaresolverr_without_proxy():
    """Тест FlareSolverr без прокси"""
    print("🔥 ТЕСТ FLARESOLVERR БЕЗ ПРОКСИ")
    print("-" * 40)
    
    try:
        payload = {
            "cmd": "request.get",
            "url": TEST_PRODUCT_URL,
            "maxTimeout": 60000,
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.post(FLARESOLVERR_URL, json=payload, timeout=70)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'ok':
                solution = result.get('solution', {})
                status_code = solution.get('status', 0)
                html = solution.get('response', '')
                
                print(f"✅ FlareSolverr статус: {status_code}")
                print(f"📏 Размер HTML: {len(html)} символов")
                
                if status_code == 200:
                    if "ozon" in html.lower() and "product" in html.lower():
                        print("✅ Ozon страница получена через FlareSolverr!")
                        
                        # Сохраняем HTML
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        html_file = f"ozon_flaresolverr_no_proxy_{timestamp}.html"
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"💾 HTML сохранен в: {html_file}")
                        
                        return True, html
                    else:
                        print("⚠️ HTML получен, но не похож на Ozon")
                        return False, html
                else:
                    print(f"❌ HTTP ошибка: {status_code}")
                    return False, html
            else:
                print(f"❌ FlareSolverr ошибка: {result.get('message', 'Unknown error')}")
                return False, None
        else:
            print(f"❌ FlareSolverr сервер ошибка: {response.status_code}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("❌ FlareSolverr не запущен!")
        print("💡 Запустите FlareSolverr: docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest")
        return False, None
    except Exception as e:
        print(f"❌ Ошибка FlareSolverr: {e}")
        return False, None

async def test_flaresolverr_with_proxy():
    """Тест FlareSolverr с прокси"""
    print("\n🔥 ТЕСТ FLARESOLVERR С ПРОКСИ")
    print("-" * 40)
    
    try:
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        
        payload = {
            "cmd": "request.get",
            "url": TEST_PRODUCT_URL,
            "maxTimeout": 60000,
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "proxy": {
                "url": proxy_url
            }
        }
        
        response = requests.post(FLARESOLVERR_URL, json=payload, timeout=70)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'ok':
                solution = result.get('solution', {})
                status_code = solution.get('status', 0)
                html = solution.get('response', '')
                
                print(f"✅ FlareSolverr с прокси статус: {status_code}")
                print(f"📏 Размер HTML: {len(html)} символов")
                
                if status_code == 200:
                    if "ozon" in html.lower() and "product" in html.lower():
                        print("✅ Ozon страница получена через FlareSolverr с прокси!")
                        
                        # Сохраняем HTML
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        html_file = f"ozon_flaresolverr_with_proxy_{timestamp}.html"
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"💾 HTML сохранен в: {html_file}")
                        
                        return True, html
                    else:
                        print("⚠️ HTML получен, но не похож на Ozon")
                        return False, html
                else:
                    print(f"❌ HTTP ошибка: {status_code}")
                    return False, html
            else:
                print(f"❌ FlareSolverr ошибка: {result.get('message', 'Unknown error')}")
                return False, None
        else:
            print(f"❌ FlareSolverr сервер ошибка: {response.status_code}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print("❌ FlareSolverr не запущен!")
        return False, None
    except Exception as e:
        print(f"❌ Ошибка FlareSolverr: {e}")
        return False, None

async def test_selenium_undetected():
    """Тест Selenium с undetected-chromedriver"""
    print("\n🤖 ТЕСТ SELENIUM UNDETECTED-CHROMEDRIVER")
    print("-" * 40)
    
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException
        
        # Настройки Chrome
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Добавляем прокси если нужно
        proxy_url = f"{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        options.add_argument(f'--proxy-server=http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{proxy_url}')
        
        print("🚀 Запуск Chrome...")
        driver = uc.Chrome(options=options)
        
        try:
            print(f"🌐 Переход на: {TEST_PRODUCT_URL}")
            driver.get(TEST_PRODUCT_URL)
            
            # Ждем загрузки страницы
            wait = WebDriverWait(driver, 30)
            
            try:
                # Ждем появления элемента страницы
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                print("✅ Страница загружена!")
                
                # Получаем HTML
                html = driver.page_source
                print(f"📏 Размер HTML: {len(html)} символов")
                
                if "ozon" in html.lower() and "product" in html.lower():
                    print("✅ Ozon страница получена через Selenium!")
                    
                    # Сохраняем HTML
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    html_file = f"ozon_selenium_uc_{timestamp}.html"
                    with open(html_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"💾 HTML сохранен в: {html_file}")
                    
                    return True, html
                else:
                    print("⚠️ HTML получен, но не похож на Ozon")
                    return False, html
                    
            except TimeoutException:
                print("❌ Таймаут загрузки страницы")
                return False, None
                
        finally:
            driver.quit()
            
    except ImportError:
        print("❌ undetected-chromedriver не установлен!")
        print("💡 Установите: pip install undetected-chromedriver")
        return False, None
    except Exception as e:
        print(f"❌ Ошибка Selenium: {e}")
        return False, None

async def main():
    """Основная функция"""
    print("🔥 ТЕСТ FLARESOLVERR И SELENIUM ДЛЯ OZON")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print(f"📦 URL: {TEST_PRODUCT_URL}")
    print("=" * 50)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'flaresolverr_no_proxy': False,
        'flaresolverr_with_proxy': False,
        'selenium_uc': False,
        'html_files': []
    }
    
    # Тест 1: FlareSolverr без прокси
    success, html = await test_flaresolverr_without_proxy()
    results['flaresolverr_no_proxy'] = success
    if html:
        results['html_files'].append('flaresolverr_no_proxy')
    
    # Тест 2: FlareSolverr с прокси
    success, html = await test_flaresolverr_with_proxy()
    results['flaresolverr_with_proxy'] = success
    if html:
        results['html_files'].append('flaresolverr_with_proxy')
    
    # Тест 3: Selenium undetected-chromedriver
    success, html = await test_selenium_undetected()
    results['selenium_uc'] = success
    if html:
        results['html_files'].append('selenium_uc')
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    print(f"🔥 FlareSolverr без прокси: {'✅ РАБОТАЕТ' if results['flaresolverr_no_proxy'] else '❌ НЕ РАБОТАЕТ'}")
    print(f"🔥 FlareSolverr с прокси: {'✅ РАБОТАЕТ' if results['flaresolverr_with_proxy'] else '❌ НЕ РАБОТАЕТ'}")
    print(f"🤖 Selenium UC: {'✅ РАБОТАЕТ' if results['selenium_uc'] else '❌ НЕ РАБОТАЕТ'}")
    
    success_count = sum([results['flaresolverr_no_proxy'], results['flaresolverr_with_proxy'], results['selenium_uc']])
    
    if success_count > 0:
        print(f"\n🎉 УСПЕХ! {success_count}/3 методов работают!")
        print("💡 Антибот Ozon можно обойти!")
        
        if results['flaresolverr_no_proxy'] or results['flaresolverr_with_proxy']:
            print("🔥 Рекомендуется использовать FlareSolverr")
        if results['selenium_uc']:
            print("🤖 Можно использовать Selenium undetected-chromedriver")
    else:
        print("\n❌ ВСЕ МЕТОДЫ НЕ РАБОТАЮТ!")
        print("💡 Рекомендации:")
        print("   - Запустите FlareSolverr: docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr:latest")
        print("   - Установите undetected-chromedriver: pip install undetected-chromedriver")
        print("   - Попробуйте другой прокси")
    
    # Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"flaresolverr_test_result_{timestamp}.json"
    
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в: {result_file}")

if __name__ == "__main__":
    asyncio.run(main())
