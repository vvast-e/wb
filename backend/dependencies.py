from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.utils.jwt import get_current_active_user
from backend.database import get_db
from backend.models.user import User
from backend.crud.user import get_decrypted_wb_key

async def get_current_user_with_wb_key(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.wb_api_key:
        raise HTTPException(
            status_code=400,
            detail="WB API key not configured for this user"
        )
    return current_user

async def get_wb_api_key(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_wb_key)
) -> str:
    return await get_decrypted_wb_key(db, current_user)