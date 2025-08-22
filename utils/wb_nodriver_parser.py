import asyncio
import logging
import os
from typing import List, Dict, Any
from utils.nodriver import Browser
import json

logger = logging.getLogger(__name__)

async def get_card_id(nmid: int, dest: str = "-1257786") -> int:
    """Получаем card_id по nmid через API карточки товара"""
    try:
        import aiohttp
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        }
        
        url = f'https://card.wb.ru/cards/v2/detail?dest={dest}&nm={nmid}'
        logger.info(f"Получаем card_id для nmid {nmid}: {url}")
        print(f"[CARD_ID] Получаем card_id для nmid {nmid}: {url}")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers) as response:
                print(f"[CARD_ID] HTTP статус: {response.status}")
                if response.status != 200:
                    logger.error(f"Ошибка получения card_id: HTTP {response.status}")
                    print(f"[CARD_ID] ОШИБКА: HTTP {response.status}")
                    return None
                
                content = await response.json()
                logger.info(f"Ответ API карточки: {type(content)}")
                print(f"[CARD_ID] Ответ API карточки: {type(content)}")
                
                if not content.get("data", {}).get("products"):
                    logger.error("Нет данных о продукте в ответе")
                    print(f"[CARD_ID] ОШИБКА: Нет данных о продукте в ответе")
                    print(f"[CARD_ID] Содержимое ответа: {content}")
                    return None
                
                card_id = content["data"]["products"][0]["root"]
                logger.info(f"Получен card_id: {card_id}")
                print(f"[CARD_ID] Получен card_id: {card_id}")
                return card_id
                
    except Exception as e:
        logger.error(f"Ошибка получения card_id: {e}")
        print(f"[CARD_ID] ОШИБКА: {e}")
        return None

