import aiohttp
import asyncio
from typing import List, Dict, Any
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_card_id(nmid: int, dest: str = "-1257786") -> int:
    """Получаем card_id по nmid через API карточки товара"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
        
        url = f'https://card.wb.ru/cards/v2/detail?dest={dest}&nm={nmid}'
        logger.info(f"Получаем card_id для nmid {nmid}: {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Ошибка получения card_id: HTTP {response.status}")
                    return None
                
                content = await response.json()
                logger.info(f"Ответ API карточки: {type(content)}")
                
                if not content.get("data", {}).get("products"):
                    logger.error("Нет данных о продукте в ответе")
                    return None
                
                card_id = content["data"]["products"][0]["root"]
                logger.info(f"Получен card_id: {card_id}")
                return card_id
                
    except Exception as e:
        logger.error(f"Ошибка получения card_id: {e}")
        return None

async def parse_feedbacks_optimized(article: int, max_count: int = 1000) -> List[Dict[str, Any]]:
    """
    Асинхронный парсер отзывов Wildberries через HTTP API с правильным двухэтапным процессом
    """
    # Этап 1: Получаем card_id по nmid
    card_id = await get_card_id(article)
    if not card_id:
        logger.error(f"Не удалось получить card_id для артикула {article}")
        return []
    
    # Этап 2: Получаем отзывы по card_id
    hosts = ["feedbacks1.wb.ru", "feedbacks2.wb.ru"]
    headers = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'referer': 'https://www.wildberries.ru/',
    }
    
    all_feedbacks = []
    seen = set()
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for host in hosts:
                try:
                    url = f'https://{host}/feedbacks/v2/{card_id}'
                    logger.info(f"Запрос отзывов: {url}")
                    
                    async with session.get(url, headers=headers) as resp:
                        logger.info(f"HTTP статус от {host}: {resp.status}")
                        
                        if resp.status != 200:
                            logger.warning(f"Ошибка HTTP {resp.status} от {host}")
                            continue
                        
                        try:
                            data = await resp.json()
                        except Exception as e:
                            logger.error(f"Ошибка парсинга JSON от {host}: {e}")
                            continue
                        
                        logger.info(f"Получен ответ от {host}: {type(data)}")
                        logger.info(f"Полный ответ от {host}: {data}")
                        
                        if not data:
                            logger.warning(f"Пустой ответ от {host}")
                            continue
                        
                        feedbacks = data.get('feedbacks', [])
                        if not feedbacks:
                            logger.warning(f"Нет отзывов в ответе от {host}")
                            logger.warning(f"feedbacks: {feedbacks}")
                            logger.warning(f"feedbackCount: {data.get('feedbackCount', 'N/A')}")
                            continue
                        
                        logger.info(f"Найдено {len(feedbacks)} отзывов от {host}")
                        
                        for fb in feedbacks:
                            try:
                                # Проверяем, что отзыв соответствует нашему артикулу
                                if str(fb.get('nmId', '')) != str(article):
                                    logger.debug(f"Пропускаем отзыв для другого артикула: {fb.get('nmId')} != {article}")
                                    continue
                                
                                # Извлекаем данные отзыва
                                author = fb.get('wbUserDetails', {}).get('name', 'Аноним')
                                date = fb.get('updatedDate', '')
                                rating = fb.get('productValuation', 0)
                                
                                # Формируем текст отзыва
                                text = fb.get('text', '')
                                pros = fb.get('pros', '')
                                cons = fb.get('cons', '')
                                
                                full_text = text
                                if pros:
                                    full_text += f"\nДостоинства: {pros}"
                                if cons:
                                    full_text += f"\nНедостатки: {cons}"
                                
                                # Проверяем уникальность
                                key = (author, date, full_text)
                                if key in seen:
                                    continue
                                seen.add(key)
                                
                                # Обрабатываем дату - убираем часовой пояс если есть
                                if date and 'T' in date:
                                    # Убираем часовой пояс из ISO строки
                                    if '+' in date:
                                        date = date.split('+')[0]
                                    elif 'Z' in date:
                                        date = date.replace('Z', '')
                                
                                feedback_data = {
                                    'author': author,
                                    'date': date,
                                    'status': 'Подтвержденная покупка' if fb.get('verified') else 'Без подтверждения',
                                    'rating': rating,
                                    'text': full_text.strip(),
                                    'article': article
                                }
                                
                                all_feedbacks.append(feedback_data)
                                logger.info(f"Добавлен отзыв от {author}, рейтинг: {rating}")
                                
                                if len(all_feedbacks) >= max_count:
                                    return all_feedbacks[:max_count]
                                    
                            except Exception as e:
                                logger.error(f"Ошибка обработки отзыва: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"HTTP ошибка для {host}: {e}")
                    continue
        
        logger.info(f"Всего найдено отзывов: {len(all_feedbacks)}")
        return all_feedbacks[:max_count]
        
    except Exception as e:
        logger.error(f"HTTP парсер критическая ошибка: {e}")
        return []
