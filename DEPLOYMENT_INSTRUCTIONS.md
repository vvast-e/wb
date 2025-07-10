# Инструкции по развертыванию Telegram бота

## 1. Подготовка к развертыванию

### Создание Telegram бота
1. Напишите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Сохраните полученный токен

### Обновление переменных окружения
Добавьте в файл `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## 2. Установка зависимостей

```bash
# Установка python-telegram-bot
pip install python-telegram-bot~=20.8

# Или обновите requirements.txt и установите все зависимости
pip install -r requirements.txt
```

## 3. Настройка базы данных

### Применение миграций
```bash
# Применение миграций для новых таблиц
alembic upgrade head
```

### Проверка таблиц
Убедитесь, что созданы таблицы:
- `shops` - магазины пользователей
- `price_history` - история цен товаров

## 4. Развертывание на VPS

### Копирование файлов
```bash
# Скопируйте файлы на сервер
scp -r . user@your-server:/var/www/wb_api/

# Или используйте git
git pull origin main
```

### Настройка systemd сервиса
```bash
# Скопируйте файл сервиса
sudo cp telegram-bot.service /etc/systemd/system/

# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable telegram-bot

# Запустите сервис
sudo systemctl start telegram-bot

# Проверьте статус
sudo systemctl status telegram-bot
```

### Просмотр логов
```bash
# Просмотр логов в реальном времени
sudo journalctl -u telegram-bot -f

# Просмотр последних логов
sudo journalctl -u telegram-bot -n 50
```

## 5. Проверка работы

### Тестирование бота
1. Найдите бота в Telegram по имени
2. Отправьте команду `/start`
3. Проверьте работу всех функций

### Проверка мониторинга цен
```bash
# Проверьте логи на наличие мониторинга
sudo journalctl -u telegram-bot | grep "мониторинг"

# Проверьте таблицы в БД
psql -d your_database -c "SELECT * FROM shops LIMIT 5;"
psql -d your_database -c "SELECT * FROM price_history LIMIT 5;"
```

## 6. Управление сервисом

### Команды управления
```bash
# Запуск
sudo systemctl start telegram-bot

# Остановка
sudo systemctl stop telegram-bot

# Перезапуск
sudo systemctl restart telegram-bot

# Статус
sudo systemctl status telegram-bot

# Включение автозапуска
sudo systemctl enable telegram-bot

# Отключение автозапуска
sudo systemctl disable telegram-bot
```

## 7. Мониторинг и логирование

### Настройка ротации логов
Создайте файл `/etc/logrotate.d/telegram-bot`:
```
/var/log/telegram-bot.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 www-data www-data
}
```

### Проверка работы мониторинга
Бот будет:
- Проверять цены каждые 30 минут
- Отправлять уведомления при изменении цен
- Сохранять историю цен в БД

## 8. Устранение неполадок

### Частые проблемы

1. **Бот не запускается**
   ```bash
   # Проверьте токен
   sudo journalctl -u telegram-bot -n 20
   
   # Проверьте права доступа
   sudo chown -R www-data:www-data /var/www/wb_api
   ```

2. **Ошибки подключения к БД**
   ```bash
   # Проверьте настройки БД
   sudo journalctl -u telegram-bot | grep "database"
   ```

3. **Проблемы с мониторингом цен**
   ```bash
   # Проверьте логи парсера
   sudo journalctl -u telegram-bot | grep "price"
   ```

### Отладка
```bash
# Запуск в режиме отладки
sudo systemctl stop telegram-bot
cd /var/www/wb_api
source .venv/bin/activate
python run_telegram_bot.py
```

## 9. Обновление

### Обновление кода
```bash
# Остановите сервис
sudo systemctl stop telegram-bot

# Обновите код
git pull origin main

# Примените миграции (если есть)
alembic upgrade head

# Запустите сервис
sudo systemctl start telegram-bot
```

### Обновление зависимостей
```bash
# Обновите зависимости
pip install -r requirements.txt

# Перезапустите сервис
sudo systemctl restart telegram-bot
```

## 10. Безопасность

### Рекомендации
1. Используйте отдельного пользователя для бота
2. Ограничьте права доступа к файлам
3. Регулярно обновляйте зависимости
4. Мониторьте логи на подозрительную активность

### Настройка firewall
```bash
# Разрешите только необходимые порты
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
``` 