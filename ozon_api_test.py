import asyncio
from utils.ozon_api import (
    fetch_offer_ids_and_skus_from_ozon,
    fetch_prices_v5_by_offer_ids,
    save_ozon_prices_v5_to_txt
)

async def main():
    # Получаем все offer_id и sku
    offer_sku_list = await fetch_offer_ids_and_skus_from_ozon()
    print(f"Всего товаров: {len(offer_sku_list)}")
    offer_ids = [item["offer_id"] for item in offer_sku_list]
    offerid_to_sku = {item["offer_id"]: item["sku"] for item in offer_sku_list}

    # Получаем подробные цены по товарам
    items = await fetch_prices_v5_by_offer_ids(offer_ids)
    print(f"Всего товаров с ценами: {len(items)}")

    # Сохраняем в txt
    save_ozon_prices_v5_to_txt(items, offerid_to_sku, filename="ozon_prices_v5_test.txt")
    print("Готово! Смотри ozon_prices_v5_test.txt")

if __name__ == "__main__":
    asyncio.run(main()) 