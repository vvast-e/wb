from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    wb_api_key = Column(JSON, default={})
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_admin = Column(String, nullable=True)  # Email админа, который создал пользователя

    tasks = relationship("ScheduledTask", back_populates="owner")