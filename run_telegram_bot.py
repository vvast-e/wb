#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота мониторинга цен Wildberries
"""

import asyncio
import logging
import sys
from telegram_bot import PriceMonitorBot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Главная функция запуска бота"""
    try:
        logger.info("Запуск Telegram бота мониторинга цен...")
        
        # Создаем и запускаем бота
        bot = PriceMonitorBot()
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 