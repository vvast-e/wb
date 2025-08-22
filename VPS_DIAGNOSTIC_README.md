# 🔧 ДИАГНОСТИКА VPS СЕРВЕРА ДЛЯ ПАРСЕРА OZON

## 📋 Описание

Создано два диагностических скрипта для выявления проблем с парсером Ozon на VPS сервере:

1. **`vps_diagnostic.py`** - Полная диагностика всех компонентов
2. **`quick_proxy_test.py`** - Быстрая проверка прокси и Selenium

## 🚀 Как использовать

### Шаг 1: Загрузите файлы на VPS

```bash
# Скопируйте файлы на ваш VPS сервер
scp vps_diagnostic.py user@your-vps-ip:/home/user/
scp quick_proxy_test.py user@your-vps-ip:/home/user/
```

### Шаг 2: Установите зависимости

```bash
# Подключитесь к VPS
ssh user@your-vps-ip

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите необходимые пакеты
sudo apt install curl wget unzip -y

# Установите Python зависимости
pip install psutil selenium selenium-wire undetected-chromedriver beautifulsoup4 lxml aiohttp
```

### Шаг 3: Установите Chrome и ChromeDriver

```bash
# Установка Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install google-chrome-stable -y

# Установка ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | awk -F'.' '{print $1}')
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}/chromedriver_linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver

# Проверка установки
google-chrome --version
chromedriver --version
```

### Шаг 4: Настройте переменные окружения

```bash
# Создайте .env файл
cat > .env << EOF
OZON_PROXY_HOST=p15184.ltespace.net
OZON_PROXY_PORT=15184
OZON_PROXY_USERNAME=uek7t66y
OZON_PROXY_PASSWORD=zbygddap
OZON_PROXY_SCHEME=http
EOF

# Загрузите переменные
export $(cat .env | xargs)
```

### Шаг 5: Запустите диагностику

#### Быстрая проверка прокси:
```bash
python3 quick_proxy_test.py
```

#### Полная диагностика:
```bash
python3 vps_diagnostic.py
```

## 🔍 Что проверяют скрипты

### `quick_proxy_test.py`:
- ✅ Доступность прокси `ltespace.net`
- ✅ Проверка IP через прокси
- ✅ Доступность Ozon через прокси
- ✅ Простой тест Selenium

### `vps_diagnostic.py`:
- ✅ Системная информация (OS, Python, архитектура)
- ✅ Системные ресурсы (CPU, RAM, диск, swap)
- ✅ Python пакеты (selenium, selenium-wire, undetected-chromedriver)
- ✅ Chrome браузер и ChromeDriver
- ✅ Прокси соединение
- ✅ Сетевое соединение (DNS, ping)
- ✅ Тесты Selenium и Undetected ChromeDriver

## 📊 Интерпретация результатов

### ✅ УСПЕШНО:
- Все проверки прошли
- VPS готов к работе с парсером Ozon

### ⚠️ ПРЕДУПРЕЖДЕНИЯ:
- Некоторые компоненты работают не оптимально
- Рекомендуется исправить для стабильной работы

### ❌ ОШИБКИ:
- Критические проблемы, которые нужно исправить
- Парсер не будет работать до устранения

## 🔧 Частые проблемы и решения

### 1. Chrome не запускается
```bash
# Добавьте в Chrome options:
--no-sandbox --disable-dev-shm-usage --disable-gpu
```

### 2. Недостаточно памяти
```bash
# Создайте swap файл
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 3. Прокси недоступен
```bash
# Проверьте настройки прокси
curl -x http://user:pass@proxy:port https://ifconfig.me

# Проверьте firewall
sudo ufw status
sudo ufw allow out 15184
```

### 4. Selenium ошибки
```bash
# Установите зависимости
sudo apt install -y xvfb libgconf-2-4

# Используйте virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
```

## 📞 Поддержка

Если диагностика показала ошибки, которые вы не можете исправить:

1. **Скопируйте полный вывод** диагностики
2. **Укажите версию OS** и Python
3. **Опишите, что именно не работает**

## 🎯 Следующие шаги

После успешной диагностики:

1. **Адаптируйте существующий парсер** для отзывов
2. **Протестируйте на простых задачах**
3. **Настройте мониторинг** и логирование
4. **Запустите в продакшене**

---

**Удачи с парсером Ozon! 🚀**



