#!/usr/bin/env python3
"""
Парсер цен Ozon на основе Selenium (undetected-chromedriver)
Адаптирован под проект WB_API
"""

import time
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import re
import asyncio
import logging
from utils.ozon_api import fetch_ozon_products_v3, save_ozon_products_to_db
from database import AsyncSessionLocal
import requests
import os
import tempfile
import contextlib

# Настройка логирования
logger = logging.getLogger(__name__)

# === Прокси параметры ===
PROXY_HOST = 'localhost'
PROXY_PORT = 3128  # порт, который ты укажешь в 3proxy


# Селекторы для поиска товаров и цен (адаптированы под ваш опыт)
PRODUCT_LINK_SELECTORS = [
    'a[href*="/product/"]',
    '.product-card a[href*="/product/"]',
    '[data-testid*="product"] a[href*="/product/"]',
    '.item a[href*="/product/"]',
    'div[data-index] a[href*="/product/"]'
]

PRICE_SELECTORS = [
    'span.kz1_27.y9k_27',  # цена со скидкой карты озон
    'span.z5k_27.kz6_27.z9k_27',  # обычная цена
]

def clean_price_text(price_text):
    # Удаляем неразрывные пробелы, символ рубля и лишние символы
    return ''.join(filter(str.isdigit, price_text.replace('\u2009', '').replace('\xa0', '')))


def check_proxy_ip_via_requests():
    """Проверяет внешний IP через requests с теми же прокси, что и для Selenium."""
    proxies = {
        "http": f"http://{PROXY_HOST}:{PROXY_PORT}",
        "https": f"https://{PROXY_HOST}:{PROXY_PORT}",
    }
    try:
        response = requests.get("https://api.ipify.org", proxies=proxies, timeout=10)
        logger.info(f"[ПРОКСИ] Внешний IP через requests: {response.text}")
    except Exception as e:
        logger.error(f"[ПРОКСИ] Не удалось получить IP через requests: {e}")


# --- Динамическое создание расширения для прокси с авторизацией ---
def create_temp_proxy_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='https'):
    context = tempfile.TemporaryDirectory()
    extension_dir = context.name
    manifest_json = '{"version":"1.0.0","manifest_version":2,"name":"Chrome Proxy","permissions":["proxy","tabs","unlimitedStorage","storage","<all_urls>","webRequest","webRequestBlocking"],"background":{"scripts":["auth.js"]},"minimum_chrome_version":"22.0.0"}'
    background_js = (
        'var e={mode:"fixed_servers",rules:{singleProxy:{scheme:"%s",host:"%s",port:parseInt(%s)},bypassList:["localhost"]}};'
        'chrome.proxy.settings.set({value:e,scope:"regular"},function(){}),'
        'chrome.webRequest.onAuthRequired.addListener((function(e){return{authCredentials:{username:"%s",password:"%s"}}}),{urls:["<all_urls>"]},["blocking"]);'
        % (scheme, proxy_host, proxy_port, proxy_username, proxy_password)
    )
    with open(f"{extension_dir}/manifest.json", "w", encoding="utf8") as f:
        f.write(manifest_json)
    with open(f"{extension_dir}/auth.js", "w", encoding="utf8") as f:
        f.write(background_js)
    return context, extension_dir


def start_driver(headless_mode: str = 'headless'):
    """Запуск браузера с настройками и локальным прокси-гейтом (без авторизации)."""
    options = uc.ChromeOptions()
    if headless_mode:
        options.add_argument(f"--{headless_mode}")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # --- Указываем прокси без авторизации ---
    options.add_argument(f"--proxy-server={PROXY_HOST}:{PROXY_PORT}")
    try:
        driver = uc.Chrome(options=options)
    except Exception as e:
        logger.error("[ОШИБКА] Не удалось запустить Chrome. Убедитесь, что браузер Chrome или Chromium установлен на вашем компьютере.")
        logger.error(f"Детали ошибки: {e}")
        raise
    driver.implicitly_wait(5)
    # --- Проверяем внешний IP через Selenium ---
    try:
        driver.get("https://api.ipify.org")
        ip_in_browser = driver.page_source.strip()
        logger.info(f"[ПРОКСИ] Внешний IP через Selenium: {ip_in_browser}")
    except Exception as e:
        logger.error(f"[ПРОКСИ] Не удалось получить IP через Selenium: {e}")
    return driver


