#!/usr/bin/env python3
"""
Парсер цен Ozon на основе Selenium (undetected-chromedriver)
Адаптирован под проект WB_API
"""

import time
import os
import random
import re
from bs4 import BeautifulSoup
from utils.ozon_api import fetch_ozon_products_v3, save_ozon_products_to_db
from database import AsyncSessionLocal

try:
    from seleniumwire import webdriver as sw_webdriver
except ImportError:
    sw_webdriver = None

PROXY_HOST = os.getenv('OZON_PROXY_HOST', 'p15184.ltespace.net')
PROXY_PORT = int(os.getenv('OZON_PROXY_PORT', 15184))
PROXY_USERNAME = os.getenv('OZON_PROXY_USERNAME', 'uek7t66y')
PROXY_PASSWORD = os.getenv('OZON_PROXY_PASSWORD', 'zbygddap')
PROXY_SCHEME = os.getenv('OZON_PROXY_SCHEME', 'http')

PRODUCT_LINK_SELECTORS = [
    'a[href*="/product/"]',
    '.product-card a[href*="/product/"]',
    '[data-testid*="product"] a[href*="/product/"]',
    '.item a[href*="/product/"]',
    'div[data-index] a[href*="/product/"]'
]
DISCOUNT_SELECTORS = [
    'span.kz1_27.y9k_27',
    'span.z3k_27.kz2_27',
]
REGULAR_SELECTORS = [
    'span.z5k_27.kz6_27.z9k_27',
    '.zk8_27.z8k_27.l4l_27',
]

def clean_price_text(price_text):
    return ''.join(filter(str.isdigit, price_text.replace('\u2009', '').replace('\xa0', '')))

def extract_nm_id(product_url: str) -> str:
    match = re.search(r'/product/(?:[^/]+-)?(\d+)', product_url)
    if match:
        return match.group(1)
    return None

def extract_seller_id(seller_url: str) -> int:
    match = re.search(r'seller[_/-](?:[a-zA-Z0-9-]+-)?(\d+)', seller_url)
    if match:
        return int(match.group(1))
    return None

