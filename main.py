from fastapi import FastAPI
from sqlalchemy import select
import asyncio

from database import engine, Base, AsyncSessionLocal
from routers import items, auth, tasks, admin, history, feedbacks, analytics, product_reviews, aspect_analysis
from utils.password import get_password_hash
from utils.scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware
from routers.shops_summary import router as shops_summary_router

app = FastAPI()

app.include_router(items.router)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(admin.router)
app.include_router(history.router)
app.include_router(feedbacks.router)
app.include_router(analytics.router)
app.include_router(product_reviews.router)
app.include_router(shops_summary_router)
app.include_router(aspect_analysis.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Запускаем планировщик в фоновой задаче
    asyncio.create_task(start_scheduler_async())
    print("🚀 Планировщик запущен в фоновой задаче")


async def start_scheduler_async():
    """Асинхронный запуск планировщика"""
    try:
        start_scheduler()
    except Exception as e:
        print(f"❌ Ошибка запуска планировщика: {e}")


@app.get("/")
def read_root():
    return {"message": "Wildberries Content Manager API"}