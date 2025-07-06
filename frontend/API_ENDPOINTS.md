# API Endpoints для аналитики

## Общие endpoints

### 1. Получение списка магазинов пользователя
```
GET /analytics/shops
Authorization: Bearer {token}
```
**Ответ:**
```json
[
  {
    "id": "shop_id",
    "name": "Название магазина",
    "status": "active"
  }
]
```

### 2. Получение отзывов с фильтрацией
```
GET /analytics/reviews
Authorization: Bearer {token}
```
**Параметры:**
- `page` (int) - номер страницы
- `per_page` (int) - количество на странице
- `search` (string) - поиск по тексту
- `rating` (int) - фильтр по рейтингу (1-5)
- `shop` (string) - ID магазина
- `date_from` (date) - дата начала
- `date_to` (date) - дата окончания
- `negative` (boolean) - только негативные/позитивные

**Ответ:**
```json
{
  "reviews": [
    {
      "id": "review_id",
      "text": "Текст отзыва",
      "rating": 4,
      "author_name": "Имя автора",
      "product_name": "Название товара",
      "shop_name": "Название магазина",
      "created_at": "2024-01-01T00:00:00Z",
      "photos": ["url1", "url2"],
      "sentiment": "positive|negative|neutral",
      "is_processed": true,
      "is_deleted": false
    }
  ],
  "total": 100
}
```

## BrandShopsPage endpoints

### 3. Получение данных магазина
```
GET /analytics/shop/{shop_id}
Authorization: Bearer {token}
```
**Параметры:**
- `start_date` (date) - дата начала периода
- `end_date` (date) - дата окончания периода

**Ответ:**
```json
{
  "total_reviews": 1000,
  "average_rating": 4.2,
  "negative_reviews": 150,
  "five_star_reviews": 600,
  "products": [
    {
      "name": "Название товара",
      "rating": 4.5,
      "period_rating": 4.3,
      "five_stars_before_upgrade": "Заглушка",
      "ratings_count": {
        "5": 50,
        "4": 30,
        "3": 15,
        "2": 3,
        "1": 2
      }
    }
  ],
  "negative_tops": [
    {
      "product_name": "Товар",
      "negative_count": 25
    }
  ],
  "negative_percentage_tops": [
    {
      "product_name": "Товар",
      "negative_percentage": 15.5
    }
  ],
  "internal_negative_tops": [
    {
      "product_name": "Товар",
      "internal_negative_percentage": 20.0
    }
  ]
}
```

### 4. Получение товаров магазина
```
GET /analytics/shop/{shop_id}/products
Authorization: Bearer {token}
```
**Ответ:**
```json
[
  {
    "id": "product_id",
    "name": "Название товара"
  }
]
```

## ReputationEfficiencyPage endpoints

### 5. Получение данных эффективности
```
GET /analytics/efficiency/{shop_id}
Authorization: Bearer {token}
```
**Параметры:**
- `start_date` (date) - дата начала периода
- `end_date` (date) - дата окончания периода
- `product_id` (string, optional) - ID товара

**Ответ:**
```json
{
  "total_reviews": 1000,
  "negative_count": 150,
  "negative_percentage": 0.15,
  "deleted_count": 50,
  "deleted_percentage": 0.05,
  "response_time_avg": 24.5,
  "processed_count": 800,
  "pending_count": 200,
  "ratings_distribution": {
    "5": 600,
    "4": 250,
    "3": 100,
    "2": 30,
    "1": 20
  },
  "negative_trend": [
    {
      "date": "2024-01-01",
      "count": 5
    }
  ],
  "deleted_trend": [
    {
      "date": "2024-01-01",
      "count": 2
    }
  ]
}
```

## ShopsSummaryPage endpoints

### 6. Получение сводки по магазинам
```
GET /analytics/shops-summary
Authorization: Bearer {token}
```
**Параметры:**
- `start_date` (date) - дата начала периода
- `end_date` (date) - дата окончания периода

**Ответ:**
```json
[
  {
    "id": "shop_id",
    "name": "Название магазина",
    "total_reviews": 1000,
    "average_rating": 4.2,
    "negative_reviews": 150,
    "five_star_reviews": 600,
    "negative_percentage": 0.15,
    "five_star_percentage": 0.6,
    "status": "active",
    "is_processing": false,
    "top_products": [
      {
        "name": "Товар",
        "rating": 4.5
      }
    ]
  }
]
```

## Примечания

1. **Аутентификация**: Все endpoints требуют Bearer token в заголовке Authorization
2. **Даты**: Формат дат - YYYY-MM-DD
3. **Пагинация**: Для списков используется пагинация с параметрами page и per_page
4. **Фильтрация**: Поддерживается фильтрация по различным параметрам
5. **Обработка ошибок**: Все endpoints возвращают стандартные HTTP коды ошибок
6. **Форматирование**: Числа форматируются на фронтенде, даты в ISO формате

## Примеры использования

### Получение отзывов с фильтрацией
```bash
curl -X GET "http://localhost:8000/analytics/reviews?page=1&per_page=20&rating=5&negative=true" \
  -H "Authorization: Bearer your_token"
```

### Получение данных магазина за период
```bash
curl -X GET "http://localhost:8000/analytics/shop/shop_id?start_date=2024-01-01&end_date=2024-01-31" \
  -H "Authorization: Bearer your_token"
``` 