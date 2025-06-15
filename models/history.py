from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON
from database import Base


class ActionHistory(Base):
    __tablename__ = "action_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    nm_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # 'update', 'media_upload', etc.
    payload = Column(JSON, nullable=False)
    status = Column(String(10), nullable=False)  # 'pending', 'success', 'error'
    timestamp = Column(DateTime, default=datetime.utcnow)
    wb_response = Column(JSON)  # Ответ от WB API