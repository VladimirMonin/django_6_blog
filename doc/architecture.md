# Архитектура проекта

`django_6_blog` — монолитное Django-приложение для публичного блога и контентной платформы с Markdown/Obsidian импортом.

## Текущий стек

- Python `>=3.12`, окружение через `uv`.
- Django `6.0.x`.
- SQLite — текущая база разработки.
- Bootstrap 5 + django-components для SSR UI.
- HTMX для поиска, догрузки карточек и реакций без SPA.
- Python Markdown + `pymdown-extensions` + BeautifulSoup-процессоры для HTML.
- Mermaid + `svg-pan-zoom` на фронтенде для диаграмм.

## Основные зоны

- `config/` — настройки Django и root URL routing.
- `blog/models.py` — доменная модель публичных записей, медиа и session interactions.
- `blog/views.py` — class-based public views: список, деталка, about, toggle-like.
- `blog/content_import/` — доменная логика импорта Markdown/Obsidian контента.
- `blog/services/` — Markdown → HTML pipeline и HTML processors.
- `blog/management/commands/` — CLI для генерации заметок, сбора assets и импорта.
- `blog/components/` — django-components для повторяемого UI.
- `templates/blog/` — публичные страницы и partials.
- `static/css/`, `static/js/` — внешний вид и небольшие интерактивные сценарии.

## Данные

Главные модели:

- `Category` — публичная категория записи.
- `Tag` — сквозная тема записи.
- `Post` — запись блога с Markdown body, cached HTML, status, type, media URL, timecodes, счётчиками.
- `PostMedia` — файл, прикреплённый к одному посту: image/video/audio/document/other.
- `SessionPostInteraction` — централизованная история anonymous session interactions для просмотров и лайков.

## Посты и публикация

`Post.status` имеет два пользовательских состояния:

- `published` — запись видна в ленте и на detail page;
- `draft` — запись скрыта и detail URL возвращает `404`.

Публичные URL записей slug-only. Числовой ID в URL не используется.

`Post.description` обязателен и служит источником текста карточки. Карточки не должны брать excerpt из сырого Markdown body.

## Markdown → HTML

При сохранении `Post` Markdown конвертируется в `content_html`. Detail template использует `body_content_html`, чтобы не показывать дублирующий H1, если заголовок уже вынесен в header страницы.

Pipeline:

1. `MarkdownMediaPreprocessor` связывает локальные media references с `PostMedia`.
2. Python Markdown конвертирует Markdown в HTML.
3. BeautifulSoup processors добавляют проектные классы для таблиц, изображений, callouts и code.
4. Mermaid blocks экранируют исходник и рендерятся как управляемые pan/zoom диаграммы.

Любой HTML, который потом идёт в template через `|safe`, считается security boundary: пользовательский исходник нужно экранировать, а локальные пути assets не должны выходить за `assets_dir`.

## Публичный UI

Список постов использует обычные SEO-friendly ссылки пагинации. HTMX добавляет progressive enhancement: поиск и догрузка карточек возвращают partial templates, но без HTMX страница остаётся рабочей.

Detail page отвечает за:

- заголовок, badges и meta;
- основной video/audio player для медиа-постов;
- кликабельные таймкоды;
- Markdown body;
- сессионные реакции.

## Сессионные реакции

Просмотры и лайки не хранятся в session dict разрозненно. Источник истории — `SessionPostInteraction` с `session_key` и `post`. Счётчики на `Post` обновляются через централизованную service/mixin-логику.

## Архитектурные границы

- Импорт контента не должен расползаться в templates или views: доменная логика живёт в `blog/content_import/`.
- Markdown rendering не должен дублироваться в разных местах: общий вход — `convert_markdown_to_html`.
- Public views должны фильтровать только `published` записи.
- UI polishing должен закрываться тестами и browser/visual QA, когда меняется видимая поверхность.
- SQLite-only остаётся текущей границей, пока Postgres/pgvector не выделены в отдельный слайс.
