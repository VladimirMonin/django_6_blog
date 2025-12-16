# Фаза 4.3: Модель TextChunk

## Цель

Создать модель `TextChunk` — атомарную единицу знаний для семантического поиска.

---

## Контекст

`TextChunk` — центральная сущность поисковой системы. Каждый чанк представляет собой фрагмент статьи (абзац текста, блок кода, описание диаграммы), обогащённый:
- Векторным представлением для семантического поиска
- Метаданными для контекстной навигации
- Типом контента для дифференцированной обработки

Ключевое архитектурное решение — использование `halfvec(1536)` вместо `vector(1536)`. Это FP16 тип, который экономит 50% памяти с минимальной потерей точности (доли процента). Для модели OpenAI `text-embedding-3-small` размерность 1536.

Поле `content_hash` (SHA256) обеспечивает идемпотентность: при повторной индексации неизменённые чанки пропускаются, экономя API-вызовы.

**Философия:** Чанк должен "знать" своё место в структуре документа.

**Документация:**
- [ИИ поиск на базе смыслов — концепция](../researches/report_6/ИИ%20поиск%20на%20базе%20смыслов%20-%20концепция.md) — раздел "Расширенная концептуальная модель данных"
- [Django, pgvector: семантический поиск локально](../researches/report_6/Django,%20pgvector_%20семантический%20поиск%20локально.md) — раздел 4.1 "Проектирование схемы данных"

---

## Задачи

### Создание модели

- [ ] Создать файл `blog/models/text_chunk.py` (или добавить в существующий `models.py`)
- [ ] Определить модель `TextChunk` со следующими полями:

**Основные поля:**
- `post` — ForeignKey на Post, CASCADE, related_name='chunks'
- `content` — TextField, текст или код чанка
- `section_title` — CharField(255), заголовок секции H2/H3 (для "хлебных крошек")
- `position_index` — PositiveIntegerField, порядковый номер в статье

**Типизация:**
- `chunk_type` — CharField с choices: TEXT, CODE, MERMAID_DESC, IMAGE_DESC
- `code_language` — CharField(50), nullable, язык для CODE (python, javascript и т.д.)

**Векторизация:**
- `embedding` — VectorField(dimensions=1536), nullable (заполняется после векторизации)
- `content_hash` — CharField(64), SHA256 хеш контента, db_index=True

**FTS:**
- `search_vector` — SearchVectorField, nullable (для полнотекстового поиска)

### Создание Enum для типов

- [ ] Определить `ChunkType` как TextChoices с вариантами TEXT, CODE, MERMAID_DESC, IMAGE_DESC

### Индексы

- [ ] HNSW индекс на `embedding` с параметрами m=16, ef_construction=64, opclasses=['vector_cosine_ops']
- [ ] GIN индекс на `search_vector` для FTS
- [ ] B-Tree индекс на `content_hash` для быстрой проверки дубликатов
- [ ] Composite индекс на (`post`, `position_index`) для загрузки контекста

### Миграция

- [ ] Сгенерировать миграцию: `python manage.py makemigrations`
- [ ] Применить миграцию: `python manage.py migrate`
- [ ] Проверить создание таблицы и индексов через psql

### Meta-опции

- [ ] Установить `ordering = ['post', 'position_index']`
- [ ] Добавить `verbose_name` и `verbose_name_plural` для админки

---

## Тестирование

- [ ] Создать тестовый чанк через Django shell
- [ ] Проверить, что чанк сохраняется с пустым embedding (nullable)
- [ ] Проверить каскадное удаление при удалении поста

---

## Коммит

```
phase 4.3 feat: Модель TextChunk
- Создана модель TextChunk с полями content, embedding, chunk_type
- Добавлен ChunkType enum (TEXT, CODE, MERMAID_DESC, IMAGE_DESC)
- Настроены индексы HNSW, GIN, B-Tree
- Добавлено поле content_hash для идемпотентности
```
