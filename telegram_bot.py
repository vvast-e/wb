import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import AsyncSessionLocal
from crud.shop import (
    create_shop, get_shops_by_user, get_shop_by_id, 
    add_price_history, get_price_history_by_vendor, get_latest_price
)
from crud.user import get_user_by_email
from models.user import User
from utils.wb_price_parser import WBPriceParser
from config import settings

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для хранения состояний пользователей
user_states = {}

class PriceMonitorBot:
    def __init__(self):
        self.parser = WBPriceParser()
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = [
            [InlineKeyboardButton("➕ Добавить магазин", callback_data="add_shop")],
            [InlineKeyboardButton("📊 История цен", callback_data="price_history")],
            [InlineKeyboardButton("🔍 Мои магазины", callback_data="my_shops")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            "👋 Добро пожаловать в бота мониторинга цен Wildberries!\n\n"
            "Выберите действие:"
        )
        
        # Проверяем, откуда вызвана функция
        if update.callback_query:
            # Если вызвана из callback (кнопки)
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=reply_markup
            )
        elif update.message:
            # Если вызвана из сообщения (команда /start)
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "add_shop":
            await self.add_shop_start(update, context)
        elif query.data == "price_history":
            await self.price_history_start(update, context)
        elif query.data == "my_shops":
            await self.my_shops(update, context)
        elif query.data.startswith("shop_"):
            shop_id = int(query.data.split("_")[1])
            await self.show_shop_products(update, context, shop_id)
        elif query.data.startswith("product_"):
            parts = query.data.split("_")
            vendor_code = parts[1]
            shop_id = int(parts[2])
            await self.show_product_history(update, context, vendor_code, shop_id)
        elif query.data == "back_to_main":
            await self.start(update, context)
    
    async def add_shop_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления магазина"""
        user_states[update.effective_user.id] = {"state": "waiting_shop_name"}
        
        message_text = (
            "Введите название магазина на Wildberries:\n\n"
            "Пример: '11i professional'"
        )
        
        # Проверяем, откуда вызвана функция
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text)
        elif update.message:
            await update.message.reply_text(message_text)
    
    async def get_user_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[User]:
        """Поиск пользователя по telegram_id"""
        try:
            # Ищем пользователя с admin статусом или первого доступного
            result = await db.execute(select(User).where(User.status == "admin").limit(1))
            user = result.scalars().first()
            
            if not user:
                # Если нет админа, берем первого пользователя
                result = await db.execute(select(User).limit(1))
                user = result.scalars().first()
            
            if not user:
                # Если пользователей нет, создаем первого пользователя для Telegram
                from crud.user import create_user
                from schemas import UserCreate
                
                user_data = UserCreate(
                    email=f"telegram_{telegram_id}@bot.local",
                    password="telegram_bot_password_123"
                )
                user = await create_user(db, user_data)
                logger.info(f"Создан новый пользователь для Telegram ID {telegram_id}")
            else:
                logger.info(f"Найден существующий пользователь ID {user.id} для Telegram ID {telegram_id}")
            
            return user
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя: {e}")
            return None
    
    async def handle_shop_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка введенного названия магазина"""
        user_id = update.effective_user.id
        shop_name = update.message.text.strip()
        
        if user_id not in user_states or user_states[user_id]["state"] != "waiting_shop_name":
            return
        
        try:
            async with AsyncSessionLocal() as db:
                # Находим пользователя по telegram_id
                user = await self.get_user_by_telegram_id(db, user_id)
                if not user:
                    logger.error(f"Не удалось найти или создать пользователя для Telegram ID {user_id}")
                    await update.message.reply_text(
                        "❌ Пользователь не найден. Обратитесь к администратору."
                    )
                    return
                
                logger.info(f"Пользователь найден: ID={user.id}, Email={user.email}")
                
                shop = await create_shop(db, shop_name, shop_name, user.id)
                
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ Магазин '{shop_name}' успешно добавлен!\n\n"
                    f"ID магазина: {shop.id}",
                    reply_markup=reply_markup
                )
                
                del user_states[user_id]
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка при добавлении магазина: {str(e)}"
            )
    
    async def my_shops(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать магазины пользователя"""
        try:
            async with AsyncSessionLocal() as db:
                user = await self.get_user_by_telegram_id(db, update.effective_user.id)
                if not user:
                    logger.error(f"Не удалось найти или создать пользователя для Telegram ID {update.effective_user.id}")
                    await update.callback_query.edit_message_text(
                        "❌ Пользователь не найден. Обратитесь к администратору."
                    )
                    return
                
                logger.info(f"Пользователь найден для my_shops: ID={user.id}, Email={user.email}")
                
                shops = await get_shops_by_user(db, user.id)
                
                if not shops:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.callback_query.edit_message_text(
                        "У вас пока нет добавленных магазинов.",
                        reply_markup=reply_markup
                    )
                    return
                
                keyboard = []
                for shop in shops:
                    keyboard.append([InlineKeyboardButton(
                        f"🏪 {shop.name}", 
                        callback_data=f"shop_{shop.id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    "Выберите магазин для просмотра товаров:",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении магазинов: {str(e)}"
            )
    
    async def show_shop_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE, shop_id: int):
        """Показать товары магазина"""
        try:
            async with AsyncSessionLocal() as db:
                shop = await get_shop_by_id(db, shop_id)
                
                if not shop:
                    await update.callback_query.edit_message_text("Магазин не найден.")
                    return
                
                # Получаем товары магазина используя существующую логику
                user = await self.get_user_by_telegram_id(db, update.effective_user.id)
                if not user:
                    await update.callback_query.edit_message_text("Пользователь не найден.")
                    return
                
                logger.info(f"Получаем товары для магазина '{shop.name}' пользователя {user.id}")
                products = await self.parser.get_products_by_shop(shop.name, user.id, db)
                logger.info(f"Получено товаров: {len(products)}")
                
                if not products:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="my_shops")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.callback_query.edit_message_text(
                        f"Товары для магазина '{shop.name}' не найдены.",
                        reply_markup=reply_markup
                    )
                    return
                
                keyboard = []
                for product in products[:10]:  # Показываем первые 10 товаров
                    price_str = f"{product.get('price', 0):,}".replace(",", " ")
                    product_name = product.get('name', 'Неизвестный товар')
                    product_id = product.get('id', '')
                    
                    keyboard.append([InlineKeyboardButton(
                        f"📦 {product_name[:30]}... ({price_str} ₽)",
                        callback_data=f"product_{product_id}_{shop_id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="my_shops")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    f"Товары магазина '{shop.name}':",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении товаров: {str(e)}"
            )
    
    async def show_product_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 vendor_code: str, shop_id: int):
        """Показать историю цен товара"""
        try:
            async with AsyncSessionLocal() as db:
                price_history = await get_price_history_by_vendor(db, vendor_code, shop_id)
                
                if not price_history:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"shop_{shop_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.callback_query.edit_message_text(
                        f"История цен для товара {vendor_code} не найдена.",
                        reply_markup=reply_markup
                    )
                    return
                
                history_text = f"📊 История цен товара {vendor_code}:\n\n"
                
                for i, price in enumerate(price_history[:10]):  # Показываем последние 10 записей
                    date_str = price.price_date.strftime("%d.%m.%Y %H:%M")
                    price_str = f"{price.new_price:,}".replace(",", " ")
                    
                    if price.old_price:
                        old_price_str = f"{price.old_price:,}".replace(",", " ")
                        change = price.new_price - price.old_price
                        change_str = f"({change:+,})".replace(",", " ")
                        history_text += f"{date_str}: {price_str} ₽ {change_str}\n"
                    else:
                        history_text += f"{date_str}: {price_str} ₽\n"
                
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"shop_{shop_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    history_text,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении истории цен: {str(e)}"
            )
    
    async def price_history_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало просмотра истории цен"""
        await self.my_shops(update, context)
    
    async def monitor_prices_task(self, context: ContextTypes.DEFAULT_TYPE):
        """Задача мониторинга цен - каждые 30 минут"""
        try:
            async with AsyncSessionLocal() as db:
                # Получаем все активные магазины
                from crud.shop import get_all_active_shops
                shops = await get_all_active_shops(db)
                
                for shop in shops:
                    try:
                        # Получаем товары магазина
                        user = await self.get_user_by_telegram_id(db, shop.user_id)
                        if not user:
                            continue
                        
                        products = await self.parser.get_products_by_shop(shop.name, user.id, db)
                        
                        # Проверяем цены для каждого товара
                        for product in products:
                            try:
                                nm_id = int(product['id'])
                                current_price = product.get('price', 0)
                                vendor_code = product.get('vendor_code', '')
                                product_name = product.get('name', '')
                                
                                if current_price and vendor_code:
                                    # Получаем последнюю цену из БД
                                    latest_price = await get_latest_price(db, vendor_code, shop.id)
                                    
                                    if latest_price and latest_price.new_price != current_price:
                                        # Цена изменилась - отправляем уведомление
                                        await self.send_price_change_notification(
                                            shop.user_id, shop.name, vendor_code, 
                                            latest_price.new_price, current_price, product_name, nm_id
                                        )
                                    
                                    # Сохраняем новую цену
                                    await add_price_history(
                                        db, vendor_code, shop.id, nm_id, current_price,
                                        latest_price.new_price if latest_price else None
                                    )
                                    
                            except Exception as e:
                                logger.error(f"Ошибка при проверке цены товара {product['id']}: {e}")
                                
                    except Exception as e:
                        logger.error(f"Ошибка при мониторинге магазина {shop.name}: {e}")
                        
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга цен: {e}")

    async def send_price_change_notification(self, user_id: int, shop_name: str, vendor_code: str, 
                                           old_price: int, new_price: int, product_name: str, nm_id: int):
        """Отправка уведомления об изменении цены"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalars().first()
                if not user:
                    return
                
                # Формируем сообщение
                change = new_price - old_price
                change_str = f"{change:+,}".replace(",", " ")
                price_str = f"{new_price:,}".replace(",", " ")
                old_price_str = f"{old_price:,}".replace(",", " ")
                
                message = (
                    f"💰 Изменение цены!\n\n"
                    f"🏪 Магазин: {shop_name}\n"
                    f"📦 Товар: {product_name}\n"
                    f"🔢 Артикул: {vendor_code}\n"
                    f"💵 Старая цена: {old_price_str} ₽\n"
                    f"💵 Новая цена: {price_str} ₽\n"
                    f"📈 Изменение: {change_str} ₽\n\n"
                    f"🔗 Ссылка: https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
                )
                
                # Отправляем уведомление (нужно реализовать отправку в Telegram)
                # Пока просто логируем
                logger.info(f"Изменение цены: {message}")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
    
    def run(self):
        """Запуск бота"""
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_shop_name))
        
        # Добавляем задачу мониторинга в JobQueue (каждые 30 минут)
        self.application.job_queue.run_repeating(self.monitor_prices_task, interval=1800, first=10)
        
        # Запускаем бота
        self.application.run_polling()


# Создаем экземпляр бота
bot = PriceMonitorBot()

if __name__ == "__main__":
    bot.run() 