async def _http_fallback_parser(article: int, max_count: int) -> List[Dict[str, Any]]:
    """Fallback парсер через HTTP API с правильным двухэтапным процессом"""
    try:
        import aiohttp
        
        print(f"[HTTP_PARSER] Начинаем HTTP парсинг для артикула {article}")
        
        # Этап 1: Получаем card_id по nmid
        print(f"[HTTP_PARSER] Этап 1: Получаем card_id для артикула {article}...")
        card_id = await get_card_id(article)
        if not card_id:
            logger.error(f"Не удалось получить card_id для артикула {article}")
            print(f"[HTTP_PARSER] ОШИБКА: Не удалось получить card_id для артикула {article}")
            return []
        
        print(f"[HTTP_PARSER] Получен card_id: {card_id}")
        
        # Этап 2: Получаем отзывы по card_id
        print(f"[HTTP_PARSER] Этап 2: Получаем отзывы по card_id {card_id}...")
        hosts = ["feedbacks1.wb.ru", "feedbacks2.wb.ru"]
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'referer': 'https://www.wildberries.ru/',
        }
        
        all_feedbacks = []
        seen = set()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for host in hosts:
                try:
                    url = f'https://{host}/feedbacks/v2/{card_id}'
                    logger.info(f"HTTP fallback: запрос к {url}")
                    print(f"[HTTP_PARSER] Запрос к {url}")
                    
                    async with session.get(url, headers=headers) as resp:
                        logger.info(f"HTTP статус от {host}: {resp.status}")
                        print(f"[HTTP_PARSER] HTTP статус от {host}: {resp.status}")
                        
                        if resp.status != 200:
                            logger.warning(f"Ошибка HTTP {resp.status} от {host}")
                            print(f"[HTTP_PARSER] ОШИБКА HTTP {resp.status} от {host}")
                            continue
                        
                        try:
                            data = await resp.json()
                        except Exception as e:
                            logger.error(f"Ошибка парсинга JSON от {host}: {e}")
                            print(f"[HTTP_PARSER] ОШИБКА парсинга JSON от {host}: {e}")
                            continue
                        
                        logger.info(f"Получен ответ от {host}: {type(data)}")
                        print(f"[HTTP_PARSER] Получен ответ от {host}: {type(data)}")
                        
                        # --- Сохраняем первые 10 отзывов для диагностики ---
                        feedbacks = data.get('feedbacks', [])
                        if feedbacks:
                            sample = feedbacks[:10]
                            with open('wb_feedbacks_sample.json', 'w', encoding='utf-8') as f:
                                json.dump(sample, f, ensure_ascii=False, indent=2)
                        # --- конец блока сохранения ---

                        # --- Сохраняем полный ответ от сервера для диагностики ---
                        if data:
                            try:
                                with open('wb_api_full_response.json', 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                logger.error(f"Ошибка при сохранении полного ответа WB API: {e}")
                        # --- конец блока сохранения полного ответа ---
                        
                        if not data:
                            logger.warning(f"Пустой ответ от {host}")
                            print(f"[HTTP_PARSER] Пустой ответ от {host}")
                            continue
                        
                        feedbacks = data.get('feedbacks', [])
                        feedback_count = data.get('feedbackCount', 0)
                        
                        print(f"[HTTP_PARSER] feedbackCount в ответе: {feedback_count}")
                        print(f"[HTTP_PARSER] feedbacks в ответе: {len(feedbacks) if feedbacks else 'None'}")
                        
                        if not feedbacks:
                            logger.warning(f"Нет отзывов в ответе от {host}")
                            logger.warning(f"feedbacks: {feedbacks}")
                            logger.warning(f"feedbackCount: {data.get('feedbackCount', 'N/A')}")
                            print(f"[HTTP_PARSER] Нет отзывов в ответе от {host}")
                            print(f"[HTTP_PARSER] feedbacks: {feedbacks}")
                            print(f"[HTTP_PARSER] feedbackCount: {data.get('feedbackCount', 'N/A')}")
                            continue
                        
                        logger.info(f"Найдено {len(feedbacks)} отзывов от {host}")
                        print(f"[HTTP_PARSER] Найдено {len(feedbacks)} отзывов от {host}")
                        
                        for fb in feedbacks:
                            # Проверяем, что отзыв соответствует нашему артикулу
                            if str(fb.get('nmId', '')) != str(article):
                                logger.debug(f"Пропускаем отзыв для другого артикула: {fb.get('nmId')} != {article}")
                                continue
                            
                            key = (fb.get('wbUserDetails', {}).get('name', 'Аноним'), fb.get('createdDate', fb.get('updatedDate', '')), fb.get('text', ''))
                            if key in seen:
                                continue
                            seen.add(key)
                            
                            # Обрабатываем дату - используем createdDate или updatedDate
                            date_str = fb.get('createdDate', fb.get('updatedDate', ''))
                            # Убираем логирование дат в файл
                            # НЕ обрабатываем дату здесь - это будет сделано в parse_wb_date
                            
                            # Формируем текст с правильными разделителями
                            main_text = fb.get('text', '')
                            pros_text = fb.get('pros', '')
                            cons_text = fb.get('cons', '')
                            
                            # Если есть отдельные поля pros/cons, формируем структурированный текст
                            if pros_text or cons_text:
                                full_text = main_text
                                if pros_text:
                                    full_text += f"\nДостоинства: {pros_text}"
                                if cons_text:
                                    full_text += f"\nНедостатки: {cons_text}"
                            else:
                                full_text = main_text
                            
                            all_feedbacks.append({
                                'id': fb.get('id'),  # Добавляем wb_id
                                'author': fb.get('wbUserDetails', {}).get('name', 'Аноним'),
                                'date': date_str,
                                'status': 'Подтвержденная покупка' if fb.get('statusId', 0) == 16 else 'Без подтверждения',
                                'rating': fb.get('productValuation', 0),
                                'text': full_text,
                                'article': article,
                                'nmId': fb.get('nmId'),
                                'wb_id': fb.get('id'),  # Добавлено поле wb_id
                                'pros': fb.get('pros', ''),
                                'cons': fb.get('cons', '')
                            })
                            
                            if len(all_feedbacks) >= max_count:
                                print(f"[HTTP_PARSER] Достигнут лимит отзывов: {max_count}")
                                return all_feedbacks[:max_count]
                                
                except Exception as e:
                    logger.error(f"HTTP fallback ошибка для {host}: {e}")
                    print(f"[HTTP_PARSER] ОШИБКА для {host}: {e}")
                    continue
        
        print(f"[HTTP_PARSER] Итого найдено отзывов: {len(all_feedbacks)}")
        return all_feedbacks[:max_count]
        
    except Exception as e:
        logger.error(f"HTTP fallback критическая ошибка: {e}")
        print(f"[HTTP_PARSER] КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return []

async def parse_feedbacks_optimized(article: int, max_count: int = 1000) -> List[Dict[str, Any]]:
    """
    Асинхронный парсер отзывов Wildberries с автоматическим выбором метода
    """
    logger.info(f"=== НАЧАЛО ПАРСИНГА ДЛЯ АРТИКУЛА {article} ===")
    logger.info(f"Максимальное количество отзывов: {max_count}")
    
    print(f"[PARSER] Начинаем парсинг отзывов для артикула {article}")
    print(f"[PARSER] Максимальное количество отзывов: {max_count}")
    
    try:
        import aiohttp
        logger.info("aiohttp доступен")
        print("[PARSER] aiohttp доступен")
    except ImportError as e:
        logger.error(f"aiohttp не установлен: {e}")
        print(f"[PARSER] ОШИБКА: aiohttp не установлен: {e}")
        return []
    
    logger.info("Используем HTTP парсер...")
    print("[PARSER] Используем HTTP парсер...")
    
    http_feedbacks = await _http_fallback_parser(article, max_count)
    
    if http_feedbacks:
        logger.info(f"HTTP парсер успешно нашел {len(http_feedbacks)} отзывов")
        print(f"[PARSER] HTTP парсер успешно нашел {len(http_feedbacks)} отзывов")
        return http_feedbacks
    else:
        logger.warning("HTTP парсер не нашел отзывов")
        print("[PARSER] HTTP парсер не нашел отзывов")
        return []
    
    # Отключаем nodriver для сервера (проблемы с браузером)
    # logger.info("HTTP парсер не сработал, пробуем nodriver...")
    # 
    # # Проверяем доступность nodriver
    # try:
    #     from utils.nodriver import Browser
    #     logger.info("nodriver доступен")
    # except ImportError as e:
    #     logger.error(f"nodriver не установлен: {e}")
    #     return []
    # 
    # all_feedbacks = []
    # seen = set()
    # 
    # try:
    #     # Пробуем запустить браузер с автоматическим поиском Chrome
    #     logger.info("Запускаем Browser...")
    #     async with Browser(headless=True) as browser:
    #         logger.info("Browser запущен, создаем вкладку...")
    #         # Создаем вкладку
    #         tab = await browser.create_tab()
    #         if not tab:
    #             logger.error("Не удалось создать вкладку")
    #             logger.info("Переключаемся на HTTP fallback парсер")
    #             return await _http_fallback_parser(article, max_count)
    #         
    #         # Переходим на страницу отзывов
    #         url = f"https://www.wildberries.ru/catalog/{article}/feedbacks?sort=newest"
    #         logger.info(f"Переходим на URL: {url}")
    #         await tab.navigate(url)
    #         logger.info("Ожидаем загрузки страницы...")
    #         await tab.wait_for_load()
    #         
    #         # Ждем появления отзывов
    #         logger.info("Ждем появления отзывов...")
    #         await asyncio.sleep(3)
    #         
    #         # Включаем логирование консоли
    #         await tab.evaluate("""
    #             console.log('=== НАЧАЛО ЛОГИРОВАНИЯ ===');
    #             console.log('URL:', window.location.href);
    #             console.log('Title:', document.title);
    #             console.log('Body length:', document.body.innerHTML.length);
    #         """)
    #         
    #         last_count = 0
    #         while len(all_feedbacks) < max_count:
    #             # Парсим отзывы через JavaScript
    #             logger.info("Выполняем JavaScript для парсинга отзывов...")
    #             reviews_batch = await tab.evaluate("""
    #                 const reviews = [];
    #                 
    #                 // Логируем структуру страницы для отладки
    #                 console.log('Document body:', document.body.innerHTML.substring(0, 1000));
    #                 
    #                 // Пробуем разные селекторы
    #                 let items = document.querySelectorAll('.comments__item.feedback');
    #                 if (items.length === 0) {
    #                     items = document.querySelectorAll('[data-testid="feedback-item"]');
    #                 }
    #                 if (items.length === 0) {
    #                     items = document.querySelectorAll('.feedback-item');
    #                 }
    #                 if (items.length === 0) {
    #                     items = document.querySelectorAll('.review-item');
    #                 }
    #                 if (items.length === 0) {
    #                     items = document.querySelectorAll('.comment-item');
    #                 }
    #                 
    #                 console.log('Найдено элементов отзывов:', items.length);
    #                 
    #                 for (let i = 0; i < items.length; i++) {
    #                     const item = items[i];
    #                     console.log('Обрабатываем элемент:', item.outerHTML.substring(0, 200));
    #                     
    #                     // Получаем рейтинг (пробуем разные селекторы)
    #                     let rating = 0;
    #                     const ratingEl = item.querySelector('.feedback__rating') || 
    #                                    item.querySelector('.rating') || 
    #                                    item.querySelector('.stars') ||
    #                                    item.querySelector('[data-rating]');
    #                     
    #                     if (ratingEl) {
    #                         const ratingClass = ratingEl.className || '';
    #                         const ratingMatch = ratingClass.match(/star(\\d)/);
    #                         if (ratingMatch) {
    #                             rating = parseInt(ratingMatch[1]);
    #                         } else {
    #                             const dataRating = ratingEl.getAttribute('data-rating');
    #                             if (dataRating) rating = parseInt(dataRating);
    #                         }
    #                     }
    #                     
    #                     // Получаем автора
    #                     let author = 'Аноним';
    #                     const authorEl = item.querySelector('.feedback__header') || 
    #                                    item.querySelector('.author') || 
    #                                    item.querySelector('.user-name') ||
    #                                    item.querySelector('[data-author]');
    #                     if (authorEl) {
    #                         author = authorEl.textContent.trim();
    #                     }
    #                     
    #                     // Получаем дату
    #                     let date = '';
    #                     const dateEl = item.querySelector('.feedback__date') || 
    #                                   item.querySelector('.date') || 
    #                                   item.querySelector('.review-date');
    #                     if (dateEl) {
    #                         date = dateEl.getAttribute('content') || dateEl.textContent.trim();
    #                     }
    #                     
    #                     // Получаем текст отзыва
    #                     let mainText = '';
    #                     const mainTextEl = item.querySelector('.feedback__text--item:not(.feedback__text--item-pro):not(.feedback__text--item-contra)') ||
    #                                      item.querySelector('.review-text') ||
    #                                      item.querySelector('.comment-text') ||
    #                                      item.querySelector('.text');
    #                     if (mainTextEl) mainText = mainTextEl.innerText.trim();
    #                     
    #                     let prosText = '';
    #                     const prosEl = item.querySelector('.feedback__text--item-pro') ||
    #                                  item.querySelector('.pros') ||
    #                                  item.querySelector('.advantages');
    #                     if (prosEl) prosText = prosEl.innerText.replace(/Достоинства?:/, '').trim();
    #                     
    #                     let consText = '';
    #                     const consEl = item.querySelector('.feedback__text--item-contra') ||
    #                                  item.querySelector('.cons') ||
    #                                  item.querySelector('.disadvantages');
    #                     if (consEl) consText = consEl.innerText.replace(/Недостатки?:/, '').trim();
    #                     
    #                     // Формируем полный текст
    #                     let fullText = '';
    #                     if (mainText) fullText += mainText + '\\n';
    #                     if (prosText) fullText += 'Достоинства: ' + prosText + '\\n';
    #                     if (consText) fullText += 'Недостатки: ' + consText;
    #                     
    #                     // Получаем статус
    #                     let status = 'Без подтверждения';
    #                     const statusEl = item.querySelector('.feedback__state--text') ||
    #                                    item.querySelector('.status') ||
    #                                    item.querySelector('.verified');
    #                     if (statusEl) {
    #                         status = statusEl.innerText || statusEl.textContent;
    #                     }
    #                     
    #                     reviews.push({
    #                         author: author,
    #                         date: date,
    #                         status: status,
    #                         rating: rating,
    #                         text: fullText.trim()
    #                     });
    #                 }
    #                 
    #                 console.log('Собрано отзывов:', reviews.length);
    #                 return reviews;
    #             """)
    #             
    #             logger.info(f"JavaScript вернул: {reviews_batch}")
    #             if not reviews_batch:
    #                 logger.warning("Отзывы не найдены на странице")
    #                 break
    #             
    #             # Обрабатываем новые отзывы
    #             for fb in reviews_batch:
    #                 key = (fb['author'], fb['date'], fb['text'])
    #                 if key not in seen:
    #                     all_feedbacks.append(fb)
    #                     seen.add(key)
    #                     logger.info(f"Добавлен отзыв от {fb['author']}, рейтинг: {fb['rating']}")
    #             
    #             # Проверяем, есть ли новые отзывы
    #             if len(all_feedbacks) == last_count:
    #                 logger.info("Новых отзывов не найдено, завершаем парсинг")
    #                 break
    #             
    #             last_count = len(all_feedbacks)
    #             
    #             # Скроллим вниз для загрузки новых отзывов
    #             await tab.evaluate("""
    #                 window.scrollTo(0, document.body.scrollHeight);
    #             """)
    #             
    #             await asyncio.sleep(1)
    #             
    #             if len(all_feedbacks) >= max_count:
    #                 logger.info(f"Достигнут лимит отзывов: {max_count}")
    #                 break
    #     
    # except Exception as e:
    #     logger.error(f"Ошибка в парсере nodriver: {e}")
    #     logger.info("Переключаемся на HTTP fallback парсер")
    #     # Fallback на HTTP парсер
    #     return await _http_fallback_parser(article, max_count)
    
    logger.info(f"Всего собрано отзывов: {len(all_feedbacks)}")
    return all_feedbacks[:max_count] 