from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List


from crud.user import get_user_by_email
from database import get_db
from schemas import BrandCreate, BrandUpdate, IsAdminResponse, UserResponse, UserCreate
from crud.admin import (
    get_brands,
    create_brand,
    update_brand,
    delete_brand, register_new_user
)
from models.user import User
from utils.jwt import get_current_active_user

router = APIRouter(tags=["brands"], prefix="/api/admin")

@router.get("/brands/", response_model=Dict[str, str])
async def read_brands(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return await get_brands(db, current_user.id)

@router.post("/brands/", response_model=Dict[str, str])
async def add_new_brand(
    brand_data: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return await create_brand(db, current_user.id, brand_data)

@router.put("/brands/{brand_name}", response_model=Dict[str, str])
async def update_brand_api_key(
    brand_name: str,
    brand_data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return await update_brand(db, current_user.id, brand_name, brand_data)

@router.delete("/brands/{brand_name}", response_model=Dict[str, str])
async def remove_brand(
    brand_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    return await delete_brand(db, current_user.id, brand_name)
#Астахов И.А.

@router.get("/check-admin", response_model=IsAdminResponse)
async def check_admin(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_email(db, current_user.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"status": user.status}


@router.post("/register", response_model=UserResponse)
async def register_user_by_admin(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    user_data.owner_admin = current_user.email

    db_user = await register_new_user(db, user_data)
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        status=db_user.status,
        wb_api_key=db_user.wb_api_key,
        created_at=db_user.created_at,
        owner_admin=db_user.owner_admin,
        brands=list(db_user.wb_api_key.keys()) if db_user.wb_api_key else []
    )


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if current_user.status != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(User).where(User.owner_admin == current_user.email))
    users = result.scalars().all()

    print(users[0].wb_api_key)

    return [
        UserResponse(
            id=user.id,
            email=user.email,
            status=user.status,
            wb_api_key=user.wb_api_key,
            created_at=user.created_at,
            owner_admin=user.owner_admin,
            brands=list(user.wb_api_key.keys()) if user.wb_api_key else []
        )
        for user in users
    ]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.status != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(User).where(User.id == user_id).where(User.owner_admin == current_user.email))
    user_to_delete = result.scalar_one_or_none()

    if not user_to_delete:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await db.delete(user_to_delete)
    await db.commit()
    return


# Изменить статус пользователя
@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def change_user_status(
    user_id: int,
    new_status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.status != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(select(User).where(User.id == user_id).where(User.owner_admin == current_user.email))
    user_to_update = result.scalar_one_or_none()

    if not user_to_update:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user_to_update.status = new_status
    await db.commit()
    await db.refresh(user_to_update)

    return UserResponse(
        id=user_to_update.id,
        email=user_to_update.email,
        status=user_to_update.status,
        wb_api_key=user_to_update.wb_api_key,
        created_at=user_to_update.created_at,
        owner_admin=user_to_update.owner_admin,
        brands=list(user_to_update.wb_api_key.keys()) if user_to_update.wb_api_key else []
    )