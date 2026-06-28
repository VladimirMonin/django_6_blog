# CLI: локальная разработка и импорт контента

Краткая справка по management commands проекта `django_6_blog`.

## Общие правила запуска

Все команды запускаются через `uv` из корня репозитория:

```bash
uv sync --python 3.12
uv run python manage.py <command>
```

Если нужна другая версия Python, выбирай её через `uv`, например `uv sync --python 3.13`. Системный Python через `apt`, `pyenv` или ручную установку для этого проекта не нужен.

## Базовые команды Django

### Применить миграции

```bash
uv run python manage.py migrate
```

### Запустить локальный сервер

```bash
uv run python manage.py runserver 127.0.0.1:8036
```

### Проверить проект

```bash
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

## `collect_note_assets`

Собирает Obsidian/Markdown-заметку и все локальные файлы, на которые она ссылается, в одну плоскую папку assets. Это удобно перед импортом статьи в Django.

### Синтаксис

```bash
uv run python manage.py collect_note_assets NOTE OUTPUT_DIR [options]
```

### Аргументы

- `NOTE` — исходная Markdown/Obsidian-заметка.
- `OUTPUT_DIR` — папка, куда нужно скопировать заметку и медиа.

### Опции

- `--vault-root PATH` — корень Obsidian vault для разрешения vault-relative ссылок вроде `999_files/image.webp`.
- `--clean` — удалить `OUTPUT_DIR` перед копированием.
- `--no-copy-note` — скопировать только медиа, без Markdown-файла.
- `--title TEXT` — записать или заменить `title` во frontmatter копии заметки.
- `--description TEXT` — записать или заменить `description` во frontmatter копии заметки.

### Что понимает команда

- Obsidian embeds: `![[image.webp]]`, `![[image.webp|500]]`, `![[999_files/image.webp|alt]]`.
- Markdown images: `![alt](image.webp)`, `![alt](../image.webp)`.
- Vault-relative и note-relative пути.
- Обычные wikilinks на `.md`-карточки, если они используются в теле статьи.

Команда смотрит ссылки в теле Markdown, а не в служебных frontmatter-полях вроде `related` или `derived_from`.

### Пример для статьи LM Studio №1

```bash
uv run python manage.py collect_note_assets \
  "/home/v/Syncthing/AUTO_OBSIDIAN/10_Lessons/LM Studio/01-токены-параметры-и-встраивания.md" \
  tests/assets/obsidian/lm-studio-lesson-01 \
  --vault-root "/home/v/Syncthing/AUTO_OBSIDIAN" \
  --clean \
  --title "LM Studio: токены, параметры и встраивания" \
  --description "Как локальная LLM превращает текст в токены, числовые представления, embeddings и ответ."
```

`tests/assets/` игнорируется Git и используется только как локальная рабочая папка для smoke-проверок.


## Типы записей и таймкоды

Модель `Post` поддерживает четыре типа контента:

- `article` — обычная статья;
- `video` — видео с HTML5 video-плеером;
- `audio` — аудио с HTML5 audio-плеером;
- `podcast` — подкаст с audio-плеером и отдельным бейджем.

Для медиа-постов можно указать внешний файл во frontmatter:

```yaml
---
title: "Видео выпуск"
description: "Короткое описание для карточки."
type: video
media_url: https://cdn.example.test/video.mp4
cover: cover.webp
tags: [django, video]
---
```

Таймкоды хранятся прямо в Markdown как fenced code block с языком `timecodes`:

````markdown
```timecodes
00:00 Вступление
01:23 — Главная мысль
1:02:03 | Ответы на вопросы
```
````

При импорте блок `timecodes` удаляется из тела статьи, парсится в `Post.timecodes` и на публичной странице рендерится как список кнопок. Клик по кнопке проматывает audio/video-плеер в нужную точку. Для `video`, `audio` и `podcast` CLI валидирует каждую непустую строку блока: формат должен быть `MM:SS Название` или `H:MM:SS Название`, секунды — `00..59`, минуты в часовом формате — `00..59`. Ошибка формата останавливает импорт до записи в БД.

## `create_content_note`

Создаёт Markdown-шаблон для статьи, видео, аудио или подкаста.

```bash
uv run python manage.py create_content_note notes/podcast.md   --title "Подкаст выпуск 1"   --description "Короткое описание подкаста."   --content-type podcast   --tags "django,agents"   --media-url "https://cdn.example.test/podcast.mp3"   --cover "cover.webp"
```

Команда создаёт frontmatter с `title`, `description`, `type`, `tags`, опциональными `media_url` и `cover`, а также заготовкой блока `timecodes` для медиа-типов. По умолчанию существующий файл не перезаписывается; для перезаписи есть `--force`.

## `import_obsidian_note`

Импортирует подготовленную Markdown/Obsidian-заметку в модель `Post` и прикрепляет найденные медиа как `PostMedia`.

### Синтаксис

```bash
uv run python manage.py import_obsidian_note NOTE [options]
```

### Аргументы

- `NOTE` — Markdown-файл, который нужно импортировать.

### Опции

- `--assets-dir PATH` — папка с подготовленными медиа. Если не указана, используется папка самой заметки.
- `--slug SLUG` — явный slug статьи. Если не указан, slug строится из заголовка.
- `--title TEXT` — явный заголовок статьи. Приоритет выше frontmatter.
- `--description TEXT` — явное описание для карточки статьи. Приоритет выше frontmatter.
- `--content-type article|video|audio|podcast` — тип записи. Приоритет выше frontmatter `content_type`/`type`.
- `--media-url URL` — внешний URL основного аудио/видео для плеера.
- `cover` во frontmatter — локальная обложка из `--assets-dir`; поддерживаются `cover.webp`, `images/cover.webp`, `![[cover.webp]]`, `![alt](cover.webp)`. Обложка сохраняется как первый image `PostMedia` и используется в карточке.
- `--replace` — удалить существующий пост с тем же slug и импортировать заново.
- `--check-links` — только проверить локальные ссылки, без создания/изменения поста.

### Приоритет заголовка

Команда выбирает заголовок так:

1. `--title`;
2. `title` из frontmatter;
3. первый H1 в теле заметки;
4. имя файла.

Если первый H1 совпадает с выбранным заголовком, он удаляется из сохраняемого Markdown, чтобы на публичной странице не было дубля заголовка.

### Обязательное описание

Для публичных карточек нужно `description`. Его можно передать одним из способов:

- `description` во frontmatter;
- `--description` при импорте.

Без описания импорт завершается ошибкой.

### Проверить ссылки без записи в БД

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --check-links
```

