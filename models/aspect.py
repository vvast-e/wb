from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index, func
from sqlalchemy.orm import relationship
from database import Base

class Aspect(Base):
    """Модель для хранения всех аспектов (базовых + новых)"""
    __tablename__ = "aspects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False, default='Общие')
    description = Column(Text, nullable=True)
    is_base_aspect = Column(Boolean, default=False)
    is_new_aspect = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Индексы для оптимизации
    __table_args__ = (
        Index('idx_aspects_category', 'category'),
        Index('idx_aspects_usage_count', 'usage_count'),
        Index('idx_aspects_is_base', 'is_base_aspect'),
        Index('idx_aspects_is_new', 'is_new_aspect'),
    )

class FeedbackAspect(Base):
    """Модель для связи аспектов с отзывами (many-to-many)"""
    __tablename__ = "feedback_aspects"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, nullable=False, index=True)  # Ссылка на feedbacks.id
    aspect_name = Column(String(100), nullable=False, index=True)  # Ссылка на aspects.name
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    confidence = Column(Integer, default=50)  # 0-100 для упрощения
    evidence_words = Column(Text, nullable=True)  # JSON строка с ключевыми словами
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Индексы для оптимизации
    __table_args__ = (
        Index('idx_feedback_aspects_feedback_id', 'feedback_id'),
        Index('idx_feedback_aspects_aspect_name', 'aspect_name'),
        Index('idx_feedback_aspects_sentiment', 'sentiment'),
        Index('idx_feedback_aspects_feedback_sentiment', 'feedback_id', 'sentiment'),
    )


