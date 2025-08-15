import asyncio
import random
import httpx
from bs4 import BeautifulSoup
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

async def get_html_flaresolverr(url, max_timeout=60000):
    FLARESOLVERR_URL = "http://localhost:8191/v1"
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": max_timeout
    }
    async with httpx.AsyncClient(timeout=max_timeout/1000+5) as client:
        resp = await client.post(FLARESOLVERR_URL, json=payload)
        data = resp.json()
        if data.get("status") != "ok":
            raise Exception(f"FlareSolverr error: {data}")
        return data["solution"]["response"]

async def get_all_products_prices_flaresolverr(seller_url, max_products=None):
    logger.info(f'[FLARESOLVERR] Получаем страницу продавца: {seller_url}')
    try:
        # Проверка IP через FlareSolverr
        try:
            ip_html = await get_html_flaresolverr("https://ifconfig.me/")
            soup = BeautifulSoup(ip_html, "lxml")
            ip_elem = soup.find(id="ip_address")
            if ip_elem:
                ip = ip_elem.text.strip()
            else:
                ip = soup.text.strip()
            logger.info(f"[FLARESOLVERR] Внешний IP через FlareSolverr: {ip}")
            with open("ozon_ip_debug.txt", "w", encoding="utf-8") as f:
                f.write(ip)
        except Exception as e:
            logger.warning(f"[FLARESOLVERR] Не удалось получить IP: {e}")
        html = await get_html_flaresolverr(seller_url)
        with open("ozon_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        logger.error(f"[FLARESOLVERR] Ошибка получения HTML продавца: {e}")
        return []
    soup = BeautifulSoup(html, 'lxml')
    products = set()
    for selector in PRODUCT_LINK_SELECTORS:
        links = soup.select(selector)
        logger.info(f"[FLARESOLVERR] Найдено товаров по селектору '{selector}': {len(links)}")
        for link in links:
            href = link.get('href')
            if isinstance(href, list):
                href = href[0] if href else None
            if href and '/product/' in href:
                full_url = href if href.startswith('http') else 'https://www.ozon.ru' + href
                products.add(full_url)
            if max_products and len(products) >= max_products:
                break
        if max_products and len(products) >= max_products:
            break
    logger.info(f'[FLARESOLVERR] Всего найдено товаров: {len(products)}')
    prices_data = []
    for i, product_url in enumerate(products):
        logger.info(f'[{i+1}/{len(products)}] Парсим товар: {product_url}')
        try:
            prod_html = await get_html_flaresolverr(product_url)
            prod_soup = BeautifulSoup(prod_html, 'lxml')
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
            prices_data.append({
                'url': product_url,
                'price_discount': price_discount,
                'price_discount_text': price_discount_text,
                'price_regular': price_regular,
                'price_regular_text': price_regular_text
            })
            logger.info(f'  Цена со скидкой: {price_discount_text} ({price_discount})')
            logger.info(f'  Обычная цена: {price_regular_text} ({price_regular})')
        except Exception as e:
            logger.error(f"[FLARESOLVERR] Ошибка парсинга товара {product_url}: {e}")
            prices_data.append({
                'url': product_url,
                'price_discount': None,
                'price_discount_text': None,
                'price_regular': None,
                'price_regular_text': None
            })
        await asyncio.sleep(random.uniform(0.5, 1.2))
    return prices_data

# Для обратной совместимости:
get_all_products_prices_playwright = get_all_products_prices_flaresolverr