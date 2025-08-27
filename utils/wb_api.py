import httpx
from config import settings
from schemas import WBApiResponse
from utils.validate_image import validate_images
import json
import logging
logger = logging.getLogger("wb_api")

def merge_card_data(old_data: dict, new_data: dict) -> dict:
    result = old_data.copy()

    for key, value in new_data.items():
        if value is None:
            continue

        # Если это словарь — объединяем рекурсивно
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_card_data(result[key], value)
        else:
            result[key] = value

    return result

class WBAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.WB_API_BASE_URL
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> WBApiResponse:
        headers = kwargs.pop('headers', {})
        headers.update({"Authorization": self.api_key})

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    headers=headers,
                    **kwargs
                )

                # Попытка распарсить JSON
                try:
                    json_data = response.json()
                except json.JSONDecodeError:
                    json_data = None

                # Если всё ок — возвращаем данные
                if response.is_success:
                    return WBApiResponse(
                        success=True,
                        data=json_data,
                        wb_response=json_data
                    )
                print(WBApiResponse)

                if json_data:
                    return WBApiResponse(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        wb_response=json_data
                    )

                return WBApiResponse(
                    success=False,
                    data=None,
                    error=f"HTTP {response.status_code} — Invalid JSON",
                    wb_response={"raw_response": response.text}
                )

            except httpx.RequestError as e:
                # Обработка сетевых ошибок
                print("Request Error:", str(e))
                return WBApiResponse(
                    success=False,
                    error=f"Network error: {str(e)}"
                )
            except Exception as e:
                print("Unexpected Error:", str(e))
                return WBApiResponse(
                    success=False,
                    error=str(e)
                )

    async def get_cards_list(self, payload: dict = None):
        response = await self._make_request(
            method="POST",
            endpoint="/content/v2/get/cards/list",
            json=payload or {
                "settings": {
                    "cursor": {},
                    "filter": {"withPhoto": 1}
                }
            }
        )
        return response

    async def get_all_cards_with_pagination(self, brand: str = None, limit: int = 1000):
        """Получает все товары бренда с пагинацией"""
        all_cards = []
        cursor = {}
        page = 1
        
        while True:
            logger.info(f"[WB_API] Запрашиваем страницу {page} товаров для бренда {brand}")
            
            payload = {
                "settings": {
                    "cursor": cursor,
                    "filter": {"withPhoto": 1}
                }
            }
            
            # Добавляем фильтр по бренду если указан
            if brand:
                payload["settings"]["filter"]["brand"] = brand
            
            response = await self._make_request(
                method="POST",
                endpoint="/content/v2/get/cards/list",
                json=payload
            )
            
            if not response.success:
                logger.error(f"[WB_API] Ошибка получения страницы {page}: {response.error}")
                break
            
            data = response.data
            if not data or not isinstance(data, dict):
                logger.error(f"[WB_API] Неверный формат данных на странице {page}")
                break
            
            cards = data.get("cards", [])
            if not cards:
                logger.info(f"[WB_API] На странице {page} нет товаров, завершаем")
                break
            
            logger.info(f"[WB_API] Страница {page}: получено {len(cards)} товаров")
            all_cards.extend(cards)
            
            # Проверяем, есть ли следующая страница
            next_cursor = data.get("cursor", {})
            if not next_cursor or next_cursor == cursor:
                logger.info(f"[WB_API] Достигнут конец списка товаров")
                break
            
            cursor = next_cursor
            page += 1
            
            # Защита от бесконечного цикла
            if page > 100:
                logger.warning(f"[WB_API] Достигнут лимит страниц (100), останавливаемся")
                break
        
        logger.info(f"[WB_API] Всего получено товаров: {len(all_cards)}")
        return WBApiResponse(
            success=True,
            data={"cards": all_cards, "total": len(all_cards)}
        )

    async def get_seller_info(self) -> WBApiResponse:
        """Получение информации о продавце через API WB"""
        # Костыль: используем конкретный URL для seller-info, а не базовый из конфига
        seller_info_url = "https://common-api.wildberries.ru/api/v1/seller-info"
        
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    "GET",
                    seller_info_url,
                    headers=headers
                )

                # Попытка распарсить JSON
                try:
                    json_data = response.json()
                except json.JSONDecodeError:
                    json_data = None

                # Если всё ок — возвращаем данные
                if response.is_success:
                    return WBApiResponse(
                        success=True,
                        data=json_data,
                        wb_response=json_data
                    )

                if json_data:
                    return WBApiResponse(
                        success=False,
                        error=f"HTTP {response.status_code}",
                        wb_response=json_data
                    )

                return WBApiResponse(
                    success=False,
                    data=None,
                    error=f"HTTP {response.status_code} — Invalid JSON",
                    wb_response={"raw_response": response.text}
                )

            except httpx.RequestError as e:
                # Обработка сетевых ошибок
                print("Request Error:", str(e))
                return WBApiResponse(
                    success=False,
                    error=f"Network error: {str(e)}"
                )
            except Exception as e:
                print("Unexpected Error:", str(e))
                return WBApiResponse(
                    success=False,
                    error=str(e)
                )

    async def update_card_content(self, nm_id: int, content: dict) -> WBApiResponse:
        nm_id = str(nm_id)
        current_card = await self.get_card_by_nm(nm_id)
        if not current_card.success:
            print(f"❌ Не удалось получить карточку nm_id={nm_id}: {current_card.error}")
            return WBApiResponse(success=False, error="Карточка не найдена")

        old_data = current_card.data
        vendor_code = old_data.get("vendorCode")

        payload = [{
            "nmID": nm_id,
            "vendorCode": vendor_code,
            "brand": content.get("brand", old_data.get("brand", "")),
            "title": content.get("title", old_data.get("title")),
            "description": content.get("description", old_data.get("description")),
            "dimensions": {
                "length": int(content.get("dimensions", {}).get("length", 0)),
                "width": int(content.get("dimensions", {}).get("width", 0)),
                "height": int(content.get("dimensions", {}).get("height", 0)),
                "weightBrutto": float(content.get("dimensions", {}).get("weightBrutto", 0))
            },
            "characteristics": [
                {
                    "id": ch["id"],
                    "value": ch["value"][0] if isinstance(ch["value"], list) else ch["value"]
                }
                for ch in content.get("characteristics", [])
            ],
            "sizes": old_data.get("sizes", [])
        }]

        print("📦 Payload для /cards/update:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))

        response = await self._make_request(
            "POST",
            "/content/v2/cards/update",
            json=payload
        )
        print("📬 Ответ от /cards/update:", response)
        return response

    async def upload_media(self, nm_id: int, media_urls: list[str]) -> WBApiResponse:
        nm_id = str(nm_id)
        current_card = await self.get_card_by_nm(nm_id)
        if not current_card.success:
            return WBApiResponse(success=False, error="Карточка не найдена")

        valid_urls = []
        for url in media_urls:
            if url.startswith(('https://i.ibb.co', 'https://i.imgbb.com')) or validate_images(url):
                valid_urls.append(url)
            else:
                print(f"⚠️ Пропущена некорректная ссылка: {url}")

        if not valid_urls:
            return WBApiResponse(success=False, error="Нет корректных ссылок для загрузки")

        payload = {
            "nmId": nm_id,
            "data": valid_urls
        }

        print("📤 Отправляем медиа:")
        for url in valid_urls:
            print(url)

        try:
            response = await self._make_request(
                "POST",
                "/content/v3/media/save",
                json=payload
            )
            print("--------------------------------------------------------------------")
            print(response)
            return response
        except Exception as e:
            return WBApiResponse(success=False, error=str(e))

    async def upload_mediaFile(self, nm_id: int, file_data: bytes, photo_number: int,
                               media_type: str = 'image') -> WBApiResponse:
        nm_id = str(nm_id)
        if media_type == 'video' and photo_number != 1:
            logger.error("[upload_mediaFile] Попытка загрузить видео не в позицию 1 (photo_number=%s)", photo_number)
            return WBApiResponse(success=False, error="Video can only be uploaded to position 1")

        filename = "upload.mp4" if media_type == "video" else "upload.jpg"
        content_type = "video/mp4" if media_type == "video" else "image/jpeg"

        headers = {
            "Authorization": self.api_key,
            "X-Nm-Id": nm_id,
            "X-Photo-Number": str(1 if media_type == "video" else photo_number),
        }

        logger.info("[upload_mediaFile] Параметры запроса: nm_id=%s, filename=%s, content_type=%s, file_size=%d, headers=%s, url=%s", nm_id, filename, content_type, len(file_data), headers, f"{self.base_url}/content/v3/media/file")

        timeout = httpx.Timeout(30.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/content/v3/media/file",
                    headers=headers,
                    files={"uploadfile": (filename, file_data, content_type)}
                )

            logger.info("[upload_mediaFile] Статус ответа: %s", response.status_code)
            logger.info("[upload_mediaFile] Текст ответа: %s", response.text)
            try:
                logger.info("[upload_mediaFile] JSON ответа: %s", response.json())
            except Exception as e:
                logger.error("[upload_mediaFile] Ответ не JSON: %s", e)

            if response.is_success:
                logger.info("[upload_mediaFile] Загрузка прошла успешно!")
                return WBApiResponse(
                    success=True,
                    data=response.json(),
                    wb_response=response.json()
                )
            else:
                logger.error("[upload_mediaFile] Ошибка загрузки: HTTP %s: %s", response.status_code, response.text)
                return WBApiResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    wb_response=response.text
                )

        except Exception as e:
            logger.error("[upload_mediaFile] Исключение: %s", e, exc_info=True)
            return WBApiResponse(success=False, error=str(e))

    async def get_card_by_nm(self, nm_id: int):
        nm_id = str(nm_id)
        response = await self.get_all_cards_with_pagination()

        if not response.success:
            print(f"❌ Не удалось получить список карточек: {response.error}")
            raise Exception("Не удалось получить список карточек")

        if not isinstance(response.data, dict):
            raise ValueError("Неверный формат данных от API")

        cards = response.data.get("cards", [])
        print(f"🔍 Получено карточек: {len(cards)}")

        for card in cards:
            current_nm_id = card.get("nmID")
            if str(current_nm_id) == nm_id:
                return WBApiResponse(
                    success=True,
                    data=card
                )
        print(f"⚠️ Карточка с nmID={nm_id} не найдена в списке")
        return WBApiResponse(
            success=False,
            error="Карточка не найдена"
        )

    async def get_card_by_vendor(self, vendorCode: str) -> WBApiResponse:
        try:
            # Используем новую функцию с пагинацией для поиска по vendorCode
            response = await self.get_all_cards_with_pagination()

            if not response.success:
                return WBApiResponse(
                    success=False,
                    error="Не удалось получить список карточек"
                )

            if not isinstance(response.data, dict):
                return WBApiResponse(
                    success=False,
                    error="Неверный формат данных от API"
                )

            cards = response.data.get("cards", [])

            for card in cards:
                current_vc = card.get("vendorCode")
                # Сравниваем как строки, игнорируя регистр
                if str(current_vc).lower() == str(vendorCode).lower():
                    return WBApiResponse(
                        success=True,
                        data=card
                    )

            return WBApiResponse(
                success=False,
                error=f"Карточка с vendorCode '{vendorCode}' не найдена"
            )
        except Exception as e:
            return WBApiResponse(
                success=False,
                error=f"Ошибка при поиске: {str(e)}"
            )

    # Функция get_all_cards удалена - используйте get_all_cards_with_pagination

    async def get_stocks_report_products(self, nm_ids: list, start_date: str, end_date: str) -> WBApiResponse:
        """Вызов отчёта истории остатков по товарам (isDeleted и др.)

        Документация: Аналитика и данные → История остатков → Данные по товарам.
        POST https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products

        Параметры:
        - nm_ids: список nmID
        - start_date, end_date: YYYY-MM-DD
        """
        url = "https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products"
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}

        # Минимальный валидный payload: nmIDs + даты. Добавляем таймзону по умолчанию
        payload = {
            "nmIDs": [int(x) for x in nm_ids if str(x).isdigit()],
            "currentPeriod": {
                "start": start_date,
                "end": end_date
            },
            "stockType": "",
            "skipDeletedNm": True,
            "orderBy": {
                "field": "avgOrders",
                "mode": "asc"
            },
            "availabilityFilters": [
                "deficient", "actual", "balanced", "nonActual", "nonLiquid", "invalidData"
            ],
            "limit": 1000,
            "offset": 0
        }

        try:
            logger.info(f"[WB_API] stocks-report: products={len(payload['nmIDs'])}, period={start_date}..{end_date}")
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=headers, json=payload)
                logger.info(f"[WB_API] stocks-report status={resp.status_code}")
                body_text = resp.text
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    data = None

                # Успех с первой попытки
                if resp.is_success:
                    return WBApiResponse(success=True, data=data, wb_response=data)

                logger.warning(f"[WB_API] stocks-report 1st attempt failed: status={resp.status_code}, body={body_text}")
                return WBApiResponse(success=False, error=f"HTTP {resp.status_code}", wb_response=data or {"raw": body_text})
        except Exception as e:
            return WBApiResponse(success=False, error=str(e))

