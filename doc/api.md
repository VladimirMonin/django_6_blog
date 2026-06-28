# Blog API

API для агент-управляемой публикации постов. Все эндпоинты под `/api/v1/` с namespace `api`.

## Авторизация

Token-based auth через `Authorization: Bearer <token>`.

API ключи создаются и управляются через Django admin (`/admin/api/apikey/`). Каждый ключ:

- **name** — название (например «Hermes agent»)
- **token** — автогенерируется через `secrets.token_urlsafe(32)` (43 символа)
- **is_active** — можно отозвать одним кликом
- **last_used_at** — обновляется при каждом запросе

## Эндпоинты

### POST /api/v1/posts/publish/

Создаёт или обновляет пост из JSON-пayload.

**Заголовки:**

```
Authorization: Bearer <token>
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
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Новый пост",
    "description": "Краткое описание",
    "content": "# Привет\n\nТекст поста.",
    "tags": ["Python", "Django"],
    "category": "Testing"
  }'
```

## Планируемые эндпоинты

- `GET /api/v1/posts/` — список опубликованных постов (search, filter, paginate)
- `GET /api/v1/posts/<slug>/` — детали поста
- `PATCH /api/v1/posts/<slug>/status/` — publish/unpublish
- `GET /api/v1/stats/` — статистика посещений и реакций
- `POST /api/v1/posts/publish/` с multipart media upload
- `DELETE /api/v1/posts/<slug>/` — удаление поста