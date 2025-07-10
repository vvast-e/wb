from fastapi import FastAPI
from sqlalchemy import select

from database import engine, Base, AsyncSessionLocal
from routers import items, auth, tasks, admin, history, feedbacks, analytics, product_reviews, shops
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
app.include_router(shops.router)
app.include_router(shops_summary_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reputation-ecommerce.ru",
                   "http://localhost:3000"],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    start_scheduler()


@app.get("/")
def read_root():
    return {"message": "Wildberries Content Manager API"}