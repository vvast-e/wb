from sqlalchemy import Column, Integer, DateTime, JSON, String
from database import Base
from datetime import datetime

class PriceChangeHistory(Base):
    __tablename__ = "price_change_history"

    id = Column(Integer, primary_key=True, index=True)
    nm_id = Column(String(64), index=True, nullable=False)
    shop_id = Column(Integer, index=True, nullable=True)
    change_data = Column(JSON, nullable=False)  # json: {date, old_price, new_price, diff, ...}
    created_at = Column(DateTime, default=datetime.utcnow) 