import os
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.product import Product
from config import settings
import math

OZON_API_KEY = os.getenv("OZON_API_KEY")
OZON_CLIENT_ID = "975642"  # как указано в запросе
OZON_BRAND = "11i Professional OZON"

async def fetch_ozon_products_v3(nm_ids: list, client_id=None, api_key=None):
    url = "https://api-seller.ozon.ru/v3/product/info/list"
    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")
    
    print(f"[OZON API] Начинаем enrichment для {len(nm_ids)} товаров")
    print(f"[OZON API] Client-Id: {client_id}")
    print(f"[OZON API] Api-Key: {api_key[:10]}..." if api_key else "[OZON API] Api-Key: None")
    
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Преобразуем nm_ids в строки и фильтруем пустые
    sku_list = [str(nm_id) for nm_id in nm_ids if nm_id]
    print(f"[OZON API] Подготовленные sku: {sku_list[:5]}...")  # Показываем первые 5
    
    payload = {"sku": sku_list}
    print(f"[OZON API] Отправляем запрос к: {url}")
    print(f"[OZON API] Payload: {payload}")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"[OZON API] Response status: {resp.status_code}")
            print(f"[OZON API] Response headers: {dict(resp.headers)}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"[OZON API] Response data: {data}")
                items = data.get("items", [])
                offer_ids = [item.get("offer_id") for item in items]
                print(f"[OZON API] Получены offer_id: {offer_ids}")
                return offer_ids
            else:
                print(f"[OZON API] Ошибка {resp.status_code}: {resp.text}")
                return []
    except Exception as e:
        print(f"[OZON API] Исключение при запросе: {e}")
        return []

async def save_ozon_products_to_db(db: AsyncSession, items: list):
    added = 0
    for item in items:
        vendor_code = str(item.get("offer_id")) if item.get("offer_id") is not None else None
        nm_id = str(item.get("product_id")) if item.get("product_id") is not None else None
        if not vendor_code or not nm_id:
            print(f"[OZON] save_ozon_products_to_db: пропущен товар без offer_id или product_id: {item}")
            continue
        # Проверяем, есть ли уже такой товар
        exists = await db.execute(
            Product.__table__.select().where(Product.nm_id == nm_id)
        )
        if exists.first():
            print(f"[OZON] save_ozon_products_to_db: уже есть nm_id={nm_id}, vendor_code={vendor_code}")
            continue
        db.add(Product(nm_id=nm_id, vendor_code=vendor_code, brand=OZON_BRAND))
        print(f"[OZON] save_ozon_products_to_db: добавлен nm_id={nm_id}, vendor_code={vendor_code}")
        added += 1
    await db.commit()
    print(f"[OZON] save_ozon_products_to_db: всего добавлено товаров: {added}") 

async def fetch_offer_ids_and_skus_from_ozon(client_id=None, api_key=None, limit=1000):
    """Получить offer_id и sku через Ozon API /v4/product/info/attributes с пагинацией."""
    url = "https://api-seller.ozon.ru/v4/product/info/attributes"
    client_id = client_id or os.getenv("OZON_CLIENT_ID")
    api_key = api_key or os.getenv("OZON_API_KEY")
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    offer_sku_list = []
    last_id = ""
    page = 1
    while True:
        payload = {"limit": limit, "filter": {}}
        if last_id:
            payload["last_id"] = last_id
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"[ATTR] Страница {page} — статус: {resp.status_code}")
            data = resp.json()
            result = data.get("result", [])
            for item in result:
                offer_id = item.get("offer_id", "")
                sku = item.get("sku", "")
                if offer_id:
                    offer_sku_list.append({"offer_id": offer_id, "sku": sku})
            last_id = data.get("last_id", None)
            print(f"[ATTR] last_id: {last_id}, получено товаров: {len(result)}, всего: {len(offer_sku_list)}")
            if not last_id or not result:
                break
            page += 1
    print(f"[ATTR] Всего товаров собрано: {len(offer_sku_list)}")
    return offer_sku_list

# Удаляю функцию fetch_products_info_by_offer_ids и все связанные с ней вызовы и импорты


def save_ozon_prices_to_txt(items, filename="ozon_prices_test.txt"):
    """Сохраняет цены и индексы из API Ozon в txt-файл для анализа."""
    with open(filename, "w", encoding="utf-8") as f:
        for item in items:
            offer_id = item.get("offer_id", "")
            name = item.get("name", "")
            price = item.get("price", "")
            old_price = item.get("old_price", "")
            price_indexes = item.get("price_indexes", {})
            f.write(f"offer_id: {offer_id}\n")
            f.write(f"name: {name}\n")
            f.write(f"price: {price}\n")
            f.write(f"old_price: {old_price}\n")
            f.write(f"price_indexes:\n")
            for idx_name in ["external_index_data", "ozon_index_data", "self_marketplaces_index_data"]:
                idx = price_indexes.get(idx_name, {})
                min_price = idx.get("minimal_price", "")
                min_cur = idx.get("minimal_price_currency", "")
                f.write(f"  {idx_name}.minimal_price: {min_price} {min_cur}\n")
            f.write("-----\n")
    print(f"[OZON] Сохранено в файл: {filename}") 

async def fetch_prices_v5_by_offer_ids(offer_ids, client_id=None, api_key=None):
    """Получить подробные цены по offer_id через /v5/product/info/prices (батчами по 1000)."""
    url = "https://api-seller.ozon.ru/v5/product/info/prices"
    client_id = client_id or os.getenv("OZON_CLIENT_ID")
    api_key = api_key or os.getenv("OZON_API_KEY")
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    batch_size = 1000
    all_items = []
    for i in range(0, len(offer_ids), batch_size):
        batch = offer_ids[i:i+batch_size]
        payload = {
            "filter": {"offer_id": batch},
            "limit": len(batch)
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"[V5] Статус: {resp.status_code}")
            print(f"[V5] Полный ответ API (batch {i//batch_size+1}): {resp.text}")
            data = resp.json()
            items = data.get("items", [])
            print(f"[V5] Получено товаров: {len(items)} (батч {i//batch_size+1})")
            all_items.extend(items)
    print(f"[V5] Всего товаров с ценами: {len(all_items)}")
    return all_items

ALL_PRICE_KEYS = [
    "auto_action_enabled", "auto_add_to_ozon_actions_list_enabled", "currency_code",
    "marketing_price", "marketing_seller_price", "min_price", "net_price",
    "old_price", "price", "retail_price", "vat"
]

ALL_INDEX_KEYS = [
    "color_index",
    "external_index_data",
    "ozon_index_data",
    "self_marketplaces_index_data"
]

ALL_INDEX_DATA_KEYS = [
    "min_price", "min_price_currency", "price_index_value"
]

def save_ozon_prices_v5_to_txt(items, offerid_to_sku, filename="ozon_prices_v5_test.txt"):
    """Сохраняет offer_id, sku, marketing_price и price из /v5/product/info/prices в txt-файл для анализа."""
    with open(filename, "w", encoding="utf-8") as f:
        for item in items:
            offer_id = item.get("offer_id", "")
            sku = offerid_to_sku.get(offer_id, "")
            price = item.get("price", {})
            marketing_price = price.get("marketing_price", "")
            main_price = price.get("price", "")
            f.write(f"offer_id: {offer_id}\n")
            f.write(f"sku: {sku}\n")
            f.write(f"marketing_price: {marketing_price}\n")
            f.write(f"price: {main_price}\n")
            f.write("-----\n")
    print(f"[V5] Сохранено в файл: {filename}") 