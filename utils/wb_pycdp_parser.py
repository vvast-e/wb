import asyncio
import logging
from typing import List, Dict, Any
import subprocess
import platform
import os

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

async def _http_fallback_parser(article: int, max_count: int) -> List[Dict[str, Any]]:
    """Fallback парсер через HTTP API с правильным двухэтапным процессом"""
    try:
        import aiohttp
        
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
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            for host in hosts:
                try:
                    url = f'https://{host}/feedbacks/v2/{card_id}'
                    logger.info(f"HTTP fallback: запрос к {url}")
                    
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
                            # Проверяем, что отзыв соответствует нашему артикулу
                            if str(fb.get('nmId', '')) != str(article):
                                logger.debug(f"Пропускаем отзыв для другого артикула: {fb.get('nmId')} != {article}")
                                continue
                            
                            key = (fb.get('wbUserDetails', {}).get('name', 'Аноним'), fb.get('updatedDate'), fb.get('text', ''))
                            if key in seen:
                                continue
                            seen.add(key)
                            
                            # Обрабатываем дату - убираем часовой пояс если есть
                            date_str = fb.get('updatedDate', '')
                            if date_str and 'T' in date_str:
                                # Убираем часовой пояс из ISO строки
                                if '+' in date_str:
                                    date_str = date_str.split('+')[0]
                                elif 'Z' in date_str:
                                    date_str = date_str.replace('Z', '')
                            
                            all_feedbacks.append({
                                'author': fb.get('wbUserDetails', {}).get('name', 'Аноним'),
                                'date': date_str,
                                'status': 'Подтвержденная покупка' if fb.get('verified') else 'Без подтверждения',
                                'rating': fb.get('productValuation', 0),
                                'text': fb.get('text', '') or (fb.get('pros', '') + '\n' + fb.get('cons', '')),
                                'article': article
                            })
                            
                            if len(all_feedbacks) >= max_count:
                                return all_feedbacks[:max_count]
                                
                except Exception as e:
                    logger.error(f"HTTP fallback ошибка для {host}: {e}")
                    continue
        
        return all_feedbacks[:max_count]
        
    except Exception as e:
        logger.error(f"HTTP fallback критическая ошибка: {e}")
        return []

