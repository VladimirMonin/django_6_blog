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

### GET /api/v1/posts/

Список постов для агентов.

Поддерживает фильтры:

- `status=published|draft`
- `content_type=article|video|audio|podcast`
- `category=<slug-or-name>`
- `search=<text>`
- `page=<n>`
- `per_page=<1..100>`

Ответ содержит `results` и `pagination`.

### GET /api/v1/posts/<slug>/

Возвращает полную serialized-структуру поста, включая `content`, `timecodes`, `series`, `series_order`.

### PATCH /api/v1/posts/<slug>/status/

Меняет статус поста между `published` и `draft`.

### DELETE /api/v1/posts/<slug>/

Удаляет пост по slug.

## Planned

- `GET /api/v1/stats/` — статистика посещений и реакций
- multipart upload для медиа через API