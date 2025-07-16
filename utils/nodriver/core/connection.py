import asyncio
import json
import logging

from typing import Dict, Any, Optional



logger = logging.getLogger(__name__)

class Connection:
    """Базовый класс для соединения с Chrome DevTools Protocol"""
    
    def __init__(self, host: str = "localhost", port: int = 9222):
        self.host = host
        self.port = port
        self.websocket = None
        self.message_id = 0
        
    async def connect(self):
        """Установка соединения с CDP"""
        try:
            # Сначала получаем список таргетов через HTTP API
            import aiohttp
            import websockets
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://{self.host}:{self.port}/json') as resp:
                    if resp.status != 200:
                        logger.error(f"Не удалось получить список таргетов: HTTP {resp.status}")
                        return False
                    
                    targets = await resp.json()
                    logger.info(f"Получено {len(targets)} таргетов")
                    
                    # Ищем страницу для подключения
                    page_target = None
                    for target in targets:
                        if target.get('type') == 'page':
                            page_target = target
                            break
                    
                    if not page_target:
                        logger.error("Не найдена страница для подключения")
                        return False
                    
                    # Подключаемся к WebSocket таргета
                    ws_url = page_target.get('webSocketDebuggerUrl')
                    if not ws_url:
                        logger.error("WebSocket URL не найден в таргете")
                        logger.error(f"Таргет: {page_target}")
                        return False
                    
                    logger.info(f"Подключение к WebSocket: {ws_url}")
                    try:
                        self.websocket = await websockets.connect(ws_url)
                        logger.info(f"WebSocket соединение установлено")
                        return True
                    except Exception as e:
                        logger.error(f"Ошибка подключения к WebSocket: {e}")
                        return False
                    
        except Exception as e:
            logger.error(f"Ошибка соединения: {e}")
            return False
    
    async def send(self, method: str, params: Dict[str, Any] = None, session_id: str = None) -> Dict[str, Any]:
        """Отправка команды в CDP"""
        if not self.websocket:
            raise Exception("Соединение не установлено")
        
        self.message_id += 1
        message = {
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }
        
        if session_id:
            message["sessionId"] = session_id
        
        await self.websocket.send(json.dumps(message))
        
        # Ждем ответа с правильным ID
        while True:
            response = await self.websocket.recv()
            response_data = json.loads(response)
            
            # Проверяем, что это ответ на нашу команду
            if response_data.get("id") == self.message_id:
                return response_data
            
            # Если это событие, логируем и продолжаем ждать
            if "method" in response_data:
                logger.debug(f"Получено событие: {response_data['method']}")
                continue
    
    async def close(self):
        """Закрытие соединения"""
        if self.websocket:
            await self.websocket.close()
            logger.info("Соединение закрыто") 