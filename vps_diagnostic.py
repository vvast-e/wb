#!/usr/bin/env python3
"""
Диагностический скрипт для VPS сервера
Проверяет все компоненты, необходимые для работы парсера Ozon
"""

import os
import sys
import subprocess
import platform
import psutil
import asyncio
import aiohttp
import time
from datetime import datetime

class VPSDiagnostic:
    """Диагностика VPS сервера для парсера Ozon"""
    
    def __init__(self):
        self.results = {}
        self.errors = []
        self.warnings = []
        
    def print_header(self, title: str):
        """Вывод заголовка"""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print(f"{'='*60}")
    
    def print_result(self, name: str, status: str, details: str = ""):
        """Вывод результата проверки"""
        icon = "✅" if status == "OK" else "❌" if status == "ERROR" else "⚠️"
        print(f"{icon} {name}: {status}")
        if details:
            print(f"   📝 {details}")
        self.results[name] = status
    
    def check_system_info(self):
        """Проверка системной информации"""
        self.print_header("СИСТЕМНАЯ ИНФОРМАЦИЯ")
        
        # OS
        os_info = f"{platform.system()} {platform.release()}"
        self.print_result("Операционная система", "OK", os_info)
        
        # Python
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.print_result("Python версия", "OK", python_version)
        
        # Архитектура
        arch = platform.architecture()[0]
        self.print_result("Архитектура", "OK", arch)
        
        # Время работы
        uptime = time.time() - psutil.boot_time()
        uptime_hours = int(uptime // 3600)
        self.print_result("Время работы сервера", "OK", f"{uptime_hours} часов")
    
    def check_system_resources(self):
        """Проверка системных ресурсов"""
        self.print_header("СИСТЕМНЫЕ РЕСУРСЫ")
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        self.print_result("CPU", "OK", f"{cpu_count} ядер, загрузка: {cpu_percent}%")
        
        # RAM
        memory = psutil.virtual_memory()
        ram_gb = memory.total / (1024**3)
        ram_used_gb = memory.used / (1024**3)
        ram_percent = memory.percent
        self.print_result("RAM", "OK" if ram_percent < 80 else "WARNING", 
                         f"{ram_gb:.1f} GB всего, {ram_used_gb:.1f} GB использовано ({ram_percent}%)")
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_gb = disk.total / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        disk_percent = (disk.used / disk.total) * 100
        self.print_result("Диск", "OK" if disk_percent < 90 else "WARNING",
                         f"{disk_gb:.1f} GB всего, {disk_free_gb:.1f} GB свободно ({disk_percent:.1f}%)")
        
        # Swap
        try:
            swap = psutil.swap_memory()
            if swap.total > 0:
                swap_gb = swap.total / (1024**3)
                swap_used_gb = swap.used / (1024**3)
                self.print_result("Swap", "OK", f"{swap_gb:.1f} GB всего, {swap_used_gb:.1f} GB использовано")
            else:
                self.print_result("Swap", "WARNING", "Не настроен")
        except:
            self.print_result("Swap", "ERROR", "Не удалось проверить")
    
    def check_python_packages(self):
        """Проверка Python пакетов"""
        self.print_header("PYTHON ПАКЕТЫ")
        
        required_packages = [
            'selenium', 'selenium-wire', 'undetected-chromedriver',
            'beautifulsoup4', 'lxml', 'aiohttp', 'psutil'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.print_result(f"Пакет {package}", "OK")
            except ImportError:
                self.print_result(f"Пакет {package}", "ERROR", "Не установлен")
                self.errors.append(f"Пакет {package} не установлен")
    
    def check_chrome_installation(self):
        """Проверка установки Chrome"""
        self.print_header("CHROME БРАУЗЕР")
        
        # Проверяем Chrome
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_result("Google Chrome", "OK", version)
            else:
                self.print_result("Google Chrome", "ERROR", "Не установлен или не работает")
                self.errors.append("Google Chrome не установлен")
        except FileNotFoundError:
            self.print_result("Google Chrome", "ERROR", "Не найден в PATH")
            self.errors.append("Google Chrome не найден в PATH")
        except subprocess.TimeoutExpired:
            self.print_result("Google Chrome", "ERROR", "Таймаут при проверке")
            self.errors.append("Google Chrome таймаут")
    
    def check_chromedriver(self):
        """Проверка ChromeDriver"""
        self.print_header("CHROMEDRIVER")
        
        try:
            result = subprocess.run(['chromedriver', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.print_result("ChromeDriver", "OK", version)
            else:
                self.print_result("ChromeDriver", "ERROR", "Не работает")
                self.errors.append("ChromeDriver не работает")
        except FileNotFoundError:
            self.print_result("ChromeDriver", "ERROR", "Не найден в PATH")
            self.errors.append("ChromeDriver не найден в PATH")
        except subprocess.TimeoutExpired:
            self.print_result("ChromeDriver", "ERROR", "Таймаут при проверке")
            self.errors.append("ChromeDriver таймаут")
    
    def check_proxy_connection(self):
        """Проверка прокси соединения"""
        self.print_header("ПРОВЕРКА ПРОКСИ")
        
        # Ваши настройки прокси
        proxy_host = os.getenv('OZON_PROXY_HOST', 'p15184.ltespace.net')
        proxy_port = os.getenv('OZON_PROXY_PORT', '15184')
        proxy_user = os.getenv('OZON_PROXY_USERNAME', 'uek7t66y')
        proxy_pass = os.getenv('OZON_PROXY_PASSWORD', 'zbygddap')
        
        proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        
        print(f"🔧 Проверяем прокси: {proxy_host}:{proxy_port}")
        print(f"👤 Пользователь: {proxy_user}")
        
        # Проверка через curl
        try:
            result = subprocess.run([
                'curl', '-x', proxy_url, '--connect-timeout', '30',
                '--max-time', '60', 'https://ifconfig.me'
            ], capture_output=True, text=True, timeout=70)
            
            if result.returncode == 0:
                ip = result.stdout.strip()
                self.print_result("Прокси соединение", "OK", f"IP: {ip}")
            else:
                error = result.stderr.strip()
                self.print_result("Прокси соединение", "ERROR", f"Ошибка: {error}")
                self.errors.append(f"Прокси недоступен: {error}")
                
        except FileNotFoundError:
            self.print_result("Прокси проверка", "WARNING", "curl не установлен")
        except subprocess.TimeoutExpired:
            self.print_result("Прокси соединение", "ERROR", "Таймаут соединения")
            self.errors.append("Прокси таймаут")
    
    def check_network_connectivity(self):
        """Проверка сетевого соединения"""
        self.print_header("СЕТЕВОЕ СОЕДИНЕНИЕ")
        
        # Проверка DNS
        try:
            result = subprocess.run(['nslookup', 'www.ozon.ru'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.print_result("DNS резолвинг", "OK", "ozon.ru доступен")
            else:
                self.print_result("DNS резолвинг", "ERROR", "ozon.ru недоступен")
                self.errors.append("DNS не работает")
        except FileNotFoundError:
            self.print_result("DNS проверка", "WARNING", "nslookup не установлен")
        except subprocess.TimeoutExpired:
            self.print_result("DNS резолвинг", "ERROR", "Таймаут")
            self.errors.append("DNS таймаут")
        
        # Проверка ping
        try:
            result = subprocess.run(['ping', '-c', '3', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                self.print_result("Ping Google DNS", "OK", "Сеть доступна")
            else:
                self.print_result("Ping Google DNS", "ERROR", "Сеть недоступна")
                self.errors.append("Сетевое соединение не работает")
        except FileNotFoundError:
            self.print_result("Ping проверка", "WARNING", "ping не установлен")
        except subprocess.TimeoutExpired:
            self.print_result("Ping Google DNS", "ERROR", "Таймаут")
            self.errors.append("Ping таймаут")
    
    def check_selenium_test(self):
        """Тест Selenium"""
        self.print_header("ТЕСТ SELENIUM")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            driver = webdriver.Chrome(options=options)
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()
            
            self.print_result("Selenium тест", "OK", f"Заголовок: {title}")
            
        except Exception as e:
            self.print_result("Selenium тест", "ERROR", str(e))
            self.errors.append(f"Selenium не работает: {e}")
    
    def check_undetected_chromedriver(self):
        """Тест Undetected ChromeDriver"""
        self.print_header("ТЕСТ UNDETECTED CHROMEDRIVER")
        
        try:
            import undetected_chromedriver as uc
            
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = uc.Chrome(options=options)
            driver.get("https://www.google.com")
            title = driver.title
            driver.quit()
            
            self.print_result("Undetected ChromeDriver", "OK", f"Заголовок: {title}")
            
        except Exception as e:
            self.print_result("Undetected ChromeDriver", "ERROR", str(e))
            self.errors.append(f"Undetected ChromeDriver не работает: {e}")
    
    def generate_report(self):
        """Генерация отчета"""
        self.print_header("ИТОГОВЫЙ ОТЧЕТ")
        
        total_checks = len(self.results)
        ok_checks = sum(1 for status in self.results.values() if status == "OK")
        error_checks = sum(1 for status in self.results.values() if status == "ERROR")
        warning_checks = sum(1 for status in self.results.values() if status == "WARNING")
        
        print(f"📊 Всего проверок: {total_checks}")
        print(f"✅ Успешно: {ok_checks}")
        print(f"⚠️ Предупреждения: {warning_checks}")
        print(f"❌ Ошибки: {error_checks}")
        
        if self.errors:
            print(f"\n🔴 КРИТИЧЕСКИЕ ОШИБКИ:")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n🟡 ПРЕДУПРЕЖДЕНИЯ:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors:
            print(f"\n🎉 ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО!")
            print("Ваш VPS готов к работе с парсером Ozon!")
        else:
            print(f"\n🔧 НЕОБХОДИМО ИСПРАВИТЬ:")
            print("1. Установить недостающие пакеты")
            print("2. Настроить Chrome/ChromeDriver")
            print("3. Проверить прокси соединение")
            print("4. Настроить сетевые параметры")
    
    def run_all_checks(self):
        """Запуск всех проверок"""
        print("🚀 ЗАПУСК ДИАГНОСТИКИ VPS СЕРВЕРА")
        print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            self.check_system_info()
            self.check_system_resources()
            self.check_python_packages()
            self.check_chrome_installation()
            self.check_chromedriver()
            self.check_proxy_connection()
            self.check_network_connectivity()
            self.check_selenium_test()
            self.check_undetected_chromedriver()
            
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ДИАГНОСТИКИ: {e}")
            self.errors.append(f"Ошибка диагностики: {e}")
        
        finally:
            self.generate_report()

def main():
    """Главная функция"""
    diagnostic = VPSDiagnostic()
    diagnostic.run_all_checks()

if __name__ == "__main__":
    main()



