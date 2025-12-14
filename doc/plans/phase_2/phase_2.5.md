# Фаза 2.5: Архитектура HTML-процессоров (Beautiful Soup + модульная система)

## Цель

Создать масштабируемую модульную архитектуру для обработки HTML с помощью Beautiful Soup 4. Реализовать систему процессоров, где каждый обработчик отвечает за свой тип элементов (таблицы, изображения, цитаты, код).

## Контекст

**Проблема:** После конвертации Markdown → HTML элементы не имеют Bootstrap классов:
- `<table>` без `.table`, `.table-striped`
- `<img>` без `.img-fluid`, не центрированы
- `<blockquote>` без Bootstrap классов и Obsidian Callouts
- `<code>` inline без стилизации

**Решение:** Создать модульную систему обработчиков на базе Beautiful Soup 4, которая будет:
1. Парсить HTML после Markdown конвертации
2. Применять обработчики последовательно
3. Добавлять классы Bootstrap и кастомные атрибуты
4. Возвращать модифицированный HTML

**Философия:** 
- Backend обрабатывает статические классы (Bootstrap)
- Frontend добавляет интерактивность (кнопки, плееры, фуллскрин)

**Референс:** `doc/samples/main.js` — аналогичная логика, но на JS

**Документация:**
- Beautiful Soup 4: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- Bootstrap 5 Tables: https://getbootstrap.com/docs/5.3/content/tables/
- Bootstrap 5 Images: https://getbootstrap.com/docs/5.3/content/images/

## Задачи

### 1. Установка Beautiful Soup 4

- [ ] Установить библиотеку через Poetry:
  ```bash
  poetry add beautifulsoup4
  ```
- [ ] Проверить установку:
  ```bash
  poetry show beautifulsoup4
  ```
- [ ] Зафиксировать версию в `pyproject.toml`

### 2. Создание пакета blog/services/

- [ ] Создать директорию `blog/services/` (если еще не существует)
- [ ] Создать `blog/services/__init__.py` с экспортами:
  ```python
  from blog.services.markdown_converter import convert_markdown_to_html
  
  __all__ = ['convert_markdown_to_html']
  ```
- [ ] Переместить функцию из `blog/services.py` в `blog/services/markdown_converter.py`
- [ ] Обновить импорты в `blog/models.py`

### 3. Создание базового класса HTMLProcessor

- [ ] Создать файл `blog/services/html_processor.py`
- [ ] Определить абстрактный базовый класс:
  ```python
  from abc import ABC, abstractmethod
  from bs4 import BeautifulSoup, Tag
  
  class HTMLProcessor(ABC):
      """Базовый класс для обработчиков HTML элементов."""
      
      @abstractmethod
      def process(self, soup: BeautifulSoup) -> None:
          """Обрабатывает HTML, модифицируя soup in-place."""
          pass
      
      @abstractmethod
      def get_name(self) -> str:
          """Возвращает имя процессора для логирования."""
          pass
  ```
- [ ] Добавить docstring с описанием архитектуры
- [ ] Добавить type hints для всех методов

### 4. Создание пакета blog/services/processors/

- [ ] Создать директорию `blog/services/processors/`
- [ ] Создать `blog/services/processors/__init__.py`:
  ```python
  from blog.services.processors.table_processor import TableProcessor
  from blog.services.processors.image_processor import ImageProcessor
  from blog.services.processors.blockquote_processor import BlockquoteProcessor
  from blog.services.processors.code_processor import CodeProcessor
  
  __all__ = [
      'TableProcessor',
      'ImageProcessor',
      'BlockquoteProcessor',
      'CodeProcessor',
  ]
  ```

### 5. Создание MarkdownProcessor (главный класс)

