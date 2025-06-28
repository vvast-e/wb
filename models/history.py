from datetime import datetime
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from zoneinfo import ZoneInfo


def moscow_now():
    return datetime.now(ZoneInfo("Europe/Moscow"))


class History(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=moscow_now)
    scheduled_at = Column(TIMESTAMP(timezone=True), nullable=False)
    vendor_code = Column(String, nullable=False)
    status = Column(String(10), nullable=False)
    changes = Column(JSON, nullable=False)
    card_payload = Column(JSON, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    brand = Column(String, nullable=False)
    action = Column(String(50), nullable=False)

    user = relationship("User", back_populates="history")