def get_products_from_seller_page(driver, seller_url, max_products=None):
    logger.info(f"Загружаем страницу продавца: {seller_url}")
    driver.get(seller_url)
    time.sleep(3)
    # Сохраняем HTML-код страницы Ozon для отладки
    with open('ozon_debug.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    logger.info("HTML-код страницы Ozon сохранён в ozon_debug.html")
    # Скроллим для подгрузки товаров
    logger.info("Скроллим страницу для загрузки товаров...")
    for i in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        logger.info(f"Скролл {i+1}/5")
    soup = BeautifulSoup(driver.page_source, "lxml")
    products = set()
    logger.info("Ищем товары по селекторам...")
    for selector in PRODUCT_LINK_SELECTORS:
        links = soup.select(selector)
        logger.info(f"Найдено товаров с селектором '{selector}': {len(links)}")
        for link in links:
            href = link.get('href')
            if isinstance(href, list):
                href = href[0] if href else None
            if href and '/product/' in href:
                full_url = href if href.startswith('http') else 'https://www.ozon.ru' + str(href)
                products.add(full_url)
            if max_products and len(products) >= max_products:
                break
        if max_products and len(products) >= max_products:
            break
    logger.info(f"Всего найдено товаров: {len(products)}")
    return list(products) if not max_products else list(products)[:max_products]


def get_product_price_new_tab(driver, product_url, main_handle):
    logger.info(f"Получаем цену товара: {product_url}")
    try:
        handles_before = set(driver.window_handles)
        driver.switch_to.window(main_handle)
        # Открываем новую вкладку через Selenium API
        driver.switch_to.new_window('tab')
        time.sleep(0.5)
        handles_after = set(driver.window_handles)
        new_handles = handles_after - handles_before
        if not new_handles:
            logger.warning("Не удалось открыть новую вкладку!")
            return None
        new_handle = new_handles.pop()
        driver.switch_to.window(new_handle)
        driver.get(product_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")
        price_discount = None
        price_regular = None
        price_discount_text = None
        price_regular_text = None
        # Ищем цену со скидкой по всем возможным селекторам
        discount_selectors = [
            'span.kz1_27.y9k_27',
            'span.z3k_27.kz2_27',
        ]
        for sel in discount_selectors:
            elem_discount = soup.select_one(sel)
            if elem_discount:
                price_discount_text = elem_discount.get_text().strip()
                price_discount = clean_price_text(price_discount_text)
                if price_discount:
                    price_discount = int(price_discount)
                    logger.info(f"Найдена цена со скидкой: {price_discount_text} ({price_discount} ₽)")
                    break
        # Ищем обычную цену по всем возможным селекторам
        regular_selectors = [
            'span.z5k_27.kz6_27.z9k_27',
            '.zk8_27.z8k_27.l4l_27',
        ]
        for sel in regular_selectors:
            elem_regular = soup.select_one(sel)
            if elem_regular:
                price_regular_text = elem_regular.get_text().strip()
                price_regular = clean_price_text(price_regular_text)
                if price_regular:
                    price_regular = int(price_regular)
                    logger.info(f"Найдена обычная цена: {price_regular_text} ({price_regular} ₽)")
                    break
        try:
            driver.close()
            driver.switch_to.window(main_handle)
        except Exception as e:
            logger.error(f"Ошибка при закрытии вкладки: {e}")
        return {
            'href': product_url,
            'price_discount': price_discount,
            'price_discount_text': price_discount_text,
            'price_regular': price_regular,
            'price_regular_text': price_regular_text,
            'product_url': product_url
        }
    except Exception as e:
        logger.error(f"Ошибка при парсинге товара: {e}")
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(main_handle)
        except Exception as e2:
            logger.error(f"Ошибка при аварийном закрытии вкладки: {e2}")
        return None


def extract_nm_id(product_url: str) -> str:
    """Извлекает nm_id товара из ссылки Ozon."""
    match = re.search(r'/product/(?:[^/]+-)?(\d+)', product_url)
    if match:
        return match.group(1)  # вернуть строку!
    raise ValueError(f"Не удалось извлечь nm_id из ссылки: {product_url}")

def extract_seller_id(seller_url: str) -> int:
    """Извлекает seller_id магазина из ссылки Ozon (универсально)."""
    # Ищем seller_123456 или seller/xxx-123456
    match = re.search(r'seller[_/-](?:[a-zA-Z0-9-]+-)?(\d+)', seller_url)
    if match:
        return int(match.group(1))
    raise ValueError(f"Не удалось извлечь seller_id из ссылки: {seller_url}")

ROTATION_PERIOD = 300  # 5 минут (секунд)

def get_all_products_prices(seller_url, max_products=None, headless_mode: str = 'headless'):
    """Получение цен всех товаров продавца с обработкой ротации прокси."""
    driver = start_driver(headless_mode=headless_mode)
    proxy_start_time = time.time()
    try:
        logger.info(f"=== ПАРСИНГ ЦЕН OZON ===")
        logger.info(f"URL продавца: {seller_url}")
        if max_products:
            logger.info(f"Максимальное количество товаров: {max_products}")
        # Получаем seller_id
        try:
            seller_id = extract_seller_id(seller_url)
        except Exception as e:
            logger.error(f"Ошибка извлечения seller_id: {e}")
            seller_id = None
        # Получаем список товаров
        products = get_products_from_seller_page(driver, seller_url, max_products)
        if not products:
            logger.warning("Товары не найдены!")
            return []
        logger.info(f"\nНайдено товаров: {len(products)}")
        # Получаем цены товаров
        prices_data = []
        main_handle = driver.current_window_handle
        for i, product_url in enumerate(products):
            # --- Проверка на ротацию прокси ---
            elapsed = time.time() - proxy_start_time
            if elapsed > ROTATION_PERIOD - 6:
                logger.info('[ПРОКСИ] Жду ротацию IP...')
                time.sleep(ROTATION_PERIOD - elapsed + 2)
                proxy_start_time = time.time()
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = start_driver(headless_mode=headless_mode)
                main_handle = driver.current_window_handle
            logger.info(f"\n--- Обрабатываем товар {i+1}/{len(products)} ---")
            price_info = get_product_price_new_tab(driver, product_url, main_handle)
            if price_info:
                # Извлекаем nm_id
                try:
                    nm_id = extract_nm_id(product_url)
                except Exception as e:
                    logger.error(f"Ошибка извлечения nm_id: {e}")
                    nm_id = None
                price_info['nm_id'] = str(nm_id)
                price_info['seller_id'] = seller_id
                prices_data.append(price_info)
                logger.info(f"✅ Товар {i+1} обработан (nm_id={nm_id}, seller_id={seller_id})")
            else:
                logger.warning(f"❌ Не удалось получить цену для товара {i+1}")
                break  # Если сессия потеряна — прекращаем парсинг
            # Пауза между товарами
            if i < len(products) - 1:
                time.sleep(1)
        logger.info(f"\n=== РЕЗУЛЬТАТ ===")
        logger.info(f"Получено цен: {len(prices_data)}")
        for i, price_data in enumerate(prices_data):
            logger.info(f"\nТовар {i+1}:")
            logger.info(f"  Ссылка: {price_data['href']}")
            logger.info(f"  nm_id: {price_data.get('nm_id', 'N/A')}")
            logger.info(f"  seller_id: {price_data.get('seller_id', 'N/A')}")
            logger.info(f"  Цена со скидкой: {price_data.get('price_discount', 'N/A')} ₽")
            logger.info(f"  Полный текст цены со скидкой: {price_data.get('price_discount_text', 'N/A')}")
            logger.info(f"  Обычная цена: {price_data.get('price_regular', 'N/A')} ₽")
            logger.info(f"  Полный текст обычной цены: {price_data.get('price_regular_text', 'N/A')}")
            logger.info(f"  URL товара: {price_data.get('product_url', 'N/A')}")
        return prices_data
    finally:
        logger.info("Закрываем браузер...")
        driver.quit()


def get_all_products_prices_async(*args, **kwargs):
    """Асинхронная обёртка для совместимости с telegram_bot.py (реально остаётся синхронной)."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, get_all_products_prices, *args, **kwargs)


def load_ozon_products_to_db():
    logger.info("=== load_ozon_products_to_db: старт ===")
    async def _load():
        logger.info("=== _load: старт ===")
        async with AsyncSessionLocal() as db:
            items = await fetch_ozon_products_v3([])
            await save_ozon_products_to_db(db, items)
            logger.info(f"[OZON] Загружено товаров: {len(items)}")
    asyncio.run(_load())


def test_ozon_api_prices():
    import asyncio
    async def run():
        # offer_ids = await fetch_all_offer_ids_from_ozon() # Удален
        # items = await fetch_products_info_by_offer_ids(offer_ids) # Удален
        # save_ozon_prices_to_txt(items) # Удален
        pass # Удален
    asyncio.run(run())


def main():
    logger.info("=== main: старт ===")
    # Сначала загружаем товары из OZON API в БД
    load_ozon_products_to_db()
    # Далее — стандартный парсинг цен
    # Тестовый URL продавца
    seller_url = "https://www.ozon.ru/seller/11i-professional-975642/products/"
    
    # Можно попробовать разные URL
    test_urls = [
        "https://www.ozon.ru/seller/11i-professional-975642/products/",
        "https://m.ozon.ru/seller/11i-professional-975642/products/",  # Мобильная версия
        "https://www.ozon.ru/seller/11i-professional-975642/",  # Без /products/
    ]
    
    for i, url in enumerate(test_urls):
        logger.info(f"\n{'='*50}")
        logger.info(f"ПОПЫТКА {i+1}/{len(test_urls)}")
        logger.info(f"URL: {url}")
        logger.info(f"{'='*50}")
        
        try:
            prices = get_all_products_prices(url)
            if prices:
                logger.info(f"\n✅ УСПЕХ! Получено {len(prices)} товаров!")
                break
            else:
                logger.warning(f"\n❌ Товары не найдены, пробуем следующий URL...")
        except Exception as e:
            logger.error(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        
        # Пауза между попытками
        if i < len(test_urls) - 1:
            logger.info("Ждем 5 секунд перед следующей попыткой...")
            time.sleep(5)
    
    logger.info("\nТест завершен")
    logger.info("\nТест OZON API (цены):")
    test_ozon_api_prices()


if __name__ == "__main__":
    main() 