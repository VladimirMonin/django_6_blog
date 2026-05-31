# Публичный UI

Публичный UI строится как SSR-first Django приложение с HTMX progressive enhancement.

## Лента постов

`PostListView` показывает только `Post.status = published`.

Поддерживаются query parameters:

- `search` — поиск по заголовку, Markdown-контенту, категории и тегам;
- `category` — slug категории;
- `tag` — slug тега;
- `page` — номер страницы.

Пагинация остаётся обычными ссылками. HTMX используется для частичного обновления списка и догрузки карточек, но не должен ломать обычную навигацию без JavaScript.

## Поиск по кириллице

SQLite `icontains` ограничен ASCII-поведением, поэтому для не-ASCII поисковых строк используется дополнительный Python `casefold` pass по уже ограниченному queryset. Если поиск или фильтры меняются, нужно проверять кириллицу отдельно.

## Карточки

Карточка должна использовать:

- `Post.description` для excerpt;
- `cover_media` как обложку, если есть image media;
- type badge для `article`/`video`/`audio`/`podcast`;
- placeholder для no-cover состояний;
- category/tag links как обычные URL.

Не показывай сырой Markdown, frontmatter, служебные blocks или первый H1 внутри карточки.

## Detail page

Detail page отвечает за:

- header с title, badges, tags и author meta;
- session reactions;
- основной media player для media posts;
- timecodes panel;
- rendered Markdown body;
- back link к списку.

`draft` записи не должны открываться публично.

## HTMX partials

HTMX partials должны возвращать только нужный фрагмент:

- search/filter update — список карточек + связанную UI-обвязку;
- load more — только дополнительные карточки;
- like toggle — только reactions block.

Обычный full-page response должен оставаться корректным для тех же URL.

## Reactions

Просмотры и лайки anonymous-session based:

- один просмотр поста на одну session;
- лайк переключаемый, один активный лайк на session/post;
- история хранится в `SessionPostInteraction`;
- агрегаты `view_count` и `like_count` живут на `Post`.

## Visual QA

Если меняется видимая поверхность:

1. Запусти релевантные tests.
2. Проверь страницу в браузере.
3. Посмотри console errors.
4. Для пользовательского visual feedback приложи 2–4 читаемых WebP-кропа, а не огромные full-page screenshots.
5. Перед отправкой проверь кроп глазами: важный UI не должен быть пустым, мыльным или обрезанным.
