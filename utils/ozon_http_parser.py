import aiohttp
import asyncio
from typing import List, Dict, Any

async def parse_feedbacks_optimized(article: int, max_count: int = 1000) -> List[Dict[str, Any]]:
    # Примерный публичный endpoint Ozon для отзывов (может потребоваться актуализация)
    url = f'https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/product/{article}/review'
    headers = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    }
    all_feedbacks = []
    seen = set()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # Путь к отзывам может отличаться, пример ниже для composer-api.bx/page/json/v2
            reviews = []
            try:
                widgets = data.get('widgetStates', {})
                for k, v in widgets.items():
                    if k.startswith('webProductReviews'):  # ищем виджет отзывов
                        reviews = v.get('reviews', [])
                        break
            except Exception:
                pass
            for fb in reviews:
                key = (fb.get('author', 'Аноним'), fb.get('date'), fb.get('text', ''))
                if key in seen:
                    continue
                seen.add(key)
                all_feedbacks.append({
                    'author': fb.get('author', 'Аноним'),
                    'date': fb.get('date'),
                    'status': fb.get('moderationStatus', ''),
                    'rating': fb.get('rating', 0),
                    'text': fb.get('text', ''),
                    'article': article
                })
                if len(all_feedbacks) >= max_count:
                    return all_feedbacks[:max_count]
    return all_feedbacks[:max_count] 