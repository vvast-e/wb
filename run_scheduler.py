#!/usr/bin/env python3
"""
Скрипт для запуска планировщика с автоматическим мониторингом
- Парсер отзывов: каждые 30 минут
- Анализатор аспектов: каждые 32 минуты (через 2 мин после парсера)
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import pytz

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.scheduler import start_scheduler

# Настройка логирования
def setup_logging():
    """Настройка подробного логирования для планировщика"""
    
    # Создаем папку для логов если её нет
    os.makedirs('logs', exist_ok=True)
    
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Логирование в файл
            logging.FileHandler(
                f'logs/scheduler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
                encoding='utf-8'
            ),
            # Логирование в консоль
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """Главная функция запуска планировщика"""
    logger = setup_logging()
    
    try:
        # Получаем текущее время в московском часовом поясе
        moscow_tz = pytz.timezone('Europe/Moscow')
        current_time = datetime.now(moscow_tz)
        
        logger.info("🚀 ЗАПУСК ПЛАНИРОВЩИКА С АВТОМАТИЧЕСКИМ МОНИТОРИНГОМ")
        logger.info("=" * 70)
        logger.info(f"📅 Дата и время запуска: {current_time.strftime('%d.%m.%Y %H:%M:%S')} (МСК)")
        logger.info(f"🌍 Часовой пояс: {moscow_tz}")
        logger.info("")
        logger.info("📋 НАСТРОЙКИ ПЛАНИРОВЩИКА:")
        logger.info("   📝 Парсер отзывов: каждые 30 минут")
        logger.info("   🤖 Анализатор аспектов: каждые 32 минуты")
        logger.info("   ⚙️  Обработка задач: каждые 5 секунд")
        logger.info("   ⏰ Следующий парсинг: через 30 минут")
        logger.info("   ⏰ Следующий анализ: через 32 минуты")
        logger.info("")
        logger.info("💡 Анализатор запускается через 2 минуты после парсера")
        logger.info("   чтобы парсер успел завершиться и сохранить отзывы")
        logger.info("")
        logger.info("📊 Логи сохраняются в папку logs/")
        logger.info("🔄 Планировщик работает в фоновом режиме")
        logger.info("")
        logger.info("⏹️  Для остановки нажмите Ctrl+C")
        logger.info("=" * 70)
        
        # Запускаем планировщик
        start_scheduler()
        
        # Держим скрипт запущенным
        try:
            # Бесконечный цикл для поддержания работы планировщика
            while True:
                await asyncio.sleep(60)  # Проверяем каждую минуту
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("⏹️  Получен сигнал остановки (Ctrl+C)")
            logger.info("🔄 Останавливаем планировщик...")
            
            # Останавливаем планировщик
            from utils.scheduler import scheduler
            scheduler.shutdown()
            
            logger.info("✅ Планировщик успешно остановлен")
            logger.info(f"📅 Время остановки: {datetime.now(moscow_tz).strftime('%d.%m.%Y %H:%M:%S')} (МСК)")
            
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПЛАНИРОВЩИКА: {e}")
        import traceback
        logger.error(f"Детали ошибки:\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())



















