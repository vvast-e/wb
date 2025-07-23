import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pytz
import concurrent.futures

from database import AsyncSessionLocal
from crud.shop import (
    create_shop, get_shops_by_user, get_shop_by_id, 
    add_price_history, get_price_history_by_nmid, get_latest_price
)
from crud.user import get_user_by_email
from models.user import User
from utils.wb_price_parser import WBPriceParser, fetch_wb_price_history, fetch_wb_current_price
from utils.ozon_selenium_parser import get_ozon_products_and_prices_seleniumwire
from utils.ozon_api import fetch_offer_ids_and_skus_from_ozon, fetch_prices_v5_by_offer_ids
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

# Словарь для хранения задач парсинга по пользователям
user_parsing_tasks = {}
# Словарь для хранения событий остановки парсера по пользователям
user_stop_events = {}

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
        user_id = update.effective_user.id if update.effective_user else (update.message.from_user.id if update.message else None)
        keyboard = [
            [InlineKeyboardButton("📊 История цен", callback_data="price_history")],
            [InlineKeyboardButton("💵 Текущая цена", callback_data="current_price")]
        ]
        if user_parsing_tasks.get((user_id, "wb")):
            keyboard.append([InlineKeyboardButton("⏹ Остановить парсер WB", callback_data="stop_wb")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Запустить парсер WB", callback_data="start_wb")])
        if user_parsing_tasks.get((user_id, "ozon")):
            keyboard.append([InlineKeyboardButton("⏹ Остановить парсер Ozon", callback_data="stop_ozon")])
        else:
            keyboard.append([InlineKeyboardButton("▶️ Запустить парсер Ozon", callback_data="start_ozon")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        reply_keyboard = [[KeyboardButton("📋 Меню")]]
        reply_markup_bottom = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
        if update.message:
            await update.message.reply_text(
                "👋 Добро пожаловать в бота мониторинга цен Wildberries и Ozon!\n\n"
                "Выберите действие:",
                reply_markup=reply_markup
            )
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="💡 Нажмите кнопку 'Меню' ниже для быстрого доступа",
                reply_markup=reply_markup_bottom
            )
        elif update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "👋 Добро пожаловать в бота мониторинга цен Wildberries и Ozon!\n\n"
                    "Выберите действие:",
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    await update.callback_query.answer()
                else:
                    logger.error(f"Ошибка при показе главного меню: {e}")
                    await update.callback_query.answer("Произошла ошибка при обновлении меню")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id
        if query.data == "change_market":
            await self.show_main_menu(update, context)
            return
        if query.data == "start_wb":
            await self.start_wb_parser(update, context, user_id)
            return
        if query.data == "stop_wb":
            await self.stop_wb_parser(update, context, user_id)
            return
        if query.data == "start_ozon":
            await self.start_ozon_parser(update, context, user_id)
            return
        if query.data == "stop_ozon":
            await self.stop_ozon_parser(update, context, user_id)
            return
        if query.data == "price_history":
            await self.show_suppliers_menu(update, context)
        elif query.data == "current_price":
            await self.show_suppliers_menu(update, context, current_price=True)
        elif query.data == "back_to_main":
            await self.show_main_menu(update, context)
        elif query.data == "show_menu":
            await self.show_main_menu(update, context)
        elif query.data.startswith("supplier_"):
            parts = query.data.split("_")
            supplier_id = int(parts[1])
            if "page" in parts:
                page = 1
                current_price = "current" in parts
                try:
                    page_index = parts.index("page")
                    if page_index + 1 < len(parts):
                        page = int(parts[page_index + 1])
                except Exception:
                    page = 1
                await self.show_supplier_products(update, context, supplier_id, page, current_price=current_price)
            elif "back" in parts:
                current_price = "current" in parts
                await self.show_suppliers_menu(update, context, current_price=current_price)
            else:
                current_price = "current" in parts
                await self.show_supplier_products(update, context, supplier_id, 1, current_price=current_price)
        elif query.data.startswith("product_"):
            parts = query.data.split("_")
            nm_id = parts[1]  # nm_id теперь всегда строка
            supplier_id = int(parts[2])
            if len(parts) > 3 and parts[3] == "current":
                await self.show_product_current_price(update, context, nm_id, supplier_id)
            else:
                await self.show_product_history(update, context, nm_id, supplier_id)

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
                await update.callback_query.answer()
            else:
                logger.error(f"Ошибка при показе меню магазинов: {e}")
                await update.callback_query.answer("Произошла ошибка при обновлении меню")

    async def show_supplier_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE, supplier_id: int, page: int = 1, current_price: bool = False):
        user_id = update.effective_user.id
        market = user_context.get(user_id, {}).get("market", "wb")
        try:
            if supplier_id == 975642:  # OZON
                async with AsyncSessionLocal() as db:
                    from models.product import Product
                    from sqlalchemy import select
                    result = await db.execute(select(Product).where(Product.brand == '11i Professional OZON'))
                    products = result.scalars().all()
                    nm_ids = [p.nm_id for p in products]
            else:
                nm_ids = await self.parser.get_products_by_supplier_id(supplier_id)
            if not nm_ids:
                context_type = user_context.get(user_id, {}).get("context", "history")
                back_callback = f"supplier_{supplier_id}_back{'_current' if context_type == 'current_price' else ''}"
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=back_callback)]]
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
                    result = await db.execute(select(Product).where(Product.nm_id == str(nm_id)))
                    product = result.scalars().first()
                    if supplier_id == 975642 and product and product.vendor_code:
                        display_code = f"{product.vendor_code}"
                    else:
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
            # Кнопка назад возвращает в suppliers_menu выбранного маркетплейса
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.callback_query.edit_message_text(
                    f"Товары магазина {SUPPLIERS.get(supplier_id, supplier_id)} (стр. {page}/{total_pages}):",
                    reply_markup=reply_markup
                )
            except Exception as e:
                if "Message is not modified" in str(e):
                    await update.callback_query.answer()
                else:
                    logger.error(f"Ошибка при показе товаров: {e}")
                    await update.callback_query.answer("Произошла ошибка при обновлении списка товаров")
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении товаров: {str(e)}"
            )

    async def show_product_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE, nm_id: str, supplier_id: int):
        await update.callback_query.edit_message_text("⏳ Загружаем историю цен...")
        user_id = update.effective_user.id
        market = user_context.get(user_id, {}).get("market", "wb")
        try:
            from models.price_change_history import PriceChangeHistory
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                # Для Ozon и WB теперь ищем историю по nm_id (SKU)
                result = await db.execute(
                    select(PriceChangeHistory)
                    .where(PriceChangeHistory.nm_id == nm_id, PriceChangeHistory.shop_id == supplier_id)
                    .order_by(PriceChangeHistory.created_at.asc())
                )
                changes = result.scalars().all()
            if not changes:
                vendor_code = await self.get_vendor_code_by_nm_id(None, nm_id, supplier_id)
                display_code = vendor_code or nm_id
                context_type = user_context.get(user_id, {}).get("context", "history")
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_main")]]
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
                if 'date' in data:
                    try:
                        date_obj = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                        moscow_time = date_obj.astimezone(moscow_tz)
                        date_str = moscow_time.strftime('%d.%m.%Y %H:%M')
                    except:
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
            vendor_code = await self.get_vendor_code_by_nm_id(None, nm_id, supplier_id)
            display_code = vendor_code or nm_id
            history_text = f"📊 История изменений товара {display_code}:\n\n" + "\n".join(lines[::-1])
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_main")]]
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

    async def get_vendor_code_by_nm_id(self, db, nm_id: str, shop_id: int) -> Optional[str]:
        try:
            from models.product import Product
            from sqlalchemy import select
            if db is None:
                async with AsyncSessionLocal() as db_session:
                    if shop_id == 975642:
                        # Для Ozon nm_id — это sku, ищем по nm_id → vendor_code
                        result = await db_session.execute(select(Product).where(Product.nm_id == str(nm_id)))
                        product = result.scalars().first()
                        return product.vendor_code if product else None
                    else:
                        result = await db_session.execute(select(Product).where(Product.nm_id == str(nm_id)))
                        product = result.scalars().first()
                        return product.vendor_code if product else None
            else:
                if shop_id == 975642:
                    result = await db.execute(select(Product).where(Product.nm_id == str(nm_id)))
                    product = result.scalars().first()
                    return product.vendor_code if product else None
                else:
                    result = await db.execute(select(Product).where(Product.nm_id == str(nm_id)))
                    product = result.scalars().first()
                    return product.vendor_code if product else None
        except Exception as e:
            print(f"[Bot] Ошибка поиска vendor_code по nm_id: {e}")
            return None

    async def show_product_current_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE, nm_id: str,
                                         supplier_id: int):
        await update.callback_query.edit_message_text("⏳ Получаем данные о товаре...")
        user_id = update.effective_user.id
        market = user_context.get(user_id, {}).get("market", "wb")
        try:
            async with AsyncSessionLocal() as db:
                from models.shop import PriceHistory
                from models.product import Product
                from sqlalchemy import select
                if supplier_id == 975642:
                    # Для Ozon ищем vendor_code по nm_id, а затем ищем цену по vendor_code
                    result = await db.execute(select(Product).where(Product.nm_id == str(nm_id)))
                    product = result.scalars().first()
                    vendor_code = product.vendor_code if product else None
                    if vendor_code:
                        result = await db.execute(
                            select(PriceHistory).where(
                                PriceHistory.vendor_code == vendor_code,
                                PriceHistory.shop_id == supplier_id
                            ).order_by(PriceHistory.price_date.desc())
                        )
                        latest = result.scalars().first()
                        price = latest.new_price if latest else None
                    else:
                        price = None
                else:
                    # Для WB ищем по nm_id
                    result = await db.execute(
                        select(PriceHistory).where(
                            PriceHistory.nm_id == str(nm_id),
                            PriceHistory.shop_id == supplier_id
                        ).order_by(PriceHistory.price_date.desc())
                    )
                    latest = result.scalars().first()
                    price = latest.new_price if latest else None
                    vendor_code = await self.get_vendor_code_by_nm_id(db, nm_id, supplier_id)

            display_code = vendor_code or nm_id
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if price is None:
                await update.callback_query.edit_message_text(
                    f"Текущая цена для товара {display_code} не найдена.",
                    reply_markup=reply_markup
                )
                return

            price_str = f"{int(price):,}".replace(",", " ")
            text = (f"📦 Товар: {display_code}\n"
                    f"💵 Текущая цена: {price_str} ₽")
            await update.callback_query.edit_message_text(
                text,
                reply_markup=reply_markup
            )
        except Exception as e:
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при получении текущей цены: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_main")]])
            )
    
    async def price_history_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало просмотра истории цен"""
        await self.show_suppliers_menu(update, context)
    
    async def monitor_prices_task(self, context: ContextTypes.DEFAULT_TYPE):
        """Задача мониторинга цен - каждые 30 минут для всех товаров по supplier_id из supplier_ids.py"""
        stop_event_key = context.job.data.get("stop_event_key")
        stop_event = user_stop_events.get(stop_event_key)
        try:
            total_prices = 0
            
            # Мониторинг Wildberries
            async with AsyncSessionLocal() as db:
                for supplier_id, shop_name in SUPPLIERS.items():
                    if stop_event and stop_event.is_set():
                        print(f"[WB Monitor] Остановка по запросу пользователя {stop_event_key}")
                        return
                    try:
                        nm_ids = await self.parser.get_products_by_supplier_id(supplier_id)
                        for nm_id in nm_ids:
                            if stop_event and stop_event.is_set():
                                print(f"[WB Monitor] Остановка по запросу пользователя {stop_event_key}")
                                return
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
                                        PriceHistory.nm_id == str(nm_id),
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
                                    db, str(nm_id), supplier_id, nm_id, int(current_price), old_price, market="wb"
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при мониторинге цены товара {nm_id}: {e}")
                    except Exception as e:
                        logger.error(f"Ошибка при мониторинге магазина {shop_name}: {e}")
            
            # Мониторинг Ozon (если настроен)
            try:
                # Здесь можно добавить мониторинг Ozon магазинов
                # ozon_seller_url = "https://www.ozon.ru/seller/11i-professional-975642/products/"
                # ozon_result = get_all_products_prices(ozon_seller_url, max_products=20)
                # print(f"[Ozon Monitor] {ozon_result}")
                pass
            except Exception as e:
                logger.error(f"Ошибка при мониторинге Ozon: {e}")
            
            print(f"[Monitor] Успешно спарсено текущих цен: {total_prices} (ожидалось 37)")
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга цен: {e}")

    async def send_price_change_notification(self, shop_name: str, vendor_code: str, old_price: int, new_price: int, product_name: str, nm_id: int, context, discount_price: int = None):
        """Отправка уведомления об изменении цены всем пользователям, которые писали /start"""
        try:
            change = new_price - old_price
            change_str = f"{change:+,}".replace(",", " ")
            price_str = f"{new_price:,}".replace(",", " ")
            old_price_str = f"{old_price:,}".replace(",", " ")
            # Определяем ссылку и название магазина для уведомления
            if shop_name.lower().endswith("ozon"):
                url = f"https://www.ozon.ru/product/{nm_id}/"
                shop_display = "11i professional OZON"
            else:
                from supplier_ids import SUPPLIERS
                url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
                shop_display = SUPPLIERS.get(int(shop_name.split()[0]), shop_name) if shop_name.split()[0].isdigit() else shop_name
            message = (
                f"💰 Изменение цены!\n\n"
                f"🏪 Магазин: {shop_display}\n"
                f"📦 Товар: {vendor_code}\n"
                f"🔢 Артикул: {nm_id}\n"
                f"💵 Старая цена: {old_price_str} ₽\n"
                f"💵 Новая цена: {price_str} ₽\n"
            )
            if discount_price is not None and shop_name.lower().endswith("ozon"):
                message += f"💸 Примерная цена со скидкой: {discount_price:,} ₽\n"
            elif discount_price is not None:
                message += f"💸 Цена со скидкой: {discount_price:,} ₽\n"
            message += (
                f"📈 Изменение: {change_str} ₽\n\n"
                f"Ссылка: {url}"
            )
            from models.telegram_user import TelegramUser
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(TelegramUser.telegram_id))
                chat_ids = result.scalars().all()
                batch_size = 25
                delay_between_batches = 1.1
                print(f"[Notification] Отправляем уведомление {len(chat_ids)} пользователям")
                for i in range(0, len(chat_ids), batch_size):
                    batch = chat_ids[i:i + batch_size]
                    tasks = []
                    for chat_id in batch:
                        task = self._send_single_notification(context, chat_id, message)
                        tasks.append(task)
                    await asyncio.gather(*tasks, return_exceptions=True)
                    if i + batch_size < len(chat_ids):
                        await asyncio.sleep(delay_between_batches)
                print(f"[Notification] Уведомление отправлено {len(chat_ids)} пользователям")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")

    async def _send_single_notification(self, context, chat_id, message):
        """Отправка одного уведомления с обработкой ошибок"""
        try:
            await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)
        except Exception as e:
            # Логируем только критические ошибки, не спамим лог
            if "bot was blocked" not in str(e).lower() and "chat not found" not in str(e).lower():
                logger.error(f"Ошибка при отправке уведомления chat_id={chat_id}: {e}")
    
    async def start_wb_parser(self, update, context, user_id):
        if user_parsing_tasks.get((user_id, "wb")):
            await update.callback_query.answer("Парсер WB уже запущен.", show_alert=True)
            return
        # Создаём Event для остановки
        import asyncio
        stop_event = asyncio.Event()
        user_stop_events[(user_id, "wb")] = stop_event
        # Запуск WB-парсера (пример: через job_queue)
        job = context.job_queue.run_repeating(self.monitor_prices_task, interval=900, first=1, name=f"wb_{user_id}", data={"user_id": user_id, "market": "wb", "stop_event_key": (user_id, "wb")})
        user_parsing_tasks[(user_id, "wb")] = job
        await update.callback_query.answer("Парсер WB запущен!", show_alert=True)
        await self.show_main_menu(update, context)

    async def stop_wb_parser(self, update, context, user_id):
        # Останавливаем Event
        stop_event = user_stop_events.pop((user_id, "wb"), None)
        if stop_event:
            stop_event.set()
        job = user_parsing_tasks.pop((user_id, "wb"), None)
        if job:
            job.schedule_removal()
            await update.callback_query.answer("Парсер WB остановлен.", show_alert=True)
        else:
            await update.callback_query.answer("Парсер WB не был запущен.", show_alert=True)
        await self.show_main_menu(update, context)

    async def start_ozon_parser(self, update, context, user_id):
        if user_parsing_tasks.get((user_id, "ozon")):
            await update.callback_query.answer("Парсер Ozon уже запущен.", show_alert=True)
            return
        # Создаём Event для остановки
        import asyncio
        stop_event = asyncio.Event()
        user_stop_events[(user_id, "ozon")] = stop_event
        # Запуск Ozon-парсера (через job_queue, отдельная задача)
        job = context.job_queue.run_repeating(self.monitor_ozon_task, interval=900, first=1, name=f"ozon_{user_id}", data={"user_id": user_id, "market": "ozon", "stop_event_key": (user_id, "ozon")})
        user_parsing_tasks[(user_id, "ozon")] = job
        await update.callback_query.answer("Парсер Ozon запущен!", show_alert=True)
        await self.show_main_menu(update, context)

    async def stop_ozon_parser(self, update, context, user_id):
        # Останавливаем Event
        stop_event = user_stop_events.pop((user_id, "ozon"), None)
        if stop_event:
            stop_event.set()
        job = user_parsing_tasks.pop((user_id, "ozon"), None)
        if job:
            job.schedule_removal()
            await update.callback_query.answer("Парсер Ozon остановлен.", show_alert=True)
        else:
            await update.callback_query.answer("Парсер Ozon не был запущен.", show_alert=True)
        await self.show_main_menu(update, context)

    async def monitor_ozon_task(self, context: ContextTypes.DEFAULT_TYPE):
        """Периодическая задача мониторинга Ozon через API"""
        stop_event_key = context.job.data.get("stop_event_key")
        stop_event = user_stop_events.get(stop_event_key)
        OZON_SELLER_ID = 975642
        try:
            total_prices = 0
            from models.shop import PriceHistory
            from crud.shop import add_price_history, save_price_change_history
            from models.product import Product
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                # Получаем все offer_id и sku через API
                offer_sku_list = await fetch_offer_ids_and_skus_from_ozon()
                offer_ids = [item["offer_id"] for item in offer_sku_list]
                offerid_to_sku = {item["offer_id"]: item["sku"] for item in offer_sku_list}

                # Получаем цены по offer_id через API
                items = await fetch_prices_v5_by_offer_ids(offer_ids)

                # Сохраняем полный ответ в файл для отладки
                import json
                with open("ozon_api_prices_response.json", "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)

                for item in items:
                    if stop_event and stop_event.is_set():
                        print(f"[Ozon Monitor] Остановка по запросу пользователя {stop_event_key}")
                        return

                    offer_id = item.get("offer_id")
                    # Строгая проверка: обрабатываем только если offer_id есть в исходном списке и offerid_to_sku
                    if not offer_id or offer_id not in offerid_to_sku:
                        continue
                    sku = offerid_to_sku.get(offer_id)
                    price_data = item.get("price", {})
                    price_regular = price_data.get("marketing_price")
                    # Если цена не указана, пропускаем
                    if not (offer_id and sku and price_regular):
                        continue

                    # Ищем товар в базе по nm_id (sku)
                    result = await db.execute(select(Product).where(Product.nm_id == str(sku)))
                    product_db = result.scalars().first()

                    # Если товара нет в базе, создаем его
                    if not product_db:
                        product_db = Product(
                            nm_id=str(sku),
                            vendor_code=str(offer_id),
                            brand="11i Professional OZON"
                        )
                        db.add(product_db)
                        await db.commit()

                    # Получаем последнюю цену из истории
                    result = await db.execute(
                        select(PriceHistory).where(
                            PriceHistory.vendor_code == str(offer_id),
                            PriceHistory.shop_id == OZON_SELLER_ID,
                            PriceHistory.market == 'ozon'
                        ).order_by(PriceHistory.price_date.desc())
                    )
                    latest_price = result.scalars().first()
                    old_price = latest_price.new_price if latest_price else None

                    # Если цена изменилась - отправляем уведомление
                    if old_price is not None and old_price != int(price_regular):
                        # Цена со скидкой = основная цена - 10.03%
                        discount_price = int(round(int(price_regular) * (1 - 0.1003)))
                        await self.send_price_change_notification(
                            shop_name="11i professional OZON",
                            vendor_code=str(offer_id),
                            old_price=old_price,
                            new_price=int(price_regular),
                            product_name=str(sku),
                            nm_id=sku,
                            context=context,
                            discount_price=discount_price
                        )
                        await save_price_change_history(db, sku, OZON_SELLER_ID, old_price, int(price_regular))

                    # Сохраняем новую цену строго по offer_id (vendor_code) и sku (nm_id)
                    await add_price_history(
                        db,
                        vendor_code=str(offer_id),
                        shop_id=OZON_SELLER_ID,
                        nm_id=str(sku),
                        new_price=int(price_regular),
                        old_price=old_price,
                        market="ozon"
                    )
                    total_prices += 1

            print(f"[Ozon Monitor] Успешно обработано текущих цен: {total_prices}")
        except Exception as e:
            logger.error(f"Ошибка в задаче мониторинга цен Ozon: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Запуск бота"""
        self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Добавляем обработчики
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("menu", self.menu))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        # Удаляем автозапуск мониторинга WB:
        # self.application.job_queue.run_repeating(self.monitor_prices_task, interval=900, first=10)
        
        # Запускаем бота
        self.application.run_polling()


# Создаем экземпляр бота
bot = PriceMonitorBot()

if __name__ == "__main__":
    bot.run() 