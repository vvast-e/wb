from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db, get_current_user_with_wb_key
from crud import history as history_crud
from schemas import History

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("/", response_model=list[History])
async def get_user_history(
    current_user: dict = Depends(get_current_user_with_wb_key),
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    return await history_crud.get_history_by_user(
        db, current_user["id"], limit
    )