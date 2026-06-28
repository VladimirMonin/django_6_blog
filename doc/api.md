# Blog API

API для агент-управляемой публикации постов. Все эндпоинты под `/api/v1/` с namespace `api`.

## Авторизация

Token-based auth через заголовок `Authorization: Bearer TOKEN`.

API ключи создаются и управляются через Django admin (`/admin/api/apikey/`). Каждый ключ:

- **name** — название (например «Hermes agent»)
- **token** — автогенерируется через `secrets.token_urlsafe(32)` (43 символа)
- **is_active** — можно отозвать одним кликом
- **last_used_at** — обновляется при каждом запросе

## Endpoints

### POST /api/v1/posts/publish/

Создаёт или обновляет пост из JSON-payload.

**Заголовки:**

```
Authorization: Bearer TOKEN
Content-Type: application/json
```

**Обязательные поля:**

| Поле | Тип | Описание |
|---|---|---|
| `title` | string | Заголовок поста |
| `description` | string | Описание (для карточек, OG meta, excerpt) |
| `content` | string | Markdown-контент поста |

**Опциональные поля:**

| Поле | Тип | Default | Описание |
|---|---|---|---|
| `content_type` | string | `article` | article/video/audio/podcast |
| `media_url` | string | `""` | Внешний URL медиа для плеера |
| `timecodes` | list | `[]` | `[{time: "0:00", label: "Intro"}, ...]` |
| `tags` | list | `[]` | Список строк, создаются если не существуют |
| `category` | string | `null` | Название категории, создаётся если не существует |
| `series` | string | `null` | Название серии, создаётся если не существует |
| `series_order` | int | `0` | Порядок поста внутри серии |
| `status` | string | `published` | `published` или `draft` |
| `slug` | string | auto | Явный slug, иначе генерируется из title |
| `replace` | bool | `false` | Переписать существующий пост с тем же slug |

**Ответы:**

| Код | Описание |
|---|---|
| 201 | Пост создан, возвращает serialized post |
| 400 | Ошибка валидации — отсутствуют обязательные поля |
| 401 | Неверный или отсутствует API ключ |
| 409 | Slug занят и `replace=false` |

**Пример:**

```bash
curl -X POST https://blog.example.com/api/v1/posts/publish/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Новый пост",
    "description": "Краткое описание",
    "content": "# Привет\n\nТекст поста.",
    "tags": ["Python", "Django"],
    "category": "Testing",
    "series": "Python Basics",
    "series_order": 2
  }'
```

## Дополнительные эндпоинты

### POST /api/v1/posts/bulk/

Массовая публикация нескольких постов одним запросом.

**Permission:** `publish`

```json
{
  "posts": [
    {"title": "Post 1", "description": "...", "content": "..."},
    {"title": "Post 2", "description": "...", "content": "..."}
  ]
}
```

Возвращает `results` с успехом/ошибкой для каждого поста.

### GET /api/v1/posts/

Список постов для агентов.

Поддерживает фильтры:

- `status=published|draft|archived`
- `content_type=article|video|audio|podcast`
- `category=<slug-or-name>`
- `search=<text>`
- `sort=created_at|-created_at|title|-title|view_count|-view_count|published_at|-published_at`
- `page=<n>`
- `per_page=<1..100>`

Ответ содержит `results` и `pagination`.

### GET /api/v1/posts/<slug>/

Возвращает полную serialized-структуру поста, включая `content`, `timecodes`, `series`, `series_order`.

**Permission:** `delete` (DELETE requires delete permission)

### PATCH /api/v1/posts/<slug>/status/

Меняет статус поста: `published`, `draft` или `archived`.

**Permission:** `status`

### DELETE /api/v1/posts/<slug>/

Мягкое удаление (soft delete): устанавливает `deleted_at` и переводит в `archived`. Пост остаётся в БД, но скрыт с публичного сайта и из API.

**Permission:** `delete`

### GET /api/v1/stats/

Агрегатная статистика: количество постов по статусам, типам, топ-5 категорий, суммарные просмотры/лайки, featured count.

**Permission:** `stats`

### GET /api/v1/health/

Публичный health-check. Без API ключа. Возвращает status, DB status, post count, version.

### POST /api/v1/posts/<slug>/read-depth/

Публичный endpoint для трекинга глубины чтения. Без API ключа. Принимает `{"read_depth": 0.0-1.0}`.

## Permissions

API keys имеют список разрешений (JSON field `permissions`):

| Permission | Endpoints |
|---|---|
| `read` | GET list, GET detail |
| `publish` | POST publish, POST bulk |
| `delete` | DELETE post |
| `status` | PATCH status |
| `stats` | GET stats |

Новые ключи по умолчанию получают все разрешения.

## Rate Limiting

Each API key is limited to 60 requests per minute. Exceeding returns `429` with `{"error": "Rate limit exceeded", "retry_after": N}`.

## Idempotent Publishing

Если в payload указан `source_id`, и пост с таким `source_id` уже существует, он будет обновлён (эквивалент `replace=true`).