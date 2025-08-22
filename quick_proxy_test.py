#!/usr/bin/env python3
"""
Быстрый тест прокси для диагностики проблем
"""

import os
import subprocess
import time

def test_proxy_curl():
    """Тест прокси через curl"""
    print("🔧 БЫСТРЫЙ ТЕСТ ПРОКСИ")
    print("=" * 50)
    
    # Ваши настройки прокси
    proxy_host = os.getenv('OZON_PROXY_HOST', 'p15184.ltespace.net')
    proxy_port = os.getenv('OZON_PROXY_PORT', '15184')
    proxy_user = os.getenv('OZON_PROXY_USERNAME', 'uek7t66y')
    proxy_pass = os.getenv('OZON_PROXY_PASSWORD', 'zbygddap')
    
    print(f"🌐 Прокси: {proxy_host}:{proxy_port}")
    print(f"👤 Пользователь: {proxy_user}")
    print(f"🔑 Пароль: {'*' * len(proxy_pass)}")
    
    # Тест 1: Проверка IP через прокси
    print(f"\n📡 Тест 1: Проверка IP через прокси...")
    try:
        result = subprocess.run([
            'curl', '-x', f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
            '--connect-timeout', '30',
            '--max-time', '60',
            'https://ifconfig.me'
        ], capture_output=True, text=True, timeout=70)
        
        if result.returncode == 0:
            ip = result.stdout.strip()
            print(f"✅ УСПЕХ! IP через прокси: {ip}")
        else:
            error = result.stderr.strip()
            print(f"❌ ОШИБКА: {error}")
            
    except FileNotFoundError:
        print("❌ curl не установлен на сервере")
        print("💡 Установите: sudo apt install curl")
    except subprocess.TimeoutExpired:
        print("❌ Таймаут соединения с прокси")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
    
    # Тест 2: Проверка доступности Ozon через прокси
    print(f"\n🛒 Тест 2: Проверка Ozon через прокси...")
    try:
        result = subprocess.run([
            'curl', '-x', f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}",
            '--connect-timeout', '30',
            '--max-time', '60',
            'https://www.ozon.ru'
        ], capture_output=True, text=True, timeout=70)
        
        if result.returncode == 0:
            print(f"✅ УСПЕХ! Ozon доступен через прокси")
            print(f"📊 Размер ответа: {len(result.stdout)} байт")
        else:
            error = result.stderr.strip()
            print(f"❌ ОШИБКА: {error}")
            
    except Exception as e:
        print(f"❌ Ошибка при проверке Ozon: {e}")
    
    # Тест 3: Проверка без прокси (прямое соединение)
    print(f"\n🌍 Тест 3: Проверка без прокси...")
    try:
        result = subprocess.run([
            'curl', '--connect-timeout', '30',
            '--max-time', '60',
            'https://ifconfig.me'
        ], capture_output=True, text=True, timeout=70)
        
        if result.returncode == 0:
            ip = result.stdout.strip()
            print(f"✅ УСПЕХ! Прямой IP: {ip}")
        else:
            error = result.stderr.strip()
            print(f"❌ ОШИБКА: {error}")
            
    except Exception as e:
        print(f"❌ Ошибка при прямом соединении: {e}")

def test_selenium_simple():
    """Простой тест Selenium"""
    print(f"\n🔍 Тест 4: Простой тест Selenium...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("✅ Selenium импортирован успешно")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        print("🔧 Запуск Chrome...")
        driver = webdriver.Chrome(options=options)
        
        print("🌐 Переход на Google...")
        driver.get("https://www.google.com")
        
        title = driver.title
        print(f"✅ УСПЕХ! Заголовок: {title}")
        
        driver.quit()
        print("✅ Chrome закрыт успешно")
        
    except ImportError as e:
        print(f"❌ Selenium не установлен: {e}")
    except Exception as e:
        print(f"❌ Ошибка Selenium: {e}")

def main():
    """Главная функция"""
    print("🚀 БЫСТРАЯ ДИАГНОСТИКА VPS")
    print(f"⏰ Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_proxy_curl()
    test_selenium_simple()
    
    print(f"\n{'='*50}")
    print("🏁 ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("📋 Проверьте результаты выше")

if __name__ == "__main__":
    main()

