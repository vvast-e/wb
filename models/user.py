from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    wb_api_key = Column(JSON, nullable=True)
    status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_admin = Column(String, nullable=True)
    imagebb_key = Column(String, nullable=True)

    # связи с другими таблицами
    tasks = relationship("ScheduledTask", back_populates="owner")
    history = relationship("History", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user") 