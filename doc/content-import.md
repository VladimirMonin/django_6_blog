# Импорт Markdown и Obsidian контента

Проект импортирует локальные Markdown/Obsidian заметки в модель `Post` и прикрепляет найденные медиа как `PostMedia`.

## Главный сценарий

1. Подготовить заметку и assets через `collect_note_assets`.
2. Проверить локальные ссылки через `import_obsidian_note --check-links`.
3. Импортировать или заменить запись через `import_obsidian_note --replace`.
4. Проверить публичный render: карточка, detail page, media, ссылки.

Подробные команды: [`cli.md`](cli.md).

## Frontmatter

Минимальное поле для публичной карточки:

```yaml
---
title: "Заголовок"
description: "Короткое описание для карточки."
tags: [django, agents]
---
```

`description` обязателен. Без него импорт должен завершаться ошибкой до записи в БД.

Заголовок выбирается по приоритету:

1. `--title` CLI;
2. `title` во frontmatter;
3. первый H1 в теле заметки;
4. имя файла.

Если первый H1 совпадает с выбранным заголовком, он удаляется из сохраняемого body, чтобы публичная статья не показывала дубль.

## Автор

Автор публичного сайта не хранится в Obsidian/frontmatter. Сайт использует дефолтного автора из Django-настроек/context processor. Импорт отвечает за контент, описание, slug, медиа и связи, но не за авторство.

## Поддерживаемые ссылки

Импорт поддерживает:

- Obsidian embeds: `![[image.webp]]`, `![[image.webp|500]]`, `![[folder/image.webp|alt]]`;
- Markdown images: `![alt](image.webp)`, `![alt](../image.webp)`;
- wikilinks на `.md`-карточки в теле статьи;
- note-relative и vault-relative пути через `collect_note_assets --vault-root`;
- поиск медиа по полному имени и stem: `cover` может найти `cover.webp`.

Frontmatter-поля вроде `related` или `derived_from` не считаются обязательными локальными ссылками для `collect_note_assets`.

## Границы assets

Любой локальный путь из заметки или frontmatter должен оставаться внутри объявленной `assets_dir`. Выход за `assets_dir` — ошибка, а не silent fallback.

`tests/assets/` используется только как ignored локальная папка для smoke-проверок. Эти файлы не коммитятся.

## Медиа

`PostMedia` создаётся для найденных локальных файлов. Тип определяется по расширению:

- images: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`;
- video: `.mp4`, `.webm`, `.mov`, `.avi`, `.mkv`;
- audio: `.mp3`, `.wav`, `.ogg`, `.opus`, `.m4a`, `.flac`;
- documents: `.pdf`, `.txt`, `.md`, `.doc`, `.docx`.

Для медиа-постов основной audio/video embed в Markdown body удаляется после создания `PostMedia`, потому что главный player уже рендерится над таймкодами. Это защищает detail page от второго дублирующего плеера ниже таймкодов.

## Slug

Slug можно передать явно через `--slug`. Если slug строится автоматически, для кириллицы используется проектный helper transliteration/slugification, а дубли должны получать суффикс вроде `-2`.

## Dry link-check

Перед импортом реальной заметки используй:

```bash
uv run python manage.py import_obsidian_note path/to/note.md \
  --assets-dir path/to/assets \
  --check-links
```

Успешный результат должен явно показывать, что missing links равны нулю.
