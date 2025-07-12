import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pytz

from database import AsyncSessionLocal
from crud.shop import (
    create_shop, get_shops_by_user, get_shop_by_id, 
    add_price_history, get_price_history_by_nmid, get_latest_price
)
from crud.user import get_user_by_email
from models.user import User
from utils.wb_price_parser import WBPriceParser, fetch_wb_price_history, fetch_wb_current_price
from config import settings
from supplier_ids import SUPPLIERS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для хранения состояний пользователей
user_states = {}

# Словарь для хранения контекста выбора пользователей
user_context = {}

class PriceMonitorBot:
    def __init__(self):
        self.parser = WBPriceParser()
        self.application = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        # Сохраняем chat_id пользователя Telegram
        telegram_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        async with AsyncSessionLocal() as db:
            from models.telegram_user import TelegramUser
            from sqlalchemy import select
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == telegram_id))
            user = result.scalars().first()
            if not user:
                db.add(TelegramUser(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                ))
                await db.commit()
        await self.show_main_menu(update, context)

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /menu"""
        await self.show_main_menu(update, context)

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        keyboard = [
            [InlineKeyboardButton("📊 История цен", callback_data="price_history")],
            [InlineKeyboardButton("💵 Текущая цена", callback_data="current_price")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Создаем Reply Keyboard для кнопки "Меню" под полем ввода
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        reply_keyboard = [[KeyboardButton("📋 Меню")]]
        reply_markup_bottom = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        if update.message:
            await update.message.reply_text(
                "👋 Добро пожаловать в бота мониторинга цен Wildberries!\n\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )
            # Устанавливаем кнопку "Меню" под полем ввода
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💡 Нажмите кнопку 'Меню' ниже для быстрого доступа",
                reply_markup=reply_markup_bottom
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                "👋 Добро пожаловать в бота мониторинга цен Wildberries!\n\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == "price_history":
            # Сохраняем контекст пользователя
            user_id = update.effective_user.id
            user_context[user_id] = "history"
            await self.show_suppliers_menu(update, context)
        elif query.data == "current_price":
            # Сохраняем контекст пользователя
            user_id = update.effective_user.id
            user_context[user_id] = "current_price"
            await self.show_suppliers_menu(update, context, current_price=True)
        elif query.data.startswith("supplier_"):
            parts = query.data.split("_")
            supplier_id = int(parts[1])
            page = 1
            current_price = False
            
            # Проверяем, есть ли "current" в callback_data
            if "current" in parts:
                current_price = True
            
            # Проверяем, есть ли "page" в callback_data
            if "page" in parts:
                try:
                    page_index = parts.index("page")
                    if page_index + 1 < len(parts):
                        page = int(parts[page_index + 1])
                except Exception:
                    page = 1
            
            await self.show_supplier_products(update, context, supplier_id, page, current_price=current_price)
        elif query.data.startswith("product_"):
            parts = query.data.split("_")
            nm_id = int(parts[1])
            supplier_id = int(parts[2])
            if len(parts) > 3 and parts[3] == "current":
                await self.show_product_current_price(update, context, nm_id, supplier_id)
            else:
                await self.show_product_history(update, context, nm_id, supplier_id)
        elif query.data == "back_to_main":
            # Сбрасываем контекст пользователя
            user_id = update.effective_user.id
            if user_id in user_context:
                del user_context[user_id]
            await self.show_main_menu(update, context)
        elif query.data == "show_menu":
            await self.show_main_menu(update, context)

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text
        if text == "📋 Меню":
            await self.show_main_menu(update, context)
        else:
            # Если пользователь написал что-то другое, показываем подсказку
            await update.message.reply_text(
                "💡 Нажмите кнопку '📋 Меню' ниже или напишите /menu для доступа к функциям бота"
            )

    async def show_suppliers_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, current_price: bool = False):
        keyboard = []
        for supplier_id, name in SUPPLIERS.items():
            if current_price:
                callback = f"supplier_{supplier_id}_current"
            else:
                callback = f"supplier_{supplier_id}"
            keyboard.append([InlineKeyboardButton(f"🏪 {name}", callback_data=callback)])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.callback_query.edit_message_text(
                "Выберите магазин:",
                reply_markup=reply_markup
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                # Если сообщение не изменилось, просто отвечаем на callback
                await update.callback_query.answer()
            else:
                # Если другая ошибка, логируем её
                logger.error(f"Ошибка при показе меню магазинов: {e}")
                await update.callback_query.answer("Произошла ошибка при обновлении меню")

    async def show_supplier_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE, supplier_id: int, page: int = 1, current_price: bool = False):
        try:
            nm_ids = await self.parser.get_products_by_supplier_id(supplier_id)
            if not nm_ids:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="price_history")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.edit_message_text(
                    f"Товары для магазина {SUPPLIERS.get(supplier_id, supplier_id)} не найдены.",
                    reply_markup=reply_markup
                )
                return
            page_size = 10
            total_pages = (len(nm_ids) + page_size - 1) // page_size
            page = max(1, min(page, total_pages))
            start = (page - 1) * page_size
            end = start + page_size
            keyboard = []
            from models.product import Product
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                for nm_id in nm_ids[start:end]:
                    # Получаем vendorCode из базы
                    result = await db.execute(select(Product).where(Product.nm_id == nm_id))
                    product = result.scalars().first()
                    display_code = product.vendor_code if (product and product.vendor_code) else nm_id
                    if current_price:
                        keyboard.append([InlineKeyboardButton(
                            f"📦 Товар {display_code}",
                            callback_data=f"product_{nm_id}_{supplier_id}_current"
                        )])
                    else:
                        keyboard.append([InlineKeyboardButton(
                            f"📦 Товар {display_code}",
                            callback_data=f"product_{nm_id}_{supplier_id}"
                        )])
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"supplier_{supplier_id}_page_{page-1}{'_current' if current_price else ''}"))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton("Следующая ➡️", callback_data=f"supplier_{supplier_id}_page_{page+1}{'_current' if current_price else ''}"))
            if nav_buttons:
                keyboard.append(nav_buttons)
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"supplier_{supplier_id}{'_current' if current_price else ''}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.callback_query.edit_message_text(
                    f"Товары магазина {SUPPLIERS.get(supplier_id, supplier_id)} (стр. {page}/{total_pages}):",
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    # Если сообщение не изменилось, просто отвечаем на callback
                    await update.callback_query.answer()
                else:
                    # Если другая ошибка, логируем её
                    logger.error(f"Ошибка при показе товаров: {e}")
                    await update.callback_query.answer("Произошла ошибка при обновлении списка товаров")
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении товаров: {str(e)}"
            )

    async def show_product_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, nm_id: int, supplier_id: int):
        # Показываем анимацию загрузки
        await update.callback_query.edit_message_text("⏳ Загружаем историю цен...")
        try:
            from models.price_change_history import PriceChangeHistory
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(PriceChangeHistory)
                    .where(PriceChangeHistory.nm_id == nm_id, PriceChangeHistory.shop_id == supplier_id)
                    .order_by(PriceChangeHistory.created_at.asc())
                )
                changes = result.scalars().all()
            if not changes:
                # Получаем vendorCode для отображения
                vendor_code = await self.get_vendor_code_by_nm_id(None, nm_id, supplier_id)
                display_code = vendor_code or nm_id
                
                # Определяем контекст пользователя для кнопки "Назад"
                user_id = update.effective_user.id
                context_type = user_context.get(user_id, "history")
                back_callback = f"supplier_{supplier_id}{'_current' if context_type == 'current_price' else ''}"
                
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=back_callback)]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await update.callback_query.edit_message_text(
                        f"История изменений для товара {display_code} не найдена.",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    if "Message is not modified" in str(e):
                        await update.callback_query.answer()
                    else:
                        logger.error(f"Ошибка при показе истории: {e}")
                        await update.callback_query.answer("Произошла ошибка при обновлении истории")
                return
            
            lines = []
            moscow_tz = pytz.timezone('Europe/Moscow')
            for record in changes:
                data = record.change_data
                # Конвертируем время в московский часовой пояс
                if 'date' in data:
                    try:
                        # Парсим дату из строки и конвертируем в московское время
                        date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                        moscow_time = date_obj.astimezone(moscow_tz)
                        date_str = moscow_time.strftime('%d.%m.%Y %H:%M')
                    except:
                        # Если не удалось распарсить, добавляем +3 часа к UTC
                        try:
                            date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                            moscow_time = date_obj.replace(tzinfo=pytz.UTC).astimezone(moscow_tz)
                            date_str = moscow_time.strftime('%d.%m.%Y %H:%M')
                        except:
                            date_str = data.get("date", "?")
                else:
                    date_str = "?"
                old = data.get("old_price", "—")
                new = data.get("new_price", "—")
                diff = data.get("diff", 0)
                diff_str = f"(▲ {diff})" if diff > 0 else (f"(▼ {abs(diff)})" if diff < 0 else "")
                lines.append(f"{date_str}: {old} → {new} ₽ {diff_str}")
            
            # Получаем vendorCode для отображения
            vendor_code = await self.get_vendor_code_by_nm_id(None, nm_id, supplier_id)
            display_code = vendor_code or nm_id
            history_text = f"📊 История изменений товара {display_code}:\n\n" + "\n".join(lines[::-1])
            
            # Определяем контекст пользователя для кнопки "Назад"
            user_id = update.effective_user.id
            context_type = user_context.get(user_id, "history")
            back_callback = f"supplier_{supplier_id}{'_current' if context_type == 'current_price' else ''}"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=back_callback)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.callback_query.edit_message_text(
                    history_text,
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    await update.callback_query.answer()
                else:
                    logger.error(f"Ошибка при показе истории: {e}")
                    await update.callback_query.answer("Произошла ошибка при обновлении истории")
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении истории изменений: {str(e)}"
            )

    async def get_vendor_code_by_nm_id(self, db, nm_id: int, shop_id: int) -> Optional[str]:
        try:
            from models.product import Product
            from sqlalchemy import select
            if db is None:
                async with AsyncSessionLocal() as db_session:
                    result = await db_session.execute(select(Product).where(Product.nm_id == nm_id))
                    product = result.scalars().first()
                    return product.vendor_code if product else None
            else:
                result = await db.execute(select(Product).where(Product.nm_id == nm_id))
                product = result.scalars().first()
                return product.vendor_code if product else None
        except Exception as e:
            print(f"[Bot] Ошибка поиска vendor_code по nm_id: {e}")
            return None

    async def show_product_current_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE, nm_id: int, supplier_id: int):
        # Показываем анимацию загрузки
        await update.callback_query.edit_message_text("⏳ Получаем данные о товаре...")
        """Показать текущую цену товара"""
        try:
            price, price_wallet = await fetch_wb_current_price(nm_id)
            # Сначала пробуем получить vendorCode из базы
            async with AsyncSessionLocal() as db:
                vendor_code = await self.get_vendor_code_by_nm_id(db, nm_id, supplier_id)
            # Если не нашли — пробуем из WB API
            if not vendor_code:
                product_data = await self.parser.get_product_details(nm_id)
                vendor_code = product_data.get("vendorCode") if product_data else None
            display_code = vendor_code or nm_id
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"supplier_{supplier_id}_current")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if price is None:
                # Пробуем взять последнюю цену из базы
                from models.shop import PriceHistory
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(PriceHistory).where(
                            PriceHistory.nm_id == nm_id,
                            PriceHistory.shop_id == supplier_id
                        ).order_by(PriceHistory.price_date.desc())
                    )
                    latest = result.scalars().first()
                    if latest:
                        price = latest.new_price / 100
                        price_wallet = int(price * 0.98)
                        price_str = f"{int(price):,}".replace(",", " ")
                        price_wallet_str = f"{price_wallet}".replace(",", " ")
                        text = f"📦 Товар: {display_code}\n💵 Текущая цена (по данным мониторинга): {price_str} ₽\n💳 С WB кошельком: {price_wallet_str} ₽"
                        try:
                            await update.callback_query.edit_message_text(
                                text,
                                reply_markup=reply_markup
                            )
                        except Exception as e:
                            if "Message is not modified" in str(e):
                                await update.callback_query.answer()
                            else:
                                logger.error(f"Ошибка при показе текущей цены: {e}")
                                await update.callback_query.answer("Произошла ошибка при обновлении цены")
                        return
                try:
                    await update.callback_query.edit_message_text(
                        f"Текущая цена для товара {display_code} не найдена.",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    if "Message is not modified" in str(e):
                        await update.callback_query.answer()
                    else:
                        logger.error(f"Ошибка при показе текущей цены: {e}")
                        await update.callback_query.answer("Произошла ошибка при обновлении цены")
                return
            price_str = f"{int(price):,}".replace(",", " ")
            price_wallet_str = f"{price_wallet}".replace(",", " ")
            text = f"📦 Товар: {display_code}\n💵 Текущая цена: {price_str} ₽\n💳 С WB кошельком: {price_wallet_str} ₽"
            try:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    await update.callback_query.answer()
                else:
                    logger.error(f"Ошибка при показе текущей цены: {e}")
                    await update.callback_query.answer("Произошла ошибка при обновлении цены")
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении текущей цены: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"supplier_{supplier_id}_current")]])
            )
    
    async def price_history_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало просмотра истории цен"""
        await self.show_suppliers_menu(update, context)
    
    async def monitor_prices_task(self, context: ContextTypes.DEFAULT_TYPE):
        """Задача мониторинга цен - каждые 30 минут для всех товаров по supplier_id из supplier_ids.py"""
        try:
            total_prices = 0
            async with AsyncSessionLocal() as db:
                for supplier_id, shop_name in SUPPLIERS.items():
                    try:
                        nm_ids = await self.parser.get_products_by_supplier_id(supplier_id)
                        for nm_id in nm_ids:
                            try:
                                # Получаем текущую цену с WB
                                current_price, _ = await fetch_wb_current_price(nm_id)
                                if current_price is None:
                                    continue
                                total_prices += 1
                                
                                # Получаем vendorCode для логирования
                                vendor_code = await self.get_vendor_code_by_nm_id(db, nm_id, supplier_id)
                                display_code = vendor_code or str(nm_id)
                                
                                # Логируем спарсенную цену
                                print(f"[Price] {shop_name} | {display_code} | {int(current_price)} ₽")
                                
                                # Получаем последнюю цену из базы
                                from models.shop import PriceHistory
                                result = await db.execute(
                                    select(PriceHistory).where(
                                        PriceHistory.nm_id == nm_id,
                                        PriceHistory.shop_id == supplier_id
                                    ).order_by(PriceHistory.price_date.desc())
                                )
                                latest_price = result.scalars().first()
                                old_price = latest_price.new_price if latest_price else None
                                # Если цена изменилась — уведомляем и сохраняем
                                if old_price is not None and old_price != int(current_price):
                                    await self.send_price_change_notification(
                                        shop_name, display_code, old_price, int(current_price), display_code, nm_id, context
                                    )
                                    # Сохраняем изменение в отдельную таблицу истории изменений
                                    from crud.shop import save_price_change_history
                                    await save_price_change_history(db, nm_id, supplier_id, old_price, int(current_price))
                                # Сохраняем новую цену
                                from crud.shop import add_price_history
                                await add_price_history(
                                    db, str(nm_id), supplier_id, nm_id, int(current_price), old_price
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при мониторинге цены товара {nm_id}: {e}")
                    except Exception as e:
                        logger.error(f"Ошибка при мониторинге магазина {shop_name}: {e}")
            print(f"[Monitor] Успешно спарсено текущих цен: {total_prices} (ожидалось 37)")
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга цен: {e}")

    async def send_price_change_notification(self, shop_name: str, vendor_code: str, old_price: int, new_price: int, product_name: str, nm_id: int, context):
        """Отправка уведомления об изменении цены всем пользователям, которые писали /start"""
        try:
            change = new_price - old_price
            change_str = f"{change:+,}".replace(",", " ")
            price_str = f"{new_price:,}".replace(",", " ")
            old_price_str = f"{old_price:,}".replace(",", " ")
            message = (
                f"💰 Изменение цены!\n\n"
                f"🏪 Магазин: {shop_name}\n"
                f"📦 Товар: {vendor_code}\n"
                f"🔢 Артикул: {nm_id}\n"
                f"💵 Старая цена: {old_price_str} ₽\n"
                f"💵 Новая цена: {price_str} ₽\n"
                f"📈 Изменение: {change_str} ₽\n\n"
                f"🔗 Ссылка: https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
            )
            from models.telegram_user import TelegramUser
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(TelegramUser.telegram_id))
                chat_ids = result.scalars().all()
                
                # Оптимизированная отправка с задержками
                batch_size = 25  # Отправляем по 25 сообщений за раз
                delay_between_batches = 1.1  # Задержка 1.1 секунды между батчами (лимит 30/сек)
                
                print(f"[Notification] Отправляем уведомление {len(chat_ids)} пользователям")
                
                for i in range(0, len(chat_ids), batch_size):
                    batch = chat_ids[i:i + batch_size]
                    tasks = []
                    
                    for chat_id in batch:
                        task = self._send_single_notification(context, chat_id, message)
                        tasks.append(task)
                    
                    # Отправляем батч параллельно
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Задержка между батчами (если есть следующий батч)
                    if i + batch_size < len(chat_ids):
                        await asyncio.sleep(delay_between_batches)
                
                print(f"[Notification] Уведомление отправлено {len(chat_ids)} пользователям")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")

    async def _send_single_notification(self, context, chat_id, message):
        """Отправка одного уведомления с обработкой ошибок"""
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            # Логируем только критические ошибки, не спамим лог
            if "bot was blocked" not in str(e).lower() and "chat not found" not in str(e).lower():
                logger.error(f"Ошибка при отправке уведомления chat_id={chat_id}: {e}")
    
    def run(self):
        """Запуск бота"""
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("menu", self.menu))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Добавляем задачу мониторинга в JobQueue (каждые 15 минут)
        self.application.job_queue.run_repeating(self.monitor_prices_task, interval=900, first=10)
        
        # Запускаем бота
        self.application.run_polling()


# Создаем экземпляр бота
bot = PriceMonitorBot()

if __name__ == "__main__":
    bot.run() 