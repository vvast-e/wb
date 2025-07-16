import os
import httpx
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from models.product import Product
from config import settings

OZON_API_KEY = os.getenv("OZON_API_KEY")
OZON_CLIENT_ID = "975642"  # как указано в запросе
OZON_BRAND = "11i Professional OZON"

async def fetch_ozon_products_v3(nm_ids: list, client_id=None, api_key=None):
    url = "https://api-seller.ozon.ru/v3/product/info/list"
    client_id = os.getenv("OZON_CLIENT_ID")
    api_key = os.getenv("OZON_API_KEY")
    headers = {
        "Client-Id": client_id,
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {"sku": [str(nm_id) for nm_id in nm_ids]}
    print(f"[OZON v3] Отправляем sku: {payload['sku']}")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        offer_ids = [item.get("offer_id") for item in items]
        print(f"[OZON v3] Ответ items: {items}")
        print(f"[OZON v3] Получены offer_id: {offer_ids}")
        return offer_ids

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