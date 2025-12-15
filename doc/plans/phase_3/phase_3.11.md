# Фаза 3.11: Утилита распаковки ZIP-архивов

## Цель

Создать `blog/services/archive_handler.py` с функциями для безопасной работы с ZIP-архивами: распаковка, поиск Markdown и медиа-файлов, очистка временных директорий.

## Контекст

**Текущее состояние:** В [blog/services/](../../../blog/services/) есть препроцессор и конвертеры. Нет инструментов для работы с архивами.

**Проблема:** Obsidian экспортирует заметки как ZIP с Markdown-файлом и папкой attachments. Нужно распаковать, найти нужные файлы, обработать, и безопасно удалить временные данные.

**Решение:** Набор утилитных функций для низкоуровневой работы с ZIP. Эти функции будут использоваться в PostImporter (Phase 3.12) для импорта постов.

**Технологии:** Встроенные модули Python — `zipfile` для работы с архивами, `tempfile` для временных директорий, `pathlib` для работы с путями, `mimetypes` для определения типов файлов.

**Философия:** "Safe Extraction First". Защита от zip bombs, path traversal атак, ограничение размера архивов. Никогда не доверяем содержимому архивов.

**Важно:** Path traversal — атака через имена файлов типа `../../etc/passwd`. Python zipfile с `extractall()` уязвим в старых версиях. Используем проверку путей или `extract()` с контролем.

## Задачи

### Создание файла archive_handler.py

- [ ] Создать файл `blog/services/archive_handler.py`
- [ ] Добавить docstring модуля:

```python
"""Утилиты для работы с ZIP-архивами при импорте постов.

Безопасная распаковка, поиск файлов, валидация и очистка.
"""
```

- [ ] Импортировать модули:

```python
import zipfile
import tempfile
import mimetypes
from pathlib import Path
from typing import Optional, List, Tuple
```

### Функция extract_zip

- [ ] Создать функцию `extract_zip(zip_path: Path, max_size_mb: int = 100) -> Path`:
- [ ] Добавить docstring: "Безопасно распаковывает ZIP в временную директорию. Возвращает путь к temp dir."
- [ ] Проверить размер архива:

```python
if zip_path.stat().st_size > max_size_mb * 1024 * 1024:
    raise ValueError(f"Архив слишком большой (max {max_size_mb} MB)")
```

- [ ] Создать временную директорию: `temp_dir = Path(tempfile.mkdtemp(prefix='blog_import_'))`
- [ ] Открыть архив и проверить целостность:

```python
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    # Проверить на path traversal
    for member in zip_ref.namelist():
        member_path = Path(member)
        if member_path.is_absolute() or '..' in member_path.parts:
            raise ValueError(f"Опасный путь в архиве: {member}")
    
    zip_ref.extractall(temp_dir)
```

- [ ] Вернуть `temp_dir`

### Функция find_markdown_file

- [ ] Создать функцию `find_markdown_file(directory: Path) -> Optional[Path]`:
- [ ] Добавить docstring: "Находит первый .md файл в директории (рекурсивно)."
- [ ] Искать рекурсивно: `md_files = list(directory.rglob('*.md'))`
- [ ] Если найдено несколько, вернуть первый (можно добавить сортировку по размеру — самый большой)
- [ ] Если не найдено, вернуть None:

```python
if md_files:
    # Вернуть самый большой файл (основная статья)
    return max(md_files, key=lambda f: f.stat().st_size)
return None
```

### Функция find_media_files

- [ ] Создать функцию `find_media_files(directory: Path) -> List[Tuple[Path, str]]`:
- [ ] Добавить docstring: "Находит все медиа-файлы в директории. Возвращает список (path, mime_type)."
- [ ] Определить whitelist расширений:

```python
ALLOWED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp',  # Images
    '.mp4', '.webm', '.mov', '.avi',  # Video
    '.mp3', '.wav', '.ogg', '.m4a',  # Audio
    '.pdf', '.txt', '.md'  # Documents
}
```

- [ ] Рекурсивно найти все файлы:

```python
media_files = []
for file_path in directory.rglob('*'):
    if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
        mime_type, _ = mimetypes.guess_type(file_path)
        media_files.append((file_path, mime_type or 'application/octet-stream'))
return media_files
```

### Функция cleanup_temp

- [ ] Создать функцию `cleanup_temp(temp_dir: Path) -> None`:
- [ ] Добавить docstring: "Безопасно удаляет временную директорию со всем содержимым."
- [ ] Использовать `shutil.rmtree`:

```python
import shutil

if temp_dir.exists() and temp_dir.is_dir():
    shutil.rmtree(temp_dir)
```

- [ ] Добавить try-except для обработки ошибок:

```python
try:
    shutil.rmtree(temp_dir)
except Exception as e:
    # Логировать но не падать
    print(f"Warning: Failed to cleanup {temp_dir}: {e}")
```

### Функция validate_zip

- [ ] Создать функцию `validate_zip(zip_path: Path) -> bool`:
- [ ] Добавить docstring: "Проверяет что файл является валидным ZIP архивом."
- [ ] Проверить что файл существует и является файлом
- [ ] Попытаться открыть как ZIP:

```python
try:
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Проверить целостность
        bad_file = zip_ref.testzip()
        return bad_file is None
except zipfile.BadZipFile:
    return False
```

### Тестирование

- [ ] Создать тестовый ZIP-архив вручную с:
  - Один .md файл с контентом
  - Папка attachments/ с 2-3 изображениями
- [ ] Протестировать функции в Django shell:

```python
from blog.services.archive_handler import extract_zip, find_markdown_file, find_media_files, cleanup_temp
from pathlib import Path

zip_path = Path('test_archive.zip')
temp_dir = extract_zip(zip_path)
md_file = find_markdown_file(temp_dir)
media_files = find_media_files(temp_dir)
print(md_file, len(media_files))
cleanup_temp(temp_dir)
```

### Тестирование безопасности

- [ ] Создать архив с path traversal: файл `../../evil.txt`
- [ ] Попытаться распаковать — должна быть ValueError
- [ ] Создать большой архив > 100 MB (или изменить max_size для теста)
- [ ] Попытаться распаковать — должна быть ValueError

## Коммит

**Формат:** `phase 3.11 feat: Создан archive_handler для работы с ZIP-архивами`

**Описание:**

```
phase 3.11 feat: Создан archive_handler для работы с ZIP-архивами

- Создан blog/services/archive_handler.py
- Реализованы функции: extract_zip, find_markdown_file, find_media_files
- Добавлена функция cleanup_temp для очистки временных файлов
- Добавлена функция validate_zip для проверки целостности архивов
- Защита от path traversal и zip bombs
- Whitelist расширений для медиа-файлов
```
