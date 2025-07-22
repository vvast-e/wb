import os
import asyncio
import random
from bs4 import BeautifulSoup
import undetected_playwright as upw
import logging

logger = logging.getLogger(__name__)

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

async def get_all_products_prices_playwright(seller_url, max_products=None):
    PROXY_HOST = os.getenv('OZON_PROXY_HOST', '')
    PROXY_PORT = os.getenv('OZON_PROXY_PORT', '')
    PROXY_USERNAME = os.getenv('OZON_PROXY_USERNAME', '')
    PROXY_PASSWORD = os.getenv('OZON_PROXY_PASSWORD', '')
    PROXY_SCHEME = os.getenv('OZON_PROXY_SCHEME', 'http')
    proxy = None
    if PROXY_HOST and PROXY_PORT:
        proxy = {
            'server': f'{PROXY_SCHEME}://{PROXY_HOST}:{PROXY_PORT}'
        }
        if PROXY_USERNAME and PROXY_PASSWORD:
            proxy['username'] = PROXY_USERNAME
            proxy['password'] = PROXY_PASSWORD
        logger.info(f'[PLAYWRIGHT] Используется прокси: {proxy}')
    else:
        logger.info('[PLAYWRIGHT] Прокси не задан, используется прямое соединение.')
    async with upw.async_playwright() as p:
        browser = await p.chromium.launch(headless="new", proxy=proxy)
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "User-Agent": user_agent
            }
        )
        page = await context.new_page()
        # Проверка IP-адреса
        logger.info('[PLAYWRIGHT] Проверка IP-адреса...')
        await page.goto('https://ifconfig.me', timeout=25000)
        await asyncio.sleep(2)
        ip_html = await page.content()
        ip_soup = BeautifulSoup(ip_html, 'lxml')
        ip_elem = ip_soup.find(id="ip_address")
        if ip_elem:
            ip_text = ip_elem.text.strip()
        else:
            ip_text = ip_soup.text.strip().split()[0] if ip_soup.text.strip() else 'N/A'
        logger.info(f'[PLAYWRIGHT] Внешний IP через Playwright: {ip_text}')
        # Переход на страницу продавца с обработкой JS-челленджа
        logger.info(f'[PLAYWRIGHT] Открываем страницу продавца: {seller_url}')
        max_attempts = 3
        for attempt in range(max_attempts):
            await page.goto(seller_url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(3)
            content = await page.content()
            if ("enable JavaScript" in content or "not a robot" in content) and attempt < max_attempts - 1:
                logger.warning("[PLAYWRIGHT] Антибот Ozon сработал! Пробуем перезагрузить...")
                await asyncio.sleep(10)
                continue
            break
        # Эмуляция человеческих действий
        for _ in range(random.randint(3, 7)):
            scroll_y = random.randint(200, 1200)
            await page.mouse.wheel(0, scroll_y)
            await asyncio.sleep(random.uniform(1, 2))
        for _ in range(random.randint(3, 7)):
            x = random.randint(0, 1800)
            y = random.randint(0, 900)
            await page.mouse.move(x, y, steps=random.randint(5, 20))
            await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.mouse.click(random.randint(100, 1800), random.randint(100, 900))
        await asyncio.sleep(2)
        # Парсинг товаров по селекторам
        html = await page.content()
        soup = BeautifulSoup(html, 'lxml')
        products = set()
        for selector in PRODUCT_LINK_SELECTORS:
            links = soup.select(selector)
            logger.info(f"[PLAYWRIGHT] Найдено товаров с селектором '{selector}': {len(links)}")
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
        logger.info(f'[PLAYWRIGHT] Всего найдено товаров: {len(products)}')
        # Парсинг цен по каждому товару
        prices_data = []
        for i, product_url in enumerate(products):
            logger.info(f'[{i+1}/{len(products)}] Парсим: {product_url}')
            prod_page = await context.new_page()
            await prod_page.goto(product_url, timeout=30000, wait_until="networkidle")
            await asyncio.sleep(2)
            prod_html = await prod_page.content()
            prod_soup = BeautifulSoup(prod_html, 'lxml')
            price_discount = None
            price_regular = None
            price_discount_text = None
            price_regular_text = None
            for sel in DISCOUNT_SELECTORS:
                elem_discount = prod_soup.select_one(sel)
                if elem_discount:
                    price_discount_text = elem_discount.get_text().strip()
                    price_discount = clean_price_text(price_discount_text)
                    if price_discount:
                        price_discount = int(price_discount)
                        break
            for sel in REGULAR_SELECTORS:
                elem_regular = prod_soup.select_one(sel)
                if elem_regular:
                    price_regular_text = elem_regular.get_text().strip()
                    price_regular = clean_price_text(price_regular_text)
                    if price_regular:
                        price_regular = int(price_regular)
                        break
            prices_data.append({
                'url': product_url,
                'price_discount': price_discount,
                'price_discount_text': price_discount_text,
                'price_regular': price_regular,
                'price_regular_text': price_regular_text
            })
            logger.info(f'  Цена со скидкой: {price_discount_text} ({price_discount})')
            logger.info(f'  Обычная цена: {price_regular_text} ({price_regular})')
            await prod_page.close()
            await asyncio.sleep(1)
        await browser.close()
        return prices_data 