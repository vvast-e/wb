from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.history import ActionHistory

async def create_history_record(
    db: AsyncSession,
    user_id: int,
    nm_id: int,
    action: str,
    payload: dict,
    status: str,
    wb_response: dict = None
):
    record = ActionHistory(
        user_id=user_id,
        nm_id=nm_id,
        action=action,
        payload=payload,
        status=status,
        wb_response=wb_response
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record

async def get_history_by_user(db: AsyncSession, user_id: int, limit: int = 100):
    result = await db.execute(
        select(ActionHistory)
        .where(ActionHistory.user_id == user_id)
        .order_by(ActionHistory.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()