async def parse_feedbacks_optimized(article: int, max_count: int = 1000) -> List[Dict[str, Any]]:
    """
    Асинхронный парсер отзывов Wildberries с использованием PyCDP
    """
    # Сначала пробуем HTTP парсер (он быстрее и стабильнее)
    logger.info("Пробуем HTTP парсер...")
    http_feedbacks = await _http_fallback_parser(article, max_count)
    
    if http_feedbacks:
        logger.info(f"HTTP парсер успешно нашел {len(http_feedbacks)} отзывов")
        return http_feedbacks
    
    # Если HTTP не сработал, пробуем PyCDP
    logger.info("HTTP парсер не сработал, пробуем PyCDP...")
    
    all_feedbacks = []
    seen = set()
    
    try:
        # Запускаем Chrome
        chrome_process = await _start_chrome()
        if not chrome_process:
            logger.error("Не удалось запустить Chrome")
            return await _http_fallback_parser(article, max_count)
        
        # Подключаемся через PyCDP
        try:
            from pycdp import cdp
            from pycdp.cdp import target, page, runtime
        except ImportError:
            # Попробуем альтернативный импорт
            import pycdp
            from pycdp import target, page, runtime
            cdp = pycdp
        
        async with cdp.connect_browser("localhost", 9222) as browser:
            # Создаем новую вкладку
            target_id = await browser.new_tab()
            logger.info(f"Создана вкладка: {target_id}")
            
            # Подключаемся к вкладке
            async with browser.connect_tab(target_id) as tab:
                # Включаем домены
                await tab.execute(page.enable())
                await tab.execute(runtime.enable())
                
                # Переходим на страницу отзывов
                url = f"https://www.wildberries.ru/catalog/{article}/feedbacks?sort=newest"
                logger.info(f"Переходим на URL: {url}")
                
                await tab.execute(page.navigate(url=url))
                
                # Ждем загрузки страницы
                logger.info("Ожидаем загрузки страницы...")
                await tab.wait_event(page.LoadEventFired, timeout=30.0)
                
                # Ждем появления отзывов
                logger.info("Ждем появления отзывов...")
                await asyncio.sleep(5)
                
                # Парсим отзывы
                logger.info("Выполняем JavaScript для парсинга отзывов...")
                result = await tab.evaluate("""
                    const reviews = [];
                    
                    // Логируем структуру страницы для отладки
                    console.log('=== НАЧАЛО ЛОГИРОВАНИЯ ===');
                    console.log('URL:', window.location.href);
                    console.log('Title:', document.title);
                    console.log('Body length:', document.body.innerHTML.length);
                    
                    // Пробуем разные селекторы
                    let items = document.querySelectorAll('.comments__item.feedback');
                    if (items.length === 0) {
                        items = document.querySelectorAll('[data-testid="feedback-item"]');
                    }
                    if (items.length === 0) {
                        items = document.querySelectorAll('.feedback-item');
                    }
                    if (items.length === 0) {
                        items = document.querySelectorAll('.review-item');
                    }
                    if (items.length === 0) {
                        items = document.querySelectorAll('.comment-item');
                    }
                    if (items.length === 0) {
                        items = document.querySelectorAll('.feedback');
                    }
                    if (items.length === 0) {
                        items = document.querySelectorAll('.review');
                    }
                    
                    console.log('Найдено элементов отзывов:', items.length);
                    
                    for (let i = 0; i < items.length; i++) {
                        const item = items[i];
                        console.log('Обрабатываем элемент:', item.outerHTML.substring(0, 200));
                        
                        // Получаем рейтинг (пробуем разные селекторы)
                        let rating = 0;
                        const ratingEl = item.querySelector('.feedback__rating') || 
                                       item.querySelector('.rating') || 
                                       item.querySelector('.stars') ||
                                       item.querySelector('[data-rating]') ||
                                       item.querySelector('.star-rating');
                        
                        if (ratingEl) {
                            const ratingClass = ratingEl.className || '';
                            const ratingMatch = ratingClass.match(/star(\\d)/);
                            if (ratingMatch) {
                                rating = parseInt(ratingMatch[1]);
                            } else {
                                const dataRating = ratingEl.getAttribute('data-rating');
                                if (dataRating) rating = parseInt(dataRating);
                            }
                        }
                        
                        // Получаем автора
                        let author = 'Аноним';
                        const authorEl = item.querySelector('.feedback__header') || 
                                       item.querySelector('.author') || 
                                       item.querySelector('.user-name') ||
                                       item.querySelector('[data-author]') ||
                                       item.querySelector('.reviewer-name');
                        if (authorEl) {
                            author = authorEl.textContent.trim();
                        }
                        
                        // Получаем дату
                        let date = '';
                        const dateEl = item.querySelector('.feedback__date') || 
                                     item.querySelector('.date') || 
                                     item.querySelector('.review-date') ||
                                     item.querySelector('.comment-date');
                        if (dateEl) {
                            date = dateEl.getAttribute('content') || dateEl.textContent.trim();
                        }
                        
                        // Получаем текст отзыва
                        let mainText = '';
                        const mainTextEl = item.querySelector('.feedback__text--item:not(.feedback__text--item-pro):not(.feedback__text--item-contra)') ||
                                         item.querySelector('.review-text') ||
                                         item.querySelector('.comment-text') ||
                                         item.querySelector('.text') ||
                                         item.querySelector('.feedback-text');
                        if (mainTextEl) mainText = mainTextEl.innerText.trim();
                        
                        let prosText = '';
                        const prosEl = item.querySelector('.feedback__text--item-pro') ||
                                     item.querySelector('.pros') ||
                                     item.querySelector('.advantages') ||
                                     item.querySelector('.positive');
                        if (prosEl) prosText = prosEl.innerText.replace(/Достоинства?:/, '').trim();
                        
                        let consText = '';
                        const consEl = item.querySelector('.feedback__text--item-contra') ||
                                     item.querySelector('.cons') ||
                                     item.querySelector('.disadvantages') ||
                                     item.querySelector('.negative');
                        if (consEl) consText = consEl.innerText.replace(/Недостатки?:/, '').trim();
                        
                        // Формируем полный текст
                        let fullText = '';
                        if (mainText) fullText += mainText + '\\n';
                        if (prosText) fullText += 'Достоинства: ' + prosText + '\\n';
                        if (consText) fullText += 'Недостатки: ' + consText;
                        
                        // Получаем статус
                        let status = 'Без подтверждения';
                        const statusEl = item.querySelector('.feedback__state--text') ||
                                       item.querySelector('.status') ||
                                       item.querySelector('.verified') ||
                                       item.querySelector('.purchase-verified');
                        if (statusEl) {
                            status = statusEl.innerText || statusEl.textContent;
                        }
                        
                        reviews.push({
                            author: author,
                            date: date,
                            status: status,
                            rating: rating,
                            text: fullText.trim()
                        });
                    }
                    
                    console.log('Собрано отзывов:', reviews.length);
                    return reviews;
                """)
                
                logger.info(f"JavaScript вернул: {result}")
                
                if result and result.value:
                    reviews_batch = result.value
                    logger.info(f"Найдено отзывов: {len(reviews_batch)}")
                    
                    # Обрабатываем отзывы
                    for fb in reviews_batch:
                        key = (fb['author'], fb['date'], fb['text'])
                        if key not in seen:
                            all_feedbacks.append(fb)
                            seen.add(key)
                            logger.info(f"Добавлен отзыв от {fb['author']}, рейтинг: {fb['rating']}")
                
                # Закрываем вкладку
                await browser.close_tab(target_id)
        
        # Завершаем Chrome
        chrome_process.terminate()
        chrome_process.wait(timeout=5)
        
    except Exception as e:
        logger.error(f"Ошибка в парсере PyCDP: {e}")
        logger.info("Переключаемся на HTTP fallback парсер")
        # Fallback на HTTP парсер
        return await _http_fallback_parser(article, max_count)
    
    logger.info(f"Всего собрано отзывов: {len(all_feedbacks)}")
    return all_feedbacks[:max_count]

