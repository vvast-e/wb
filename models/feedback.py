from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, Boolean, Index, JSON
from sqlalchemy.orm import relationship
from database import Base
# from utils.moscow_time import moscow_now  # если используется

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    article = Column(String(32), nullable=False, index=True)
    brand = Column(String, nullable=False, index=True)
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
    user = relationship("User", back_populates="feedbacks")
    history = relationship("History", back_populates="feedbacks")
    is_deleted = Column(Boolean, default=False)  # Новый флаг для удалённых отзывов
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Время удаления отзыва
    wb_id = Column(String, unique=True, index=True, nullable=False)  # Уникальный id отзыва WB
    aspects = Column(JSON, nullable=True)  # Новое поле для хранения аспектов отзыва

    # Составные индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_brand_wb_id', 'brand', 'wb_id'),
        Index('idx_brand_article', 'brand', 'article'),
        Index('idx_user_brand', 'user_id', 'brand'),
        Index('idx_brand_is_deleted', 'brand', 'is_deleted'),
        Index('idx_article_rating', 'article', 'rating'),
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
    created_at = Column(DateTime(timezone=True))  # default=moscow_now если нужно 