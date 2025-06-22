from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from utils.jwt import get_current_active_user
from database import get_db
from models.user import User
from crud.user import get_decrypted_wb_key

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
    current_user: User = Depends(get_current_user_with_wb_key),
    db: AsyncSession = Depends(get_db)
) -> str:
    try:
        return await get_decrypted_wb_key(db, current_user)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"API key decryption failed: {str(e)}"
        )