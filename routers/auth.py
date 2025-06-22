from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from utils.jwt import create_access_token
from config import settings
from crud.user import authenticate_user, create_user
from database import get_db
from schemas import Token, UserCreate, UserResponse
router = APIRouter(tags=["auth"], prefix="/api/auth")


@router.post("/register", response_model=UserResponse)
async def register(
        user_data: UserCreate,
        db: AsyncSession = Depends(get_db)
):
    db_user=await create_user(db, user_data)
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        status=db_user.status,
        wb_api_key=db_user.wb_api_key,
        created_at=db_user.created_at
    )


@router.post("/token", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):

    user = await authenticate_user(db, form_data.username, form_data.password)
    if user:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )