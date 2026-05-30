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
