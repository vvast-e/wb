from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.shop import Shop, PriceHistory
from typing import List, Optional


async def create_shop(db: AsyncSession, name: str, wb_name: str, user_id: int) -> Shop:
    db_shop = Shop(name=name, wb_name=wb_name, user_id=user_id)
    db.add(db_shop)
    await db.commit()
    await db.refresh(db_shop)
    return db_shop


async def get_shop_by_id(db: AsyncSession, shop_id: int) -> Optional[Shop]:
    result = await db.execute(select(Shop).where(Shop.id == shop_id))
    return result.scalars().first()


async def get_shop_by_name(db: AsyncSession, name: str) -> Optional[Shop]:
    result = await db.execute(select(Shop).where(Shop.name == name))
    return result.scalars().first()


async def get_shops_by_user(db: AsyncSession, user_id: int) -> List[Shop]:
    result = await db.execute(
        select(Shop).where(Shop.user_id == user_id, Shop.is_active == True)
    )
    return result.scalars().all()


async def get_all_active_shops(db: AsyncSession) -> List[Shop]:
    result = await db.execute(select(Shop).where(Shop.is_active == True))
    return result.scalars().all()


async def update_shop(db: AsyncSession, shop_id: int, **kwargs) -> Optional[Shop]:
    shop = await get_shop_by_id(db, shop_id)
    if shop:
        for key, value in kwargs.items():
            setattr(shop, key, value)
        await db.commit()
        await db.refresh(shop)
    return shop


async def delete_shop(db: AsyncSession, shop_id: int) -> bool:
    shop = await get_shop_by_id(db, shop_id)
    if shop:
        shop.is_active = False
        await db.commit()
        return True
    return False


async def add_price_history(db: AsyncSession, vendor_code: str, shop_id: int, nm_id: str, 
                     new_price: int, old_price: Optional[int] = None, market: str = "wb") -> Optional[PriceHistory]:
    # Проверка на дублирование: ищем последнюю запись с учётом market
    result = await db.execute(
        select(PriceHistory).where(
            PriceHistory.nm_id == str(nm_id),
            PriceHistory.shop_id == shop_id,
            PriceHistory.market == market
        ).order_by(PriceHistory.price_date.desc())
    )
    last = result.scalars().first()
    if last and last.new_price == new_price:
        # Уже есть такая цена, не добавляем дубликат
        return None
    price_history = PriceHistory(
        vendor_code=vendor_code,
        shop_id=shop_id,
        nm_id=str(nm_id),
        new_price=new_price,
        old_price=old_price,
        market=market
    )
    db.add(price_history)
    await db.commit()
    await db.refresh(price_history)
    return price_history


async def get_price_history_by_vendor(db: AsyncSession, vendor_code: str, shop_id: int) -> List[PriceHistory]:
    result = await db.execute(
        select(PriceHistory).where(
            PriceHistory.vendor_code == vendor_code,
            PriceHistory.shop_id == shop_id
        ).order_by(PriceHistory.price_date.desc())
    )
    return result.scalars().all()


async def get_latest_price(db: AsyncSession, vendor_code: str, shop_id: int) -> Optional[PriceHistory]:
    result = await db.execute(
        select(PriceHistory).where(
            PriceHistory.vendor_code == vendor_code,
            PriceHistory.shop_id == shop_id
        ).order_by(PriceHistory.price_date.desc())
    )
    return result.scalars().first() 


async def get_price_history_by_nmid(db: AsyncSession, nm_id: str, shop_id: int) -> List[PriceHistory]:
    result = await db.execute(
        select(PriceHistory).where(
            PriceHistory.nm_id == nm_id,
            PriceHistory.shop_id == shop_id
        ).order_by(PriceHistory.price_date.desc())
    )
    return result.scalars().all() 


async def save_price_change_history(db: AsyncSession, nm_id: str, shop_id: int, old_price: int, new_price: int):
    from models.price_change_history import PriceChangeHistory
    from datetime import datetime
    change_data = {
        "date": datetime.utcnow().isoformat(),
        "old_price": old_price,
        "new_price": new_price,
        "diff": new_price - old_price if old_price is not None else None
    }
    record = PriceChangeHistory(
        nm_id=str(nm_id),
        shop_id=shop_id,
        change_data=change_data
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record 