import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Явно указываем путь к .env файлу
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class Settings:
    # Обязательные параметры без значений по умолчанию
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key")
    POSTGRES_URL: Optional[str] = os.getenv("POSTGRES_URL")

    # Параметры с значениями по умолчанию
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5760"))
    WB_API_BASE_URL: str = os.getenv("WB_BASE_URL", "https://content-api.wildberries.ru")
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")  # Добавлено для OZON
    
    # Telegram Bot настройки
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL", "")


settings = Settings()