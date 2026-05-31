# Django 6 Blog

Экспериментальный блог на Django 6: SSR + HTMX, Bootstrap 5, django-components, Markdown и локальные медиа.

## Локальный запуск через uv

Проект использует только `uv` как менеджер окружения и зависимостей.

```bash
uv sync --python 3.12
uv run python manage.py migrate
uv run python manage.py runserver
```

Если нужна другая версия Python, выбираем её через `uv`, например `uv sync --python 3.12` — без системной установки Python.

## Переменные окружения

Для локальной разработки можно скопировать пример:

```bash
cp .env.example .env
```

Файл `.env` не коммитится. Приложение читает значения из process environment:

- `DJANGO_SECRET_KEY` — секрет Django для локального/production окружения.
- `DJANGO_DEBUG` — `true`/`false`.
- `DJANGO_ALLOWED_HOSTS` — список host через запятую.

Проект сейчас остаётся SQLite-only. `DATABASE_URL`, Postgres и Docker Compose не добавлены намеренно.

## Проверки

```bash
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

Подробные рабочие правила, smoke-gates и список того, что нельзя коммитить: [`doc/development.md`](doc/development.md).
CLI-команды для сборки assets и импорта Obsidian-статей: [`doc/cli.md`](doc/cli.md).

## Публичный блог

Реализовано:

- обязательное описание записи `Post.description`, импортируемое из frontmatter `description`;
- типы записей: `article`, `video`, `audio`, `podcast`;
- HTML5-плееры для видео/аудио/подкастов через `media_url` или импортированный медиафайл;
- обложки медиа-постов через frontmatter `cover`;
- кликабельные таймкоды из Markdown-блока ```` ```timecodes ```` с промоткой плеера;
- строгая CLI-валидация таймкодов для `video`, `audio` и `podcast`;
- карточки используют `description`, а не начало Markdown-статьи;
- статусы постов: `published` и `draft`;
- публично видны только опубликованные посты;
- категории;
- теги и карта тегов с количеством опубликованных постов;
- slug-only маршруты статей без числовых ID;
- серверные хлебные крошки на странице статьи;
- автор сайта по умолчанию: Владимир Монин;
- поиск по заголовку, Markdown-контенту, категории и тегам;
- обычные SEO-friendly ссылки пагинации;
- HTMX-поиск и догрузка карточек без полной перезагрузки страницы;
- paginator остаётся обычной ссылочной навигацией для поисковых роботов;
- class-based views для публичных страниц;
- просмотры и лайки через анонимные Django sessions с централизованной историей `SessionPostInteraction`.

## Импорт локальной Obsidian-статьи

Реальные заметки и медиа для локальной проверки держим в ignored-папке `tests/assets/`.

Сначала можно собрать заметку и все локальные медиа/связанные `.md`-карточки в одну папку:

```bash
uv run python manage.py collect_note_assets \
  "/path/to/vault/10_Lessons/LM Studio/01-токены-параметры-и-встраивания.md" \
  tests/assets/obsidian/lm-studio-lesson-01 \
  --vault-root "/path/to/vault" \
  --clean \
  --title "LM Studio: токены, параметры и встраивания" \
  --description "Короткое описание для карточки."
```

Команда понимает Obsidian embeds `![[999_files/image.webp|500]]` и Markdown images `![alt](../image.webp)`, копирует найденные файлы в плоскую assets-папку и может сразу дописать `title`/`description` в копию заметки.

```bash
uv run python manage.py import_obsidian_note \
  tests/assets/obsidian/lm-studio-lesson-01/01-токены-параметры-и-встраивания.md \
  --assets-dir tests/assets/obsidian/lm-studio-lesson-01 \
  --slug lm-studio-lesson-01 \
  --replace
```

Frontmatter должен содержать `description`: именно оно показывается в карточках.
Если `title` не передан явно и отсутствует во frontmatter, импорт берёт первый H1 из тела заметки как заголовок поста. Дублирующий первый H1 затем удаляется из сохраняемого Markdown, чтобы публичная статья не показывала два одинаковых заголовка.
Автор статьи не хранится в Obsidian/frontmatter: сайт использует дефолтного автора из Django-настроек (`SITE_AUTHOR`).
Для сухой проверки локальных Markdown/Obsidian ссылок без создания поста:

```bash
uv run python manage.py import_obsidian_note path/to/article.md --assets-dir path/to/assets --check-links
```


### Медиа-записи и таймкоды

Для видео, аудио и подкастов во frontmatter можно указать:

```yaml
type: video
media_url: https://cdn.example.test/video.mp4
cover: cover.webp
```

Таймкоды пишутся в Markdown отдельным блоком:

````markdown
```timecodes
00:00 Вступление
01:23 — Главная мысль
1:02:03 | Ответы на вопросы
```
````

Импорт сохраняет их в `Post.timecodes`, убирает служебный блок из тела статьи и рендерит на публичной странице кнопки, которые проматывают audio/video-плеер. Для медиа-типов каждая непустая строка блока валидируется: `MM:SS Название` или `H:MM:SS Название`; некорректный блок останавливает импорт до записи в БД.

Создать заготовку можно CLI-командой:

```bash
uv run python manage.py create_content_note notes/podcast.md   --title "Подкаст выпуск 1"   --description "Короткое описание подкаста."   --content-type podcast   --tags "django,agents"   --media-url "https://cdn.example.test/podcast.mp3"   --cover "cover.webp"
```