async def _start_chrome():
    """Запуск Chrome в режиме remote debugging"""
    try:
        # Определяем путь к Chrome для Windows
        chrome_paths = []
        if platform.system() == "Windows":
            program_files = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
            program_files_x86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
            
            chrome_paths = [
                os.path.join(program_files, 'Google\\Chrome\\Application\\chrome.exe'),
                os.path.join(program_files_x86, 'Google\\Chrome\\Application\\chrome.exe'),
                'chrome.exe',
                'google-chrome.exe'
            ]
        
        # Ищем Chrome
        chrome_executable = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_executable = path
                logger.info(f"Найден Chrome: {chrome_executable}")
                break
        
        if not chrome_executable:
            logger.error("Chrome не найден!")
            return None
        
        # Команда для запуска Chrome
        port = 9222
        cmd = [
            chrome_executable,
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-web-security",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
            "--disable-plugins",
            "--headless"
        ]
        
        logger.info(f"Запуск Chrome: {' '.join(cmd)}")
        
        # Запускаем Chrome
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        
        # Проверяем, что процесс запустился
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logger.error(f"Chrome не запустился. stdout: {stdout.decode()}, stderr: {stderr.decode()}")
            return None
        
        logger.info("Chrome запущен, ожидаем готовности...")
        await asyncio.sleep(5)
        
        # Проверяем порт
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            logger.info(f"Порт {port} доступен!")
            return process
        else:
            logger.error(f"Порт {port} недоступен!")
            process.terminate()
            return None
        
    except Exception as e:
        logger.error(f"Ошибка при запуске Chrome: {e}")
        return None 