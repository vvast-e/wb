from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import backend.config

Base=declarative_base()
engine=create_async_engine(backend.config.settings.POSTGRES_URL)
AsyncSessionLocal=sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