- [ ] Создать файл `blog/services/markdown_processor.py`
- [ ] Определить класс `MarkdownProcessor`:
  ```python
  from typing import List
  from bs4 import BeautifulSoup
  from blog.services.html_processor import HTMLProcessor
  
  class MarkdownProcessor:
      """Главный процессор для конвертации Markdown → HTML с обработкой."""
      
      def __init__(self, processors: List[HTMLProcessor]):
          self.processors = processors
      
      def process_html(self, html: str) -> str:
          """Обрабатывает HTML всеми зарегистрированными процессорами."""
          soup = BeautifulSoup(html, 'html.parser')
          
          for processor in self.processors:
              processor.process(soup)
          
          return str(soup)
  ```
- [ ] Добавить логирование (опционально)
- [ ] Добавить обработку ошибок с fallback

### 6. Интеграция в convert_markdown_to_html()

- [ ] Обновить функцию в `blog/services/markdown_converter.py`:
  ```python
  def convert_markdown_to_html(markdown_text: str) -> str:
      # 1. Markdown → HTML (существующая логика)
      html = markdown.markdown(...)
      
      # 2. Регистрация процессоров
      processors = [
          TableProcessor(),
          ImageProcessor(),
          BlockquoteProcessor(),
          CodeProcessor(),
      ]
      
      # 3. Обработка HTML
      processor = MarkdownProcessor(processors)
      html = processor.process_html(html)
      
      return html
  ```
- [ ] Протестировать с существующими постами

### 7. Создание TableProcessor (референс)

- [ ] Создать файл `blog/services/processors/table_processor.py`
- [ ] Реализовать процессор для таблиц:
  ```python
  class TableProcessor(HTMLProcessor):
      def process(self, soup: BeautifulSoup) -> None:
          for table in soup.find_all('table'):
              # Добавляем Bootstrap классы
              table['class'] = table.get('class', []) + [
                  'table',
                  'table-striped',
                  'table-hover',
                  'table-bordered'
              ]
      
      def get_name(self) -> str:
          return "TableProcessor"
  ```
- [ ] Протестировать на посте с таблицами
- [ ] Проверить в браузере наличие классов

**Референс из samples:** `doc/samples/assets/js/main.js:15-17`
```javascript
table: ["table", "table-striped"],
```

### 8. Тестирование архитектуры

- [ ] Создать тестовый пост с таблицей в админке
- [ ] Сохранить пост (должна сработать конвертация)
- [ ] Открыть пост на сайте
- [ ] Открыть DevTools → Elements
- [ ] Проверить, что `<table>` имеет классы Bootstrap
- [ ] Убедиться, что таблица стилизована корректно

## Результаты

✅ **Что получим:**
- Модульная архитектура для обработки HTML
- Базовый класс `HTMLProcessor` для расширения
- Главный класс `MarkdownProcessor` с регистрацией обработчиков
- Пакет `blog/services/processors/` для процессоров
- `TableProcessor` как референс для остальных
- Легкое добавление новых процессоров

✅ **Расширяемость:**
```python
# Добавить новый процессор:
# 1. Создать файл processors/video_processor.py
# 2. Наследовать от HTMLProcessor
# 3. Зарегистрировать в markdown_converter.py
```

## Проблемы и решения

### Проблема: Beautiful Soup экранирует HTML атрибуты
**Решение:** Использовать `soup.prettify()` или `str(soup)` без prettify

### Проблема: Классы перезаписываются вместо добавления
**Решение:** 
```python
# ❌ Неправильно:
table['class'] = ['table']

# ✅ Правильно:
table['class'] = table.get('class', []) + ['table']
```

### Проблема: Процессоры конфликтуют друг с другом
**Решение:** Порядок регистрации важен, документировать зависимости

## Чеклист готовности к Phase 2.6

- [ ] Beautiful Soup 4 установлен
- [ ] Пакет `blog/services/` создан
- [ ] Базовый класс `HTMLProcessor` реализован
- [ ] `MarkdownProcessor` интегрирован в `convert_markdown_to_html()`
- [ ] `TableProcessor` работает корректно
- [ ] Тесты пройдены (таблицы имеют Bootstrap классы)

**Следующая фаза:** 2.6 — Реализация остальных процессоров (Image, Blockquote, Code)
