from fastapi import FastAPI
from backend.database import engine, Base
from backend.routers import items, history, tasks, auth
from backend.utils.scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware

import asyncio

app = FastAPI()

app.include_router(items.router)
app.include_router(history.router)
app.include_router(auth.router)
app.include_router(tasks.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reputation-ecommerce.ru"],  # URL фронтенда
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