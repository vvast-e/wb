import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class Tab:
    """Класс для управления вкладкой браузера"""
    
    def __init__(self, connection, target_id: str):
        self.connection = connection
        self.target_id = target_id
        self.session_id = None
        
    async def attach(self):
        """Присоединение к вкладке"""
        try:
            logger.info(f"Прикрепляемся к target_id: {self.target_id}")
            response = await self.connection.send("Target.attachToTarget", {
                "targetId": self.target_id,
                "flatten": True
            })
            
            logger.info(f"Ответ Target.attachToTarget: {response}")
            
            self.session_id = response.get("result", {}).get("sessionId")
            if self.session_id:
                logger.info(f"Получен session_id: {self.session_id}")
                logger.info(f"Присоединен к вкладке {self.target_id}")
                return True
            else:
                logger.error(f"session_id не найден в ответе: {response}")
                return False
        except Exception as e:
            logger.error(f"Ошибка присоединения к вкладке: {e}")
            logger.error(f"Тип ошибки: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    async def navigate(self, url: str):
        """Переход по URL"""
        if not self.session_id:
            raise Exception("Вкладка не присоединена")
        
        await self.connection.send("Page.navigate", {
            "url": url
        }, session_id=self.session_id)
        logger.info(f"Переход на {url}")
    
    async def wait_for_load(self, timeout: int = 30):
        """Ожидание загрузки страницы"""
        if not self.session_id:
            raise Exception("Вкладка не присоединена")
        
        try:
            await asyncio.wait_for(
                self._wait_for_load_event(),
                timeout=timeout
            )
            logger.info("Страница загружена")
        except asyncio.TimeoutError:
            logger.warning("Таймаут ожидания загрузки страницы")
    
    async def _wait_for_load_event(self):
        """Ожидание события загрузки"""
        while True:
            response = await self.connection.websocket.recv()
            data = json.loads(response)
            if data.get("method") == "Page.loadEventFired":
                break
    
    async def evaluate(self, expression: str) -> Any:
        """Выполнение JavaScript в контексте страницы"""
        if not self.session_id:
            raise Exception("Вкладка не присоединена")
        
        response = await self.connection.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True
        }, session_id=self.session_id)
        
        result = response.get("result", {})
        return result.get("value")
    
    async def get_elements(self, selector: str) -> List[Dict[str, Any]]:
        """Получение элементов по CSS селектору"""
        js_code = f"""
        Array.from(document.querySelectorAll('{selector}')).map(el => {{
            return {{
                tagName: el.tagName,
                className: el.className,
                id: el.id,
                textContent: el.textContent?.trim(),
                innerHTML: el.innerHTML
            }};
        }});
        """
        return await self.evaluate(js_code) or []
    
    async def close(self):
        """Закрытие вкладки"""
        if self.session_id:
            await self.connection.send("Target.closeTarget", {
                "targetId": self.target_id
            })
            logger.info(f"Вкладка {self.target_id} закрыта") 