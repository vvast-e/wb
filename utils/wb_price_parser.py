import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import json
import logging
import math
logger = logging.getLogger("telegram_bot")


class WBPriceParser:
    def __init__(self):
        self.base_url = "https://card.wb.ru"
        self.price_history_url = "https://basket-21.wbbasket.ru"
    
    async def get_product_details(self, nm_id: int) -> Optional[Dict]:
        """Получение деталей товара по nm_id"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/cards/v4/detail"
                params = {
                    "appType": 1,
                    "curr": "rub",
                    "dest": -7706796,
                    "spp": 30,
                    "hide_dtype": 13,
                    "ab_testing": False,
                    "lang": "ru",
                    "nm": nm_id
                }
                
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("products") and len(data["products"]) > 0:
                        return data["products"][0]
                return None
        except Exception as e:
            print(f"Ошибка при получении деталей товара {nm_id}: {e}")
            return None
    
    async def get_price_history(self, nm_id: int) -> List[Dict]:
        """Получение истории цен товара"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.price_history_url}/vol{nm_id//100000}/part{nm_id//1000}/vol{nm_id}/info/price-history.json"
                
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return data
                return []
        except Exception as e:
            print(f"Ошибка при получении истории цен товара {nm_id}: {e}")
            return []
    
    def extract_current_price(self, product_data: Dict) -> Optional[int]:
        """Извлечение текущей цены из данных товара"""
        try:
            if product_data.get("sizes") and len(product_data["sizes"]) > 0:
                size = product_data["sizes"][0]
                if size.get("price") and size["price"].get("product"):
                    return size["price"]["product"]
            return None
        except Exception as e:
            print(f"Ошибка при извлечении цены: {e}")
            return None
    
    def extract_vendor_code(self, product_data: Dict) -> Optional[str]:
        """Извлечение vendor code из данных товара"""
        try:
            # Ищем vendor code в различных полях
            if product_data.get("vendorCode"):
                return str(product_data["vendorCode"])
            
            # Если нет vendorCode, попробуем извлечь из других полей
            if product_data.get("supplierId"):
                return str(product_data["supplierId"])
            
            return None
        except Exception as e:
            print(f"Ошибка при извлечении vendor code: {e}")
            return None
    
    async def get_products_by_shop(self, shop_name: str, user_id: int, db_session) -> List[Dict]:
        """Получение товаров магазина по названию"""
        try:
            from crud.user import get_decrypted_wb_key
            from utils.wb_api import WBAPIClient
            from models.user import User
            from sqlalchemy import select
            
            # Получаем пользователя
            user_query = select(User).where(User.id == user_id)
            user_result = await db_session.execute(user_query)
            user = user_result.scalars().first()
            
            if not user or not user.wb_api_key:
                print(f"API ключи не найдены для пользователя {user_id}")
                return []
            
            # Ищем бренд по названию магазина (без учета регистра)
            shop_name_lower = shop_name.lower()
            found_brand = None
            
            for brand_name, encrypted_key in user.wb_api_key.items():
                if brand_name.lower() == shop_name_lower:
                    found_brand = brand_name
                    break
            
            if not found_brand:
                print(f"Бренд '{shop_name}' не найден в API ключах пользователя")
                return []
            
            # Получаем API ключ для бренда
            wb_api_key = await get_decrypted_wb_key(db_session, user, found_brand)
            
            # Получаем список товаров бренда
            wb_client = WBAPIClient(api_key=wb_api_key)
            items_result = await wb_client.get_cards_list()
            
            if not items_result.success:
                print(f"Не удалось получить товары бренда: {items_result.error}")
                return []
            
            items = items_result.data.get("cards", [])
            if not items:
                print("Товары не найдены")
                return []
            
            # Преобразуем товары в нужный формат
            products = []
            for item in items:
                product = {
                    "id": str(item.get("nmID", "")),
                    "name": item.get("name", ""),
                    "vendor_code": str(item.get("vendorCode", "")),
                    "brand": item.get("brand", ""),
                    "price": item.get("price", {}).get("product", 0) if item.get("price") else 0
                }
                products.append(product)
            
            print(f"Получено {len(products)} товаров для магазина '{shop_name}'")
            return products
            
        except Exception as e:
            print(f"Ошибка при получении товаров магазина {shop_name}: {e}")
            return []
    
    async def get_products_by_supplier_id(self, supplier_id: int, page_limit: int = 100) -> List[int]:
        """Получить все nmID товаров магазина по supplier id через публичный API WB"""
        import httpx
        nm_ids = []
        page = 1
        while True:
            url = "https://catalog.wb.ru/sellers/v4/catalog"
            params = {
                "ab_testing": "false",
                "appType": 1,
                "curr": "rub",
                "dest": -1257786,
                "hide_dtype": 13,
                "lang": "ru",
                "page": page,
                "sort": "popular",
                "spp": 30,
                "supplier": supplier_id
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    break
                data = response.json()
                products = data.get("products", [])
                if not products:
                    break
                nm_ids.extend([p["id"] for p in products if "id" in p])
                if len(products) < 100:
                    break
                page += 1
                if page > page_limit:
                    break
        return nm_ids
    
    async def monitor_prices(self, nm_ids: List[int]) -> List[Dict]:
        """Мониторинг цен для списка товаров"""
        results = []
        
        for nm_id in nm_ids:
            try:
                product_data = await self.get_product_details(nm_id)
                if product_data:
                    current_price = self.extract_current_price(product_data)
                    vendor_code = self.extract_vendor_code(product_data)
                    
                    if current_price and vendor_code:
                        results.append({
                            "nm_id": nm_id,
                            "vendor_code": vendor_code,
                            "current_price": current_price,
                            "product_name": product_data.get("name", ""),
                            "brand": product_data.get("brand", ""),
                            "shop_name": product_data.get("supplier", "")
                        })
            except Exception as e:
                print(f"Ошибка при мониторинге цены товара {nm_id}: {e}")
        
        return results 

async def fetch_wb_price_history(nm_id: int):
    import httpx
    from datetime import datetime
    nm_id_str = str(nm_id)
    vol = nm_id_str[:4]
    part = nm_id_str[:6]
    for basket_num in range(1, 31):
        url = f'https://basket-{basket_num}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/info/price-history.json'
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        return [
                            {
                                'date': datetime.utcfromtimestamp(item['dt']).strftime('%d.%m.%Y'),
                                'price': item['price']['RUB']
                            }
                            for item in data
                        ]
        except Exception as e:
            print(f'[History] Ошибка при попытке basket-{basket_num} для nm_id={nm_id}: {e}')
    return [] 

async def fetch_wb_current_price(nm_id: int):
    import httpx
    url = f'https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&spp=30&hide_dtype=13&ab_testing=false&lang=ru&nm={nm_id}'
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            # Теперь ищем products и product на верхнем уровне
            products = data.get('products')
            price = None
            if not products:
                pass
            elif not (isinstance(products, list) and len(products) > 0):
                pass
            else:
                product = products[0]
                sizes = product.get('sizes')
                if sizes is None:
                    pass
                elif not isinstance(sizes, list):
                    pass
                elif len(sizes) == 0:
                    pass
                else:
                    price_obj = sizes[0].get('price', {})
                    price = price_obj.get('product')
                    if price is None:
                        pass
            if price is None:
                # Пробуем product (альтернативный кейс)
                product = data.get('product')
                if not product:
                    pass
                else:
                    price_obj = product.get('price', {})
                    price = price_obj.get('product')
                    if price is None:
                        pass
            if price is not None:
                price_rub = price / 100
                price_wallet = math.floor(price_rub * 0.98)
                return price_rub, price_wallet
            else:
                pass
        else:
            pass
        return None, None 