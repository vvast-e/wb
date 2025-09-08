## Развертывание проекта (Backend + Frontend через Nginx) и Telegram-бота на VPS

Ниже универсальные инструкции для Ubuntu 22.04/24.04. Настраиваются:
- Nginx (reverse proxy) с автоматическим SSL (Let's Encrypt)
- systemd-сервисы для backend и Telegram-бота
- PostgreSQL (создание БД и пользователя)
- Базовые firewall-правила и пакеты

Директория `deploy/` содержит шаблоны и скрипты. Все переменные отмечены ЗАГЛАВНЫМИ словами — замените на ваши значения перед запуском.

### 0) Предусловия
- Домен `YOUR_DOMAIN` указывает на IP вашего VPS (A-запись). Если нужен поддомен для API — укажите `API_DOMAIN`, иначе используйте один домен и маршрут `/api/`.
- Пользователь с sudo на VPS.

### 1) Подключение к серверу и базовая установка
Скопируйте проект на сервер (git clone или `scp -r`). По умолчанию далее используются пути:
- Backend: `/opt/wb_api`
- Bot: `/opt/wb_bot`
- Frontend build (статические файлы): `/var/www/wb_frontend`

Выполните на сервере:
```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install bash coreutils curl gnupg lsb-release
cd /opt && sudo mkdir -p wb_api wb_bot && sudo chown -R "$USER":"$USER" wb_api wb_bot
# Скопируйте/клоньте ваш код в эти директории (wb_api — backend, wb_bot — бот)
```

Установите базовые пакеты (nginx, certbot, python, postgresql, ufw):
```bash
cd /opt/wb_api/deploy
sudo bash ./install_base.sh
```

### 2) PostgreSQL — создание БД и пользователя
Отредактируйте переменные в `deploy/setup_postgres.sh` или передайте их через среду. Затем выполните:
```bash
sudo DB_NAME=wb_db DB_USER=wb_user DB_PASS='CHANGE_ME' bash ./setup_postgres.sh
```

Сохраните доступы в `.env`:
```bash
cp deploy/.env.backend.example /opt/wb_api/.env
cp deploy/.env.bot.example /opt/wb_bot/.env
# Отредактируйте значения: домены, пути, креды БД, токены, APP_MODULE и т.д.
```

### 3) Backend — виртуальное окружение, зависимости и сервис
Скрипт настраивает venv, устанавливает зависимости и создает systemd сервис `wb-backend.service`.
```bash
cd /opt/wb_api/deploy
sudo bash ./setup_backend.sh
sudo systemctl daemon-reload
sudo systemctl enable wb-backend
sudo systemctl start wb-backend
sudo systemctl status wb-backend --no-pager
```

По умолчанию backend слушает `127.0.0.1:8000` за Nginx.

### 4) Telegram-бот — окружение и сервис
Скрипт создает venv, ставит зависимости и сервис `wb-bot.service`.
```bash
cd /opt/wb_api/deploy
sudo bash ./setup_bot.sh
sudo systemctl daemon-reload
sudo systemctl enable wb-bot
sudo systemctl start wb-bot
sudo systemctl status wb-bot --no-pager
```

### 5) Nginx — конфиг и SSL
Скопируйте и включите конфиг. Выберите режим:
- Один домен, backend по `/api/`, статический фронтенд из `/var/www/wb_frontend`
- Отдельный домен для API (упростит CORS): `api.reputation-ecommerce.ru`

Один домен (фронт+API под `/api/`):
```bash
sudo cp deploy/nginx_site.conf /etc/nginx/sites-available/wb_site
sudo ln -s /etc/nginx/sites-available/wb_site /etc/nginx/sites-enabled/wb_site
sudo nginx -t && sudo systemctl reload nginx
```

Отдельный домен для API:
```bash
sudo cp deploy/nginx_api.conf /etc/nginx/sites-available/wb_api_site
sudo ln -s /etc/nginx/sites-available/wb_api_site /etc/nginx/sites-enabled/wb_api_site
sudo nginx -t && sudo systemctl reload nginx
```

Включите SSL (Let's Encrypt):
```bash
cd /opt/wb_api/deploy
# фронтенд домен(ы)
sudo bash ./enable_ssl.sh reputation-ecommerce.ru
sudo bash ./enable_ssl.sh www.reputation-ecommerce.ru
# api-домен
sudo bash ./enable_ssl.sh api.reputation-ecommerce.ru
```

### 6) Проверка, перезапуски, логи
```bash
sudo systemctl restart wb-backend
sudo systemctl status wb-backend --no-pager
sudo journalctl -u wb-backend -n 200 --no-pager

sudo systemctl restart wb-bot
sudo systemctl status wb-bot --no-pager
sudo journalctl -u wb-bot -n 200 --no-pager

sudo nginx -t && sudo systemctl reload nginx
```

### 7) Переменные окружения
Заполните файлы `.env` в `/opt/wb_api` и `/opt/wb_bot` на основе шаблонов:
- Для backend важно задать: `APP_MODULE` (например, `app.main:app` для FastAPI), `DB_*`, `ALLOWED_ORIGINS` и пр.
- Для бота: токен `BOT_TOKEN`, путь запуска `BOT_ENTRY` (например, `bot/main.py`).

### 8) CORS и связь фронта с бэком
Если фронтенд обслуживается Nginx с того же домена, используйте маршрут `/api/` в `nginx_site.conf`. Если фронт на другом домене, в backend настройте CORS (`ALLOWED_ORIGINS`) и укажите полный адрес API во фронтенде.

### 9) Обновление деплоя
```bash
# Backend
cd /opt/wb_api && git pull || true
source /opt/wb_api/.venv/bin/activate
pip install -U -r requirements.txt
sudo systemctl restart wb-backend

# Bot
cd /opt/wb_bot && git pull || true
source /opt/wb_bot/.venv/bin/activate
pip install -U -r requirements.txt
sudo systemctl restart wb-bot
```

### 10) Примечания
- Если у вас не FastAPI/Starlette, задайте корректный `APP_MODULE` и/или замените запуск на gunicorn/uvicorn по вашему стеку.
- Если бот использует вебхуки — в Nginx добавьте отдельный location и обеспечьте HTTPS на домене вебхука.
- UFW открывает 80/443. SSH-порт добавьте при необходимости.


