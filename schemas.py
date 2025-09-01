from dateutil import tz
from fastapi import UploadFile, File
from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import ConfigDict


class HistoryBase(BaseModel):
    nm_id: int
    action: str
    payload: Dict[str, Any]
    status: str


class HistoryCreate(HistoryBase):
    user_id: int


class History(HistoryBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True


class TaskBase(BaseModel):
    nm_id: int
    scheduled_at: datetime
    action: str
    payload: dict = {}
    user_id: int
    changes: dict = {}

    @validator('scheduled_at')
    def convert_to_msk(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=tz.gettz('Europe/Moscow'))
        return v.astimezone(tz.gettz('Europe/Moscow'))


class Characteristic(BaseModel):
    id: int
    value: list[str]



class HistoryResponse(BaseModel):
    id: int
    created_at: datetime
    scheduled_at: datetime
    vendor_code: str
    changes: Dict[str, Any]
    brand: str
    action: str
    user_email: str
    status: str

    class Config:
        orm_mode = True


class TaskCreate(BaseModel):
    content: dict = {}
    scheduled_at: datetime


class Task(TaskBase):
    id: Optional[int] = None
    status: Optional[str] = None
    brand: str
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class ImageBBUpdateRequest(BaseModel):
    imagebb_key: str


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str
    wb_api_key: Optional[Dict[str, str]] = {}
    imagebb_key: Optional[str] = ""
    status: Optional[str]
    owner_admin: Optional[str] = None  # Добавляем новое поле


class IsAdminResponse(BaseModel):
    status: str


class UserResponse(UserBase):
    id: int
    wb_api_key: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    owner_admin: Optional[str] = None
    brands: Optional[List[str]] = None
    imagebb_key: Optional[str] = None

    class Config:
        orm_mode = True


# github vvast-e
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class WBApiResponse(BaseModel):
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    wb_response: Optional[Any] = None


class MediaTaskRequest(BaseModel):
    nmId: int
    media: List[str]
    index: int
    scheduled_at: datetime


class MediaUploadResponse(WBApiResponse):
    url: Optional[str] = None


class UploadMediaRequest(BaseModel):
    nmId: str
    photoNumber: int
    file: UploadFile = File(...)


# Изменяем BrandBase и BrandUpdate
class BrandBase(BaseModel):
    name: str  # Название бренда (будет заполнено автоматически для WB)
    api_key: str

class BrandCreateRequest(BaseModel):
    """Схема для создания бренда с фронтенда"""
    platform: str = "wb"  # Тип платформы: "wb" или "ozon"
    wb_name: str  # API ключ (переименовано для совместимости с фронтендом)

class BrandCreate(BrandBase):
    pass

class BrandUpdate(BaseModel):
    name: str  # Название бренда
    api_key: str

class BrandUpdateRequest(BaseModel):
    """Схема для обновления бренда с фронтенда"""
    platform: str = "wb"  # Тип платформы: "wb" или "ozon"
    wb_name: str  # API ключ


class BrandInDB(BrandBase):
    class Config:
        orm_mode = True


class FeedbackBase(BaseModel):
    article: int
    brand: str
    author: Optional[str] = None
    rating: int
    date: Optional[datetime] = None
    status: Optional[str] = None
    text: Optional[str] = None
    main_text: Optional[str] = None
    pros_text: Optional[str] = None
    cons_text: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackUpdate(BaseModel):
    is_processed: Optional[int] = None
    processing_notes: Optional[str] = None
    sentiment_score: Optional[float] = None


class FeedbackResponse(FeedbackBase):
    id: int
    sentiment_score: Optional[float] = None
    is_negative: int
    is_processed: int
    processing_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_id: Optional[int] = None
    history_id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    bables_resolved: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class FeedbackAnalyticsResponse(BaseModel):
    total_reviews: int
    avg_rating: float
    rating_distribution: Dict[int, int]
    negative_count: int
    processed_negative_count: int
    unprocessed_negative_count: int
    processing_rate: float


class FeedbackListResponse(BaseModel):
    items: List[FeedbackResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class FeedbackFilterRequest(BaseModel):
    article: Optional[int] = None
    brand: Optional[str] = None
    rating_min: Optional[int] = None
    rating_max: Optional[int] = None
    is_negative: Optional[int] = None
    is_processed: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = 1
    per_page: int = 20
    order_by: str = "created_at"
    order_dir: str = "desc"


class FeedbackParseRequest(BaseModel):
    article: int
    brand: str
    max_date: Optional[datetime] = None  # Максимальная дата отзыва (по умолчанию 2 года назад)
    save_to_db: bool = True


# Схемы для магазинов и цен
class ShopBase(BaseModel):
    name: Optional[str] = None  # Название магазина (необязательно для WB)
    wb_name: Optional[str] = None  # Название магазина на WB (необязательно для Ozon)
    platform: str = "wb"  # Тип платформы: "wb" или "ozon"


class ShopCreateRequest(BaseModel):
    """Схема для создания магазина с фронтенда"""
    platform: str = "wb"  # Тип платформы: "wb" или "ozon"
    wb_name: str  # API ключ


class ShopCreate(ShopBase):
    pass


class ShopResponse(ShopBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PriceHistoryBase(BaseModel):
    vendor_code: str
    shop_id: int
    nm_id: int
    new_price: int
    old_price: Optional[int] = None


class PriceHistoryCreate(PriceHistoryBase):
    pass


class PriceHistoryResponse(PriceHistoryBase):
    id: int
    price_date: datetime
    created_at: datetime

    class Config:
        orm_mode = True


class TelegramUser(BaseModel):
    telegram_id: int
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
