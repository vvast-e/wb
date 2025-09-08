#!/usr/bin/env python3
"""
Тест проверки IP адреса через прокси
Проверяет что прокси работает и показывает другой IP
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

# Ваш локальный IP
YOUR_LOCAL_IP = "192.168.1.76"

async def check_ip_with_curl_cffi():
    """Проверка IP через curl_cffi"""
    print("🔍 ПРОВЕРКА IP ЧЕРЕЗ CURL_CFFI")
    print("-" * 40)
    
    try:
        from curl_cffi import requests as curl_requests
        
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        
        session = curl_requests.Session(
            impersonate="chrome120",
            proxies={
                'http': proxy_url,
                'https': proxy_url
            },
            timeout=30
        )
        
        # Проверяем IP
        response = await asyncio.to_thread(
            session.get, 
            'https://httpbin.org/ip',
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        if response.status_code == 200:
            ip_data = response.json()
            proxy_ip = ip_data.get('origin', 'Unknown')
            print(f"✅ curl_cffi IP: {proxy_ip}")
            return proxy_ip
        else:
            print(f"❌ curl_cffi ошибка: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ curl_cffi ошибка: {e}")
        return None

async def check_ip_with_httpx():
    """Проверка IP через httpx"""
    print("\n🔍 ПРОВЕРКА IP ЧЕРЕЗ HTTPX")
    print("-" * 40)
    
    try:
        import httpx
        
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        
        async with httpx.AsyncClient(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=30.0
        ) as client:
            
            response = await client.get(
                'https://httpbin.org/ip',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                ip_data = response.json()
                proxy_ip = ip_data.get('origin', 'Unknown')
                print(f"✅ httpx IP: {proxy_ip}")
                return proxy_ip
            else:
                print(f"❌ httpx ошибка: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ httpx ошибка: {e}")
        return None

async def check_ip_without_proxy():
    """Проверка IP без прокси"""
    print("\n🔍 ПРОВЕРКА IP БЕЗ ПРОКСИ")
    print("-" * 40)
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                'https://httpbin.org/ip',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                ip_data = response.json()
                direct_ip = ip_data.get('origin', 'Unknown')
                print(f"✅ Прямой IP: {direct_ip}")
                return direct_ip
            else:
                print(f"❌ Прямое подключение ошибка: {response.status_code}")
                return None
                
    except Exception as e:
        print(f"❌ Прямое подключение ошибка: {e}")
        return None

async def test_ozon_with_proxy():
    """Тест Ozon с прокси"""
    print("\n🌐 ТЕСТ OZON С ПРОКСИ")
    print("-" * 40)
    
    try:
        from curl_cffi import requests as curl_requests
        
        proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
        
        session = curl_requests.Session(
            impersonate="chrome120",
            proxies={
                'http': proxy_url,
                'https': proxy_url
            },
            timeout=30
        )
        
        # Тестируем Ozon
        test_url = "https://www.ozon.ru/"
        
        response = await asyncio.to_thread(
            session.get, 
            test_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        print(f"📊 Ozon статус: {response.status_code}")
        print(f"📏 Размер ответа: {len(response.text)} символов")
        
        if response.status_code == 200:
            if "ozon" in response.text.lower():
                print("✅ Ozon доступен через прокси!")
                return True
            else:
                print("⚠️ Ответ получен, но не похож на Ozon")
                return False
        elif response.status_code == 403:
            print("❌ 403 Forbidden - антибот заблокировал")
            return False
        else:
            print(f"❌ Ошибка {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ozon тест ошибка: {e}")
        return False

async def test_ozon_without_proxy():
    """Тест Ozon без прокси"""
    print("\n🌐 ТЕСТ OZON БЕЗ ПРОКСИ")
    print("-" * 40)
    
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.ozon.ru/",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            print(f"📊 Ozon статус: {response.status_code}")
            print(f"📏 Размер ответа: {len(response.text)} символов")
            
            if response.status_code == 200:
                if "ozon" in response.text.lower():
                    print("✅ Ozon доступен без прокси!")
                    return True
                else:
                    print("⚠️ Ответ получен, но не похож на Ozon")
                    return False
            elif response.status_code == 403:
                print("❌ 403 Forbidden - антибот заблокировал")
                return False
            else:
                print(f"❌ Ошибка {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Ozon тест ошибка: {e}")
        return False

async def main():
    """Основная функция"""
    print("🌐 ТЕСТ ПРОВЕРКИ IP АДРЕСА И ПРОКСИ")
    print("=" * 50)
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏠 Ваш локальный IP: {YOUR_LOCAL_IP}")
    print(f"🌐 Прокси: {PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}")
    print("=" * 50)
    
    # Проверяем IP адреса
    curl_ip = await check_ip_with_curl_cffi()
    httpx_ip = await check_ip_with_httpx()
    direct_ip = await check_ip_without_proxy()
    
    # Анализируем результаты
    print("\n📊 АНАЛИЗ IP АДРЕСОВ")
    print("-" * 40)
    
    if curl_ip and curl_ip != YOUR_LOCAL_IP:
        print(f"✅ curl_cffi прокси работает! IP: {curl_ip}")
        curl_proxy_works = True
    else:
        print(f"❌ curl_cffi прокси НЕ работает! IP: {curl_ip}")
        curl_proxy_works = False
    
    if httpx_ip and httpx_ip != YOUR_LOCAL_IP:
        print(f"✅ httpx прокси работает! IP: {httpx_ip}")
        httpx_proxy_works = True
    else:
        print(f"❌ httpx прокси НЕ работает! IP: {httpx_ip}")
        httpx_proxy_works = False
    
    if direct_ip:
        print(f"📡 Прямой IP: {direct_ip}")
    
    # Тестируем Ozon
    ozon_with_proxy = await test_ozon_with_proxy()
    ozon_without_proxy = await test_ozon_without_proxy()
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    print(f"🌐 curl_cffi прокси: {'✅ РАБОТАЕТ' if curl_proxy_works else '❌ НЕ РАБОТАЕТ'}")
    print(f"🌐 httpx прокси: {'✅ РАБОТАЕТ' if httpx_proxy_works else '❌ НЕ РАБОТАЕТ'}")
    print(f"🛒 Ozon с прокси: {'✅ ДОСТУПЕН' if ozon_with_proxy else '❌ ЗАБЛОКИРОВАН'}")
    print(f"🛒 Ozon без прокси: {'✅ ДОСТУПЕН' if ozon_without_proxy else '❌ ЗАБЛОКИРОВАН'}")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:")
    
    if not curl_proxy_works and not httpx_proxy_works:
        print("❌ ПРОКСИ НЕ РАБОТАЕТ!")
        print("   - Проверьте настройки прокси")
        print("   - Убедитесь что прокси активен")
        print("   - Попробуйте другой прокси")
    elif ozon_without_proxy and not ozon_with_proxy:
        print("⚠️ ПРОКСИ РАБОТАЕТ, НО OZON БЛОКИРУЕТ ПРОКСИ!")
        print("   - Попробуйте другой прокси")
        print("   - Используйте резидентный мобильный прокси")
        print("   - Попробуйте без прокси")
    elif ozon_with_proxy:
        print("🎉 ВСЕ РАБОТАЕТ!")
        print("   - Прокси работает корректно")
        print("   - Ozon доступен через прокси")
        print("   - Можно использовать парсер")
    else:
        print("🤔 СМЕШАННЫЕ РЕЗУЛЬТАТЫ")
        print("   - Нужно дополнительное тестирование")
    
    # Сохраняем результаты
    results = {
        'timestamp': datetime.now().isoformat(),
        'local_ip': YOUR_LOCAL_IP,
        'proxy_config': PROXY_CONFIG,
        'curl_cffi_ip': curl_ip,
        'httpx_ip': httpx_ip,
        'direct_ip': direct_ip,
        'curl_proxy_works': curl_proxy_works,
        'httpx_proxy_works': httpx_proxy_works,
        'ozon_with_proxy': ozon_with_proxy,
        'ozon_without_proxy': ozon_without_proxy
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"proxy_test_result_{timestamp}.json"
    
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Результаты сохранены в: {result_file}")

if __name__ == "__main__":
    asyncio.run(main())
