from fastapi import HTTPException
from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict

from sqlalchemy.orm.attributes import flag_modified

from crud.user import get_user_by_email
from models import User
from schemas import BrandCreate, BrandUpdate, UserCreate
from utils.password import verify_password, get_password_hash, encrypt_api_dict, decrypt_api_dict, encrypt_api_key


async def get_brands(db: AsyncSession, user_id: int) -> Dict[str, str]:
    """Получить все бренды администратора"""
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not user.wb_api_key:
        raise HTTPException(status_code=404, detail="Brands not found")

    return decrypt_api_dict(user.wb_api_key)


async def create_brand(
        db: AsyncSession,
        user_id: int,
        brand_data: BrandCreate
) -> Dict[str, str]:
    try:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Инициализация и проверка
        if not isinstance(user.wb_api_key, dict):
            user.wb_api_key = {}

        if brand_data.name in user.wb_api_key:
            raise HTTPException(status_code=400, detail="Brand already exists")

        # Шифруем API ключ перед сохранением
        encrypted_key = encrypt_api_key(brand_data.api_key)

        # Обновляем данные
        user.wb_api_key[brand_data.name] = encrypted_key
        flag_modified(user, "wb_api_key")

        await db.commit()
        await db.refresh(user)
        return user.wb_api_key

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create brand: {str(e)}"
        )


async def update_brand(
        db: AsyncSession,
        user_id: int,
        brand_name: str,
        brand_data: BrandUpdate
) -> Dict[str, str]:
    try:
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not isinstance(user.wb_api_key, dict):
            user.wb_api_key = {}

        if brand_name not in user.wb_api_key:
            raise HTTPException(status_code=404, detail=f"Brand '{brand_name}' not found")

        # Шифруем новый API ключ
        encrypted_key = encrypt_api_key(brand_data.api_key)

        # Обновление с проверкой имени
        if brand_name != brand_data.name:
            if brand_data.name in user.wb_api_key:
                raise HTTPException(status_code=400, detail=f"Brand '{brand_data.name}' already exists")
            del user.wb_api_key[brand_name]

        user.wb_api_key[brand_data.name] = encrypted_key
        flag_modified(user, "wb_api_key")

        await db.commit()
        await db.refresh(user)
        return user.wb_api_key

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update brand: {str(e)}"
        )


async def delete_brand(
        db: AsyncSession,
        user_id: int,
        brand_name: str
) -> Dict[str, str]:
    try:
        # Получаем пользователя
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Инициализируем wb_api_key, если его нет или это не dict
        if not hasattr(user, 'wb_api_key') or not isinstance(user.wb_api_key, dict):
            user.wb_api_key = {}

        # Проверяем существование бренда
        if brand_name not in user.wb_api_key:
            raise HTTPException(
                status_code=404,
                detail=f"Brand '{brand_name}' not found"
            )

        # Удаляем бренд
        del user.wb_api_key[brand_name]
        flag_modified(user, "wb_api_key")

        # Сохраняем изменения
        await db.commit()
        await db.refresh(user)

        return user.wb_api_key

    except HTTPException:
        raise  # Пробрасываем уже обработанные HTTPException
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete brand: {str(e)}"
        )

async def register_new_user(db: AsyncSession, user: UserCreate) -> User:
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user.password)

    hashed_wb_api = encrypt_api_dict(user.wb_api_key or {})

    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        wb_api_key=hashed_wb_api,
        status=user.status,
        owner_admin=user.owner_admin
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