def get_ozon_products_and_prices_seleniumwire(seller_url, max_products=None, save_to_db=False):
    if sw_webdriver is None:
        print("seleniumwire не установлен!")
        return []
    print("="*50)
    print("▶️ ЗАПУСК: Ozon SeleniumWire headless + антидетект + цены")
    print(f"URL: {seller_url}")
    print(f"Прокси: {PROXY_HOST}:{PROXY_PORT}")

    proxy_options = {
        'proxy': {
            'http': f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}",
            'https': f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}",
            'no_proxy': 'localhost,127.0.0.1'
        }
    }
    options = sw_webdriver.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--incognito')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless=new')
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    options.add_argument(f'--user-agent={user_agent}')
    driver = sw_webdriver.Chrome(seleniumwire_options=proxy_options, options=options)
    driver.implicitly_wait(5)
    try:
        # Антидетект: подмена webdriver и fingerprint
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("window.navigator.chrome = { runtime: {} }")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
        # WebGL spoof
        driver.execute_script('''
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) { return 'Intel Inc.'; }
                if (parameter === 37446) { return 'Intel Iris OpenGL Engine'; }
                return getParameter.call(this, parameter);
            };
        ''')
        # Canvas spoof
        driver.execute_script('''
            const toDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function() {
                return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA";
            };
        ''')
        # Проверка IP через SeleniumWire
        driver.get("https://ifconfig.me/")
        time.sleep(3)
        ip = driver.find_element("tag name", "body").text.strip()
        print(f"INFO: Внешний IP через SeleniumWire: {ip}")
        # --- Пауза между запросами (антибот) ---
        import random as _random
        sleep_time = _random.uniform(10, 20)
        print(f"INFO: Пауза {sleep_time:.1f} секунд перед следующим запросом...")
        time.sleep(sleep_time)
        # --- Переход на страницу продавца ---
        driver.get(seller_url)
        print("INFO: Ожидание загрузки страницы (до 20 секунд)...")
        time.sleep(_random.uniform(15, 20))
        # --- Скроллим страницу для подгрузки товаров ---
        for i in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"INFO: Скролл {i+1}/3")
            time.sleep(3)
        html = driver.page_source
        with open("ozon_debug_seleniumwire.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("INFO: HTML сохранен в ozon_debug_seleniumwire.html")
        soup = BeautifulSoup(html, "lxml")
        products = set()
        for selector in PRODUCT_LINK_SELECTORS:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and '/product/' in href:
                    full_url = href if href.startswith('http') else 'https://www.ozon.ru' + str(href)
                    products.add(full_url)
                if max_products and len(products) >= max_products:
                    break
            if max_products and len(products) >= max_products:
                break
        print(f"Найдено товаров: {len(products)}")
        # --- Парсинг цен по каждому товару ---
        prices_data = []
        main_handle = driver.current_window_handle
        seller_id = extract_seller_id(seller_url)
        for i, product_url in enumerate(products):
            print(f"\n--- Обрабатываем товар {i+1}/{len(products)} ---")
            # Открываем карточку товара в новой вкладке
            handles_before = set(driver.window_handles)
            driver.switch_to.window(main_handle)
            driver.switch_to.new_window('tab')
            time.sleep(0.5)
            handles_after = set(driver.window_handles)
            new_handles = handles_after - handles_before
            if not new_handles:
                print("Не удалось открыть новую вкладку!")
                continue
            new_handle = new_handles.pop()
            driver.switch_to.window(new_handle)
            driver.get(product_url)
            time.sleep(2)
            prod_soup = BeautifulSoup(driver.page_source, "lxml")
            price_discount = None
            price_regular = None
            price_discount_text = None
            price_regular_text = None
            for sel in DISCOUNT_SELECTORS:
                elem = prod_soup.select_one(sel)
                if elem:
                    price_discount_text = elem.get_text().strip()
                    price_discount = clean_price_text(price_discount_text)
                    if price_discount:
                        price_discount = int(price_discount)
                    break
            for sel in REGULAR_SELECTORS:
                elem = prod_soup.select_one(sel)
                if elem:
                    price_regular_text = elem.get_text().strip()
                    price_regular = clean_price_text(price_regular_text)
                    if price_regular:
                        price_regular = int(price_regular)
                    break
            nm_id = extract_nm_id(product_url)
            price_info = {
                'href': product_url,
                'nm_id': nm_id,
                'seller_id': seller_id,
                'price_discount': price_discount,
                'price_discount_text': price_discount_text,
                'price_regular': price_regular,
                'price_regular_text': price_regular_text,
                'product_url': product_url
            }
            prices_data.append(price_info)
            print(f"  nm_id: {nm_id}, seller_id: {seller_id}")
            print(f"  Цена со скидкой: {price_discount_text} ({price_discount})")
            print(f"  Обычная цена: {price_regular_text} ({price_regular})")
            try:
                driver.close()
                driver.switch_to.window(main_handle)
            except Exception as e:
                print(f"Ошибка при закрытии вкладки: {e}")
            # Пауза между товарами
            if i < len(products) - 1:
                time.sleep(1)
        print(f"\n=== РЕЗУЛЬТАТ ===")
        print(f"Получено цен: {len(prices_data)}")
        # --- Сохранение в БД, если нужно ---
        if save_to_db and prices_data:
            print("Сохраняем товары в БД...")
            import asyncio
            async def save():
                async with AsyncSessionLocal() as db:
                    await save_ozon_products_to_db(db, prices_data)
            asyncio.run(save())
        return prices_data
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА (seleniumwire): {e}")
        return []
    finally:
        driver.quit()
        print("⏹ ЗАВЕРШЕНИЕ: Ozon SeleniumWire")
        print("="*50 + "\n")

if __name__ == "__main__":
    seller_url = "https://www.ozon.ru/seller/11i-professional-975642/products/"
    get_ozon_products_and_prices_seleniumwire(seller_url, max_products=10, save_to_db=False) 