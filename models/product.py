from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    nm_id = Column(String(64), unique=True, index=True, nullable=False)
    vendor_code = Column(String, index=True, nullable=True)
    brand = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 