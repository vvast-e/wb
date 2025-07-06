from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from utils.password import get_password_hash, verify_password, decrypt_api_dict
from models.user import User
from schemas import UserCreate


async def get_user_by_email(db: AsyncSession, email: str)->User:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Хешируем пароль
    hashed_password = get_password_hash(user.password)
    #hashed_wb_api=encrypt_api_key(user.wb_api_key)

    # Создаем пользователя
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        status="admin"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user



async def authenticate_user(db: AsyncSession, email: str, password: str)-> User:
    user = await get_user_by_email(db, email)
    print(user)
    if not user:
        print("Ненаход")
        return False
    if not verify_password(password, user.hashed_password):
        print("не прошло проверку")
        return False
    return user


async def get_decrypted_wb_key(db: AsyncSession, user: User, brand: str) -> str:
    if not user.wb_api_key:
        raise HTTPException(
            status_code=400,
            detail="У пользователя не настроены API-ключи"
        )

    decrypted_keys = decrypt_api_dict(user.wb_api_key)

    if brand not in decrypted_keys or not decrypted_keys[brand]:
        raise HTTPException(
            status_code=400,
            detail=f"API-ключ для бренда '{brand}' не найден или не расшифрован"
        )

    return decrypted_keys[brand]


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


