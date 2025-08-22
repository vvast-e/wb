from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=True)  # Название магазина (может быть null для WB)
    wb_name = Column(String, nullable=True)  # Название магазина на WB (может быть null для Ozon)
    platform = Column(String(10), nullable=False, default="wb")  # Тип платформы: "wb" или "ozon"
    user_id = Column(Integer, nullable=False)  # ID пользователя, добавившего магазин
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    vendor_code = Column(String, nullable=False, index=True)
    shop_id = Column(Integer, nullable=False)
    nm_id = Column(String(64), nullable=False, index=True)
    old_price = Column(Integer, nullable=True)
    new_price = Column(Integer, nullable=False)
    price_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    market = Column(String(10), nullable=False, default="wb")