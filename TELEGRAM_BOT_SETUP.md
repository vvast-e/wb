# Настройка и запуск Telegram бота

## 1. Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

## 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Database
POSTGRES_URL=sqlite:///./database.db

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# JWT
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=5760

# Wildberries API
WB_BASE_URL=https://content-api.wildberries.ru

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_WEBHOOK_URL=
```

Замените `your-telegram-bot-token-here` на ваш токен бота.

## 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

## 4. Запуск миграций

```bash
alembic upgrade head
```

## 5. Запуск бота

### Локальный запуск

```bash
python run_telegram_bot.py
```

### Запуск через systemd (для VPS)

1. Скопируйте файл `telegram-bot.service` в `/etc/systemd/system/`
2. Отредактируйте пути в файле сервиса
3. Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 6. Использование бота

### Основные команды:

- `/start` - Главное меню
- Добавление магазинов через кнопки
- Просмотр истории цен
- Мониторинг изменений цен

### Функции:

1. **Добавление магазинов** - пользователи могут добавлять магазины Wildberries для мониторинга
2. **Просмотр товаров** - список товаров в каждом магазине
3. **История цен** - график изменения цен для каждого товара
4. **Уведомления** - автоматические уведомления об изменении цен

## 7. Мониторинг

Бот автоматически проверяет цены каждые 30 минут и отправляет уведомления при изменениях.

### Логи:

- Логи бота: `telegram_bot.log`
- Логи systemd: `sudo journalctl -u telegram-bot -f`

## 8. Устранение неполадок

### Ошибка "Token not found":
- Проверьте, что токен правильно указан в `.env` файле

### Ошибка "Database connection failed":
- Убедитесь, что база данных создана и миграции применены

### Ошибка "User not found":
- Временно бот использует первого пользователя из БД (ID=1)
- Убедитесь, что в базе есть хотя бы один пользователь

### Ошибка "Telegram API conflict":
- Остановите другие экземпляры бота
- Проверьте, что только один процесс использует токен

## 9. Структура базы данных

Бот использует существующие таблицы:
- `users` - пользователи системы
- `shops` - магазины для мониторинга
- `price_history` - история цен товаров

## 10. Безопасность

- Токен бота хранится в `.env` файле (не коммитьте его в git)
- Используйте HTTPS для webhook (если настроен)
- Регулярно обновляйте зависимости 