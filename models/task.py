from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database import Base
from zoneinfo import ZoneInfo


def moscow_now():
    return datetime.now(ZoneInfo("Europe/Moscow"))

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    nm_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    scheduled_at = Column(TIMESTAMP(timezone=True), nullable=False)
    status = Column(String(10), default='pending')
    created_at = Column(DateTime(timezone=True), default=moscow_now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changes = Column(JSON, nullable=True)
    brand = Column(String, nullable=False)

    owner = relationship("User", back_populates="tasks")

