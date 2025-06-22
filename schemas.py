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
    user_id: Optional[int] = None
    changes: dict = {}

    @validator('scheduled_at')
    def convert_to_msk(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=tz.gettz('Europe/Moscow'))
        return v.astimezone(tz.gettz('Europe/Moscow'))


class Characteristic(BaseModel):
    id: int
    value: list[str]


class TaskCreate(BaseModel):
    content: dict = {}
    scheduled_at: datetime


class Task(TaskBase):
    id: Optional[int] = None  # Необязательное поле
    status: Optional[str] = None  # Необязательное поле
    created_at: Optional[datetime] = None  # Необязательное поле

    class Config:
        orm_mode = True




class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str
    wb_api_key: Optional[Dict[str, str]] = {}
    status: Optional[str]
    owner_admin: Optional[str] = None  # Добавляем новое поле


class IsAdminResponse(BaseModel):
    status: str


class UserResponse(UserBase):
    id: int
    wb_api_key: Dict[str, Any]
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    owner_admin: Optional[str] = None
    brands: Optional[List[str]] = None

    class Config:
        from_attributes = True


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
    scheduled_at: datetime


class MediaUploadResponse(WBApiResponse):
    url: Optional[str] = None


class UploadMediaRequest(BaseModel):
    nmId: str
    photoNumber: int
    file: UploadFile = File(...)


class BrandBase(BaseModel):
    name: str
    api_key: str


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str
    api_key: str


class BrandInDB(BrandBase):
    class Config:
        orm_mode = True
