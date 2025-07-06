import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Element:
    """Класс для работы с DOM элементами"""
    
    def __init__(self, tab, node_id: int):
        self.tab = tab
        self.node_id = node_id
        
    async def get_text(self) -> str:
        """Получение текста элемента"""
        try:
            js_code = f"""
            (function() {{
                const element = document.querySelector('[data-node-id="{self.node_id}"]');
                return element ? element.textContent.trim() : '';
            }})();
            """
            return await self.tab.evaluate(js_code) or ""
        except Exception as e:
            logger.error(f"Ошибка получения текста: {e}")
            return ""
    
    async def get_attribute(self, name: str) -> str:
        """Получение атрибута элемента"""
        try:
            js_code = f"""
            (function() {{
                const element = document.querySelector('[data-node-id="{self.node_id}"]');
                return element ? element.getAttribute('{name}') : '';
            }})();
            """
            return await self.tab.evaluate(js_code) or ""
        except Exception as e:
            logger.error(f"Ошибка получения атрибута {name}: {e}")
            return ""
    
    async def click(self):
        """Клик по элементу"""
        try:
            js_code = f"""
            (function() {{
                const element = document.querySelector('[data-node-id="{self.node_id}"]');
                if (element) {{
                    element.click();
                    return true;
                }}
                return false;
            }})();
            """
            return await self.tab.evaluate(js_code)
        except Exception as e:
            logger.error(f"Ошибка клика: {e}")
            return False
    
    async def scroll_into_view(self):
        """Прокрутка к элементу"""
        try:
            js_code = f"""
            (function() {{
                const element = document.querySelector('[data-node-id="{self.node_id}"]');
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    return true;
                }}
                return false;
            }})();
            """
            return await self.tab.evaluate(js_code)
        except Exception as e:
            logger.error(f"Ошибка прокрутки: {e}")
            return False 