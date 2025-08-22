from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean, Index, JSON
from sqlalchemy.orm import relationship
from database import Base
# from utils.moscow_time import moscow_now  # если используется
from datetime import datetime

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    article = Column(String(32), nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)
    vendor_code = Column(String, nullable=True, index=True)  # Добавляем поле vendor_code
    author = Column(String, nullable=True)
    rating = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=True)
    status = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    main_text = Column(Text, nullable=True)
    pros_text = Column(Text, nullable=True)
    cons_text = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    is_negative = Column(Integer, default=0)
    is_processed = Column(Integer, default=0)
    processing_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True))  # default=moscow_now если нужно
    updated_at = Column(DateTime(timezone=True))  # default=moscow_now, onupdate=moscow_now если нужно
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    history_id = Column(Integer, ForeignKey("history.id"), nullable=True)
    # связи с другими таблицами
    user = relationship("User", back_populates="feedbacks")
    history = relationship("History", back_populates="feedbacks")
    top_tracking = relationship("FeedbackTopTracking", back_populates="feedback", uselist=False)
    is_deleted = Column(Boolean, default=False)  # Новый флаг для удалённых отзывов
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Время удаления отзыва
    wb_id = Column(String, index=True, nullable=False)  # Убираем unique=True
    aspects = Column(JSON, nullable=True)

    # Составные индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_brand_wb_id', 'brand', 'wb_id'),
        Index('idx_brand_article', 'brand', 'article'),
        Index('idx_user_brand', 'user_id', 'brand'),
        Index('idx_brand_is_deleted', 'brand', 'is_deleted'),
        Index('idx_article_rating', 'article', 'rating'),
        Index('idx_vendor_code_brand', 'vendor_code', 'brand'),  # Добавляем индекс для vendor_code + brand
        # Добавляем составной уникальный индекс для wb_id + article + brand
        Index('idx_wb_id_article_brand_unique', 'wb_id', 'article', 'brand', unique=True),
    )


class FeedbackTopTracking(Base):
    """Отслеживание времени нахождения негативных отзывов в топах"""
    __tablename__ = "feedback_top_tracking"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), nullable=False, index=True)
    article = Column(String(32), nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Время входа в топ
    entered_top_1_at = Column(DateTime(timezone=True), nullable=True)
    entered_top_3_at = Column(DateTime(timezone=True), nullable=True)
    entered_top_5_at = Column(DateTime(timezone=True), nullable=True)
    entered_top_10_at = Column(DateTime(timezone=True), nullable=True)
    
    # Время выхода из топа (когда негативный "выпал" из топа)
    exited_top_1_at = Column(DateTime(timezone=True), nullable=True)
    exited_top_3_at = Column(DateTime(timezone=True), nullable=True)
    exited_top_5_at = Column(DateTime(timezone=True), nullable=True)
    exited_top_10_at = Column(DateTime(timezone=True), nullable=True)
    
    # Время нахождения в топе (в секундах)
    time_in_top_1 = Column(Integer, default=0)  # секунды
    time_in_top_3 = Column(Integer, default=0)
    time_in_top_5 = Column(Integer, default=0)
    time_in_top_10 = Column(Integer, default=0)
    
    # Статус: находится ли отзыв в топе сейчас
    is_in_top_1 = Column(Boolean, default=False)
    is_in_top_3 = Column(Boolean, default=False)
    is_in_top_5 = Column(Boolean, default=False)
    is_in_top_10 = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    feedback = relationship("Feedback", back_populates="top_tracking")
    user = relationship("User", back_populates="feedback_top_tracking")
    
    # Индексы для оптимизации
    __table_args__ = (
        Index('idx_article_brand_user', 'article', 'brand', 'user_id'),
        Index('idx_feedback_id', 'feedback_id'),
        Index('idx_is_in_tops', 'is_in_top_1', 'is_in_top_3', 'is_in_top_5', 'is_in_top_10'),
    )


class FeedbackAnalytics(Base):
    __tablename__ = "feedback_analytics"

    id = Column(Integer, primary_key=True, index=True)
    article = Column(String(32), nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    total_reviews = Column(Integer, default=0)
    avg_rating = Column(Float, default=0.0)
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    negative_reviews_count = Column(Integer, default=0)
    processed_negative_count = Column(Integer, default=0)
    unprocessed_negative_count = Column(Integer, default=0)
    avg_sentiment = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True)) 