Ожидаемый успешный результат:

```text
Local links are valid: found=<N>, missing=0
```

### Импортировать или переопубликовать статью

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```

После импорта команда выводит URL, slug, title, description и количество прикреплённых медиа.

## Публикация статьи LM Studio №1 с нуля

Полный локальный сценарий:

```bash
uv run python manage.py collect_note_assets \
  "/home/v/Syncthing/AUTO_OBSIDIAN/10_Lessons/LM Studio/01-токены-параметры-и-встраивания.md" \
  tests/assets/obsidian/lm-studio-lesson-01 \
  --vault-root "/home/v/Syncthing/AUTO_OBSIDIAN" \
  --clean \
  --title "LM Studio: токены, параметры и встраивания" \
  --description "Как локальная LLM превращает текст в токены, числовые представления, embeddings и ответ."

uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --check-links

uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```

Локальные результаты импорта — `db.sqlite3`, `media/posts/*`, `tests/assets/*` — не коммитятся.

## Publisher CLI (`publisher/`)

 standalone-пакет для агентов: читает Markdown/Obsidian-заметку, парсит frontmatter и таймкоды, отправляет JSON через `POST /api/v1/posts/publish/`. Не зависит от Django — только стандартная библиотека (`urllib`, `argparse`, `json`).

### Запуск

```bash
python -m publisher publish note.md --url http://127.0.0.1:8036 --key TOKEN
```

### Переменные окружения

| Переменная | Аналог CLI | Описание |
|---|---|---|
| `BLOG_API_URL` | `--url` | Base URL блога |
| `BLOG_API_KEY` | `--key` | API токен (Bearer) |

### Опции

| Опция | Описание |
|---|---|
| `--title TEXT` | Переопределить заголовок (приоритет над frontmatter) |
| `--description TEXT` | Переопределить описание |
| `--content-type article\|video\|audio\|podcast` | Переопределить тип контента |
| `--media-url URL` | Переопределить URL медиа |
| `--status published\|draft` | Переопределить статус |
| `--slug SLUG` | Явный slug |
| `--replace` | Перезаписать существующий пост с тем же slug |
| `--dry-run` | Парсить и вывести payload без отправки на API |

### Frontmatter

Парсер читает стандартный YAML frontmatter:

```yaml
---
title: "Заголовок"
description: "Описание для карточки"
content_type: video   # или type: video
media_url: https://example.com/v.mp4
tags: Python, Django
category: testing
series: python-basics
series_order: 2
status: published     # или draft
---
```

Поддерживаются русские алиасы: `видео`, `аудио`, `подкаст`, `статья`.

`category` и `series` независимы: категория нужна для группировки в ленте, серия — для линейной навигации `prev/next` на detail page. `series_order` определяет позицию поста внутри серии.

### Таймкоды

Блок ````timecodes` извлекается, парсится и отправляется как JSON-массив:

````markdown
```timecodes
0:00 Intro
2:57 Demo
1:00:00 One hour
```
````

### Dry run

```bash
python -m publisher publish note.md --dry-run
```

Выводит JSON payload без отправки на API — удобно для отладки парсинга.

### Примеры

```bash
# Опубликовать заметку
python -m publisher publish path/to/note.md

# Как черновик
python -m publisher publish note.md --status draft

# Перезаписать существующий
python -m publisher publish note.md --replace

# Через env vars
export BLOG_API_URL=http://127.0.0.1:8036
export BLOG_API_KEY=your-token-here
python -m publisher publish note.md
```

## Что нельзя коммитить

Перед коммитом проверь staged-файлы:

```bash
git diff --cached --name-only
git diff --cached --name-only | grep -E '(^|/)(\.env$|\.venv|db\.sqlite3$)|^media/posts/|^tests/assets/' || true
```

В commit не должны попадать:

- `.env`;
- `.venv/`;
- `db.sqlite3`;
- `media/posts/*`;
- `tests/assets/*`;
- `__pycache__/`, `*.pyc`.
