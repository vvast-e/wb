import httpx
from config import settings
from schemas import WBApiResponse
from utils.validate_image import validate_images
import json

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
                # Любые другие исключения
                print("Unexpected Error:", str(e))
                return WBApiResponse(
                    success=False,
                    error=str(e)
                )

    async def get_cards_list(self, payload: dict = None):
        return await self._make_request(
            method="POST",
            endpoint="/content/v2/get/cards/list",
            json=payload or {
                "settings": {
                    "cursor": {},
                    "filter": {"withPhoto": 1}
                }
            }
        )

    async def update_card_content(self, nm_id: int, content: dict):
        """Обновление карточки с учетом ограничений WB API"""
        current_card = await self.get_card_by_nm(nm_id)
        if not current_card.success:
            raise ValueError("Карточка не найдена")

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

        print("Payload characteristics example value:",
              next((c["value"] for c in payload[0].get("characteristics", []) if c.get("id") == 89010), None))

        try:
            response = await self._make_request(
                "POST",
                "/content/v2/cards/update",
                json=payload
            )
        except Exception as e:
            print(f"Exception during WB API request: {e}")
            raise

        print("WB API update response:", response)

        if not response.get("success", False):
            error_msg = response.get("error", "Неизвестная ошибка при обновлении карточки")
            print(f"Ошибка при обновлении карточки: {error_msg}")
            raise ValueError(f"Ошибка при обновлении карточки: {error_msg}")

        if "data" in response and isinstance(response["data"], list):
            for card_result in response["data"]:
                if card_result.get("status") != "success":
                    detail = card_result.get("error", "Неизвестная ошибка в результате обновления")
                    print(f"Ошибка в карточке nmID={nm_id}: {detail}")
                    raise ValueError(f"Ошибка в карточке nmID={nm_id}: {detail}")

        return response

    async def upload_media(self, nm_id: int, media_urls: list[str]):
        current_card = await self.get_card_by_nm(nm_id)
        if not current_card.success:
            raise ValueError("Карточка не найдена")

        # Валидация новых ссылок (если надо)
        valid_urls = []
        for url in media_urls:
            if validate_images(url):
                valid_urls.append(url)
            else:
                print(f"⚠️ Пропущено некорректное изображение: {url}")

        if not valid_urls:
            raise ValueError("Нет корректных ссылок для загрузки")

        payload = {
            "nmId": nm_id,
            "data": valid_urls
        }

        print("📤 Отправляем медиа:")
        for url in valid_urls:
            print(url)

        return await self._make_request(
            "POST",
            "/content/v3/media/save",
            json=payload
        )

    async def upload_mediaFile(self, nm_id: int, file_data: bytes, photo_number: int,
                               media_type: str = 'image') -> WBApiResponse:
        if media_type == 'video' and photo_number != 1:
            return WBApiResponse(success=False, error="Video can only be uploaded to position 1")

        headers = {
            "Authorization": self.api_key,
            "X-Nm-Id": str(nm_id),
            "X-Photo-Number": str(1 if media_type == "video" else photo_number),
        }

        filename = "upload.mp4" if media_type == "video" else "upload.jpg"
        content_type = "video/mp4" if media_type == "video" else "image/jpeg"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/content/v3/media/file",
                    headers=headers,
                    files={"uploadfile": (filename, file_data, content_type)}
                )

            if response.is_success:
                return WBApiResponse(
                    success=True,
                    data=response.json(),
                    wb_response=response.json()
                )
            else:
                return WBApiResponse(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text}",
                    wb_response=response.text
                )
            print("Response status:", response.status_code)
            print("Response text:", response.text)


        except Exception as e:
            return WBApiResponse(success=False, error=str(e))


    async def get_card_by_nm(self, nm_id: int):
        response = await self.get_cards_list()

        if not response.success:
            raise Exception("Не удалось получить список карточек")

        if not isinstance(response.data, dict):
            raise ValueError("Неверный формат данных от API")

        cards = response.data.get("cards", [])

        for card in cards:
            current_nm_id = card.get("nmID")
            if isinstance(current_nm_id, int) and current_nm_id == nm_id:
                return WBApiResponse(
                    success=True,
                    data=card
                )

        return WBApiResponse(
            success=False,
            error="Карточка не найдена"
        )

    async def get_card_by_vendor(self, vendorCode: str) -> WBApiResponse:
        try:
            response = await self.get_cards_list()

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

