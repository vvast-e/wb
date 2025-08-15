#!/usr/bin/env python3
"""
Скрипт для расчёта средней скидки на Ozon с использованием Selenium + undetected-chromedriver (UC).
Не требует прокси и импортов из других частей проекта.
"""
import sys
import time
import re
from bs4 import BeautifulSoup

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
except ImportError:
    print("Требуется установить undetected-chromedriver и selenium: pip install undetected-chromedriver selenium bs4")
    sys.exit(1)

def clean_price_text(price_text):
    return ''.join(filter(str.isdigit, price_text.replace('\u2009', '').replace('\xa0', '')))

def extract_nm_id(url):
    match = re.search(r'/product/(?:[^/]+-)?(\d+)', url)
    return match.group(1) if match else None

PRODUCT_LINK_SELECTORS = [
    'a[href*="/product/"]',
    '.product-card a[href*="/product/"]',
    '[data-testid*="product"] a[href*="/product/"]',
    '.item a[href*="/product/"]',
    'div[data-index] a[href*="/product/"]'
]
DISCOUNT_SELECTORS = [
    '.k2z_27.zk0_27',
]
REGULAR_SELECTORS = [
    '.kz7_27.k7z_27.l1l_27',
]

def get_ozon_products_and_prices_uc(seller_url, max_products=None):
    print("="*50)
    print("▶️ ЗАПУСК: Ozon Selenium UC (без прокси)")
    print(f"URL: {seller_url}")
    options = uc.ChromeOptions()
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-infobars')
    options.add_argument('--incognito')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless=new')
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    options.add_argument(f'--user-agent={user_agent}')
    driver = uc.Chrome(options=options)
    driver.implicitly_wait(5)
    try:
        driver.get(seller_url)
        time.sleep(3)
        # --- Скроллим страницу для подгрузки товаров ---
        for i in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"INFO: Скролл {i+1}/4")
            time.sleep(2)
        main_handle = driver.current_window_handle
        soup = BeautifulSoup(driver.page_source, "lxml")
        products = []
        for sel in PRODUCT_LINK_SELECTORS:
            for a in soup.select(sel):
                href = a.get('href')
                if href and '/product/' in href:
                    full_url = href if href.startswith('http') else f"https://www.ozon.ru{href}"
                    if full_url not in products:
                        products.append(full_url)
        if max_products:
            products = products[:max_products]
        print(f"Найдено товаров: {len(products)}")
        prices_data = []
        discount_percentages = []
        for i, product_url in enumerate(products):
            print(f"\n--- Обрабатываем товар {i+1}/{len(products)} ---")
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
                'price_discount': price_discount,
                'price_discount_text': price_discount_text,
                'price_regular': price_regular,
                'price_regular_text': price_regular_text,
                'product_url': product_url
            }
            prices_data.append(price_info)
            print(f"  nm_id: {nm_id}")
            print(f"  Цена со скидкой: {price_discount_text} ({price_discount})")
            print(f"  Обычная цена: {price_regular_text} ({price_regular})")
            # Подсчет процента скидки
            if price_regular and price_discount and price_regular > 0:
                percent = (price_regular - price_discount) / price_regular * 100
                discount_percentages.append(percent)
                print(f"  Скидка: {percent:.2f}%")
            try:
                driver.close()
                driver.switch_to.window(main_handle)
            except Exception as e:
                print(f"Ошибка при закрытии вкладки: {e}")
            if i < len(products) - 1:
                time.sleep(1)
        print(f"\n=== РЕЗУЛЬТАТ ===")
        print(f"Получено цен: {len(prices_data)}")
        if discount_percentages:
            avg_discount = sum(discount_percentages) / len(discount_percentages)
            print(f"\nСредняя скидка по всем товарам: {avg_discount:.2f}% (по {len(discount_percentages)} товарам)")
        else:
            print("Не удалось рассчитать среднюю скидку (нет данных)")
        return prices_data
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА (selenium uc): {e}")
        return []
    finally:
        driver.quit()
        print("⏹ ЗАВЕРШЕНИЕ: Ozon Selenium UC")
        print("="*50 + "\n")

if __name__ == '__main__':
    print("=== Ozon Selenium UC Discount Stats ===")
    if len(sys.argv) > 1:
        seller_url = sys.argv[1]
    else:
        seller_url = input("Введите ссылку на страницу продавца Ozon: ").strip()
    if len(sys.argv) > 2:
        try:
            max_products = int(sys.argv[2])
        except ValueError:
            max_products = None
    else:
        max_products = input("Максимум товаров (Enter для всех): ").strip()
        max_products = int(max_products) if max_products.isdigit() else None
    get_ozon_products_and_prices_uc(seller_url, max_products=max_products) 