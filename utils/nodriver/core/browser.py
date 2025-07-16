import asyncio
import json
import logging
import subprocess
import time
import platform
import os
from typing import List, Optional
from .connection import Connection
from .tab import Tab

logger = logging.getLogger(__name__)

class Browser:
    """Класс для управления браузером Chrome через CDP"""
    
    def __init__(self, headless: bool = True, port: int = 9222):
        self.headless = headless
        self.port = port
        self.process = None
        self.connection = Connection(port=port)
        self.tabs = []
        
    async def start(self):
        """Запуск браузера Chrome с CDP"""
        try:
            # Определяем путь к Chrome для Windows
            import platform
            import os
            
            chrome_paths = []
            if platform.system() == "Windows":
                # Стандартные пути Chrome на Windows
                program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
                program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
                
                chrome_paths = [
                    os.path.join(program_files, 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(program_files_x86, 'Google\\Chrome\\Application\\chrome.exe'),
                    os.path.join(program_files, 'Google\\Chrome Beta\\Application\\chrome.exe'),
                    os.path.join(program_files_x86, 'Google\\Chrome Beta\\Application\\chrome.exe'),
                    'chrome.exe',  # Если Chrome в PATH
                    'google-chrome.exe'  # Альтернативное имя
                ]
            else:
                # Для Linux/Mac
                chrome_paths = ['google-chrome', 'chrome', 'chromium']
            
            # Ищем Chrome
            chrome_executable = None
            for path in chrome_paths:
                if os.path.exists(path) or self._check_command_exists(path):
                    chrome_executable = path
                    break
            
            if not chrome_executable:
                # Пробуем найти Chrome в реестре Windows
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                        chrome_executable = winreg.QueryValue(key, None)
                        logger.info(f"Chrome найден в реестре: {chrome_executable}")
                except:
                    pass
                
                if not chrome_executable:
                    # Последняя попытка - ищем в PATH
                    try:
                        result = subprocess.run(['where', 'chrome'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            chrome_executable = result.stdout.strip().split('\n')[0]
                            logger.info(f"Chrome найден в PATH: {chrome_executable}")
                    except:
                        pass
                
                if not chrome_executable:
                    raise Exception("Chrome не найден. Установите Google Chrome или добавьте его в PATH.")
            
            # Команда для запуска Chrome с CDP
            cmd = [
                chrome_executable,
                f"--remote-debugging-port={self.port}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-popup-blocking",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",
                "--disable-client-side-phishing-detection",
                "--disable-component-extensions-with-background-pages",
                "--disable-default-apps",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-features=TranslateUI,BlinkGenPropertyTrees",
                "--disable-hang-monitor",
                "--disable-ipc-flooding-protection",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-renderer-backgrounding",
                "--disable-sync",
                "--force-color-profile=srgb",
                "--metrics-recording-only",
                "--no-sandbox",
                "--password-store=basic",
                "--use-mock-keychain",
                "--disable-gpu",
                # "--disable-web-security",
            ]
            
            if self.headless:
                cmd.append("--headless")
            
            # Запуск процесса
            logger.info(f"Запуск Chrome с командой: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Проверяем, что процесс запустился
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise Exception(f"Chrome не запустился. stdout: {stdout.decode()}, stderr: {stderr.decode()}")
            
            # Ожидание запуска и проверка доступности порта
            logger.info("Ожидание запуска Chrome...")
            await asyncio.sleep(8)  # увеличить время ожидания
            
            # Проверяем, что порт доступен
            import socket
            max_attempts = 15
            for attempt in range(max_attempts):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex(('localhost', self.port))
                    sock.close()
                    if result == 0:
                        logger.info(f"Chrome успешно запущен на порту {self.port}")
                        break
                    else:
                        logger.info(f"Попытка {attempt + 1}/{max_attempts}: порт {self.port} еще недоступен")
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Ошибка проверки порта (попытка {attempt + 1}): {e}")
                    await asyncio.sleep(2)
            else:
                # Проверяем, не умер ли процесс
                if self.process and self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    logger.error(f"Chrome завершился с ошибкой. stdout: {stdout.decode()}, stderr: {stderr.decode()}")
                raise Exception(f"Chrome не запустился на порту {self.port} после {max_attempts} попыток")
            
            # Установка соединения
            if await self.connection.connect():
                logger.info("Браузер запущен и готов к работе")
                return True
            else:
                logger.error("Не удалось установить соединение с браузером")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка запуска браузера: {e}")
            return False
    
    async def create_tab(self) -> Optional[Tab]:
        """Создание новой вкладки или использование существующей"""
        try:
            # Сначала попробуем получить существующие вкладки
            logger.info("Получаем существующие таргеты...")
            response = await self.connection.send("Target.getTargets")
            logger.info(f"Ответ Target.getTargets: {response}")
            
            targets = response.get("targetInfos", [])
            logger.info(f"Найдено таргетов: {len(targets)}")
            
            # Ищем существующую страницу
            for target in targets:
                if target.get("type") == "page":
                    target_id = target["targetId"]
                    logger.info(f"Найдена существующая страница: {target_id}")
                    tab = Tab(self.connection, target_id)
                    if await tab.attach():
                        self.tabs.append(tab)
                        logger.info(f"Используем существующую вкладку {target_id}")
                        return tab
            
            # Если нет существующих страниц, создаем новую
            logger.info("Создаем новую вкладку...")
            response = await self.connection.send("Target.createTarget", {
                "url": "about:blank"
            })
            
            logger.info(f"Ответ Target.createTarget: {response}")
            
            target_id = response.get("result", {}).get("targetId")
            if target_id:
                logger.info(f"Получен target_id: {target_id}")
                tab = Tab(self.connection, target_id)
                logger.info("Пытаемся прикрепиться к вкладке...")
                if await tab.attach():
                    self.tabs.append(tab)
                    logger.info(f"Создана вкладка {target_id}")
                    return tab
                else:
                    logger.error("Не удалось прикрепиться к вкладке")
            else:
                logger.error(f"target_id не найден в ответе: {response}")
            
            return None
        except Exception as e:
            logger.error(f"Ошибка создания вкладки: {e}")
            logger.error(f"Тип ошибки: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    async def get_tabs(self) -> List[Tab]:
        """Получение списка всех вкладок"""
        try:
            response = await self.connection.send("Target.getTargets")
            targets = response.get("targetInfos", [])
            
            tabs = []
            for target in targets:
                if target.get("type") == "page":
                    tab = Tab(self.connection, target["targetId"])
                    if await tab.attach():
                        tabs.append(tab)
            
            return tabs
        except Exception as e:
            logger.error(f"Ошибка получения вкладок: {e}")
            return []
    
    async def close_tab(self, tab: Tab):
        """Закрытие вкладки"""
        try:
            await tab.close()
            if tab in self.tabs:
                self.tabs.remove(tab)
            logger.info("Вкладка закрыта")
        except Exception as e:
            logger.error(f"Ошибка закрытия вкладки: {e}")
    
    async def stop(self):
        """Остановка браузера"""
        try:
            # Закрытие всех вкладок
            for tab in self.tabs[:]:
                await self.close_tab(tab)
            
            # Закрытие соединения
            await self.connection.close()
            
            # Завершение процесса
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
            
            logger.info("Браузер остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки браузера: {e}")
    
    async def __aenter__(self):
        """Контекстный менеджер - вход"""
        await self.start()
        return self
    
    def _check_command_exists(self, command: str) -> bool:
        """Проверка существования команды в PATH"""
        try:
            subprocess.run([command, '--version'], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE, 
                         timeout=5)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        await self.stop() 