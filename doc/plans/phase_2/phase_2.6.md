# Фаза 2.6: Процессоры для изображений, цитат и кода

## Цель

Реализовать три оставшихся процессора для обработки HTML: ImageProcessor (стилизация и центровка), BlockquoteProcessor (Obsidian Callouts), CodeProcessor (inline-код с Bootstrap).

## Контекст

После Phase 2.5 у нас есть:
- ✅ Архитектура с `HTMLProcessor` и `MarkdownProcessor`
- ✅ `TableProcessor` как референс
- ⏳ Нужно добавить 3 процессора для остальных элементов

**Философия:** Backend добавляет Bootstrap классы, Frontend добавит интерактивность (фуллскрин для изображений — Phase 2.7).

**Референс:** `doc/samples/assets/js/main.js` — аналогичная логика на JS

**Документация:**
- Bootstrap Images: https://getbootstrap.com/docs/5.3/content/images/
- Bootstrap Alerts (для Callouts): https://getbootstrap.com/docs/5.3/components/alerts/
- Obsidian Callouts: https://help.obsidian.md/Editing+and+formatting/Callouts

## Задачи

### 1. ImageProcessor — стилизация изображений

- [ ] Создать файл `blog/services/processors/image_processor.py`
- [ ] Реализовать процессор:
  ```python
  from blog.services.html_processor import HTMLProcessor
  from bs4 import BeautifulSoup
  
  class ImageProcessor(HTMLProcessor):
      """Добавляет Bootstrap классы к изображениям."""
      
      def process(self, soup: BeautifulSoup) -> None:
          for img in soup.find_all('img'):
              # Добавляем Bootstrap классы
              img['class'] = img.get('class', []) + [
                  'img-fluid',    # Адаптивность
                  'd-block',      # Display block
                  'mx-auto'       # Центровка по горизонтали
              ]
              
              # Добавляем loading="lazy" для оптимизации
              if 'loading' not in img.attrs:
                  img['loading'] = 'lazy'
      
      def get_name(self) -> str:
          return "ImageProcessor"
  ```
- [ ] Добавить в `processors/__init__.py`
- [ ] Зарегистрировать в `markdown_converter.py`

**Референс из samples:** `doc/samples/assets/js/main.js:14`
```javascript
img: ["img-fluid", "d-block", "mx-auto"],
```

### 2. Тестирование ImageProcessor

- [ ] Создать пост с изображением: `![Alt text](image.jpg)`
- [ ] Сохранить и открыть на сайте
- [ ] Проверить DevTools: `<img>` должен иметь `.img-fluid .d-block .mx-auto`
- [ ] Убедиться, что изображение центрировано и адаптивно

### 3. BlockquoteProcessor — Obsidian Callouts

- [ ] Создать файл `blog/services/processors/blockquote_processor.py`
- [ ] Реализовать обработку Obsidian Callouts:
  ```python
  from blog.services.html_processor import HTMLProcessor
  from bs4 import BeautifulSoup
  
  class BlockquoteProcessor(HTMLProcessor):
      """Обрабатывает blockquote и Obsidian Callouts."""
      
      # Маппинг Obsidian типов на Bootstrap классы
      CALLOUT_MAPPING = {
          '[!info]': 'alert alert-info',
          '[!warning]': 'alert alert-warning',
          '[!success]': 'alert alert-success',
          '[!error]': 'alert alert-danger',
          '[!tip]': 'alert alert-primary',
          '[!note]': 'alert alert-secondary',
          '[!danger]': 'alert alert-danger',
      }
      
      def process(self, soup: BeautifulSoup) -> None:
          for blockquote in soup.find_all('blockquote'):
              first_p = blockquote.find('p')
              
              if first_p:
                  text = first_p.get_text().strip()
                  
                  # Проверяем, есть ли Obsidian Callout маркер
                  if text in self.CALLOUT_MAPPING:
                      # Добавляем Bootstrap классы
                      classes = self.CALLOUT_MAPPING[text].split()
                      blockquote['class'] = blockquote.get('class', []) + classes
                      
                      # Удаляем маркер из контента
                      first_p.decompose()
              
              # Если нет маркера, добавляем базовые классы
              if 'class' not in blockquote.attrs:
                  blockquote['class'] = ['blockquote', 'border-start', 'border-warning', 'ps-3']
      
      def get_name(self) -> str:
          return "BlockquoteProcessor"
  ```
- [ ] Добавить в `processors/__init__.py`
- [ ] Зарегистрировать в `markdown_converter.py`

**Референс из samples:** `doc/samples/assets/js/main.js:40-67`
```javascript
const typeMapping = {
  "[!info]": "alert-info",
  "[!warning]": "alert-warning",
  "[!success]": "alert-success",
  "[!error]": "alert-error",
  "[!tip]": "alert-tip",
  "[!highlight]": "alert-highlight",
  "[!danger]": "alert-danger",
};
```

### 4. Тестирование BlockquoteProcessor

- [ ] Создать пост с цитатой без маркера:
  ```markdown
  > Обычная цитата
  ```
- [ ] Создать пост с Obsidian Callout:
  ```markdown
  > [!warning]
  > Внимание! Важная информация
  ```
- [ ] Сохранить и открыть на сайте
- [ ] Проверить DevTools:
  - Обычная цитата: `.blockquote .border-start .border-warning`
  - Callout: `.alert .alert-warning`
  - Маркер `[!warning]` удален из текста
- [ ] Убедиться, что стили Bootstrap применились

### 5. CodeProcessor — inline-код

- [ ] Создать файл `blog/services/processors/code_processor.py`
- [ ] Реализовать процессор для inline `<code>`:
  ```python
  from blog.services.html_processor import HTMLProcessor
  from bs4 import BeautifulSoup
  
  class CodeProcessor(HTMLProcessor):
      """Обрабатывает inline-код (не code blocks)."""
      
      def process(self, soup: BeautifulSoup) -> None:
          # Находим <code> без родителя <pre> (inline-код)
          for code in soup.find_all('code'):
              # Пропускаем code blocks
              if code.parent and code.parent.name == 'pre':
                  continue
              
              # Добавляем Bootstrap класс для inline-кода
              code['class'] = code.get('class', []) + ['text-danger', 'bg-light', 'px-1']
      
      def get_name(self) -> str:
          return "CodeProcessor"
  ```
- [ ] Добавить в `processors/__init__.py`
- [ ] Зарегистрировать в `markdown_converter.py`

**Примечание:** Code blocks (`<pre><code>`) не трогаем, они обрабатываются Highlight.js на фронтенде.

### 6. Тестирование CodeProcessor

- [ ] Создать пост с inline-кодом:
  ```markdown
  Используйте функцию `convert_markdown_to_html()` для конвертации.
  ```
- [ ] Создать пост с code block (не должен измениться):
  ````markdown
  ```python
  def hello():
      print("world")
  ```
  ````
- [ ] Сохранить и открыть на сайте
- [ ] Проверить DevTools:
  - Inline `<code>`: классы `.text-danger .bg-light .px-1`
  - Code block `<pre><code>`: классы от Highlight.js (без наших)
- [ ] Убедиться, что inline-код выделен визуально

### 7. Интеграция всех процессоров

- [ ] Обновить `blog/services/markdown_converter.py`:
  ```python
  from blog.services.processors import (
      TableProcessor,
      ImageProcessor,
      BlockquoteProcessor,
      CodeProcessor,
  )
  
  def convert_markdown_to_html(markdown_text: str) -> str:
      # ... Markdown → HTML ...
      
      processors = [
          TableProcessor(),      # Таблицы
          ImageProcessor(),      # Изображения
          BlockquoteProcessor(), # Цитаты + Callouts
          CodeProcessor(),       # Inline-код
      ]
      
      processor = MarkdownProcessor(processors)
      html = processor.process_html(html)
      
      return html
  ```
- [ ] Проверить, что все процессоры регистрируются

### 8. Комплексное тестирование

- [ ] Создать пост со всеми элементами сразу:
  - Таблица
  - Изображение
  - Цитата обычная
  - Obsidian Callout `[!warning]`
  - Inline-код `функция()`
  - Code block с Python кодом
- [ ] Сохранить пост
- [ ] Открыть на сайте
- [ ] Проверить DevTools — все элементы должны иметь правильные классы
- [ ] Сделать скриншот для документации

### 9. Обновление существующих постов

- [ ] Открыть админку
- [ ] Для каждого из 9 архитектурных постов:
  - Открыть пост
  - Нажать "Сохранить" (без изменений)
  - Это перегенерирует `content_html` с новыми процессорами
- [ ] Проверить несколько постов на сайте
- [ ] Убедиться, что все элементы стилизованы корректно

## Результаты

✅ **Что получим:**
- `ImageProcessor` — адаптивные центрированные изображения с lazy loading
- `BlockquoteProcessor` — стилизованные цитаты и Obsidian Callouts
- `CodeProcessor` — выделенный inline-код
- Все 4 процессора работают вместе
- 9 архитектурных постов обновлены с новыми стилями

## Проблемы и решения

### Проблема: Obsidian Callout маркер не удаляется
**Решение:** Использовать `first_p.decompose()` вместо `first_p.string = ''`

### Проблема: CodeProcessor применяется к code blocks
**Решение:** Проверять родителя: `if code.parent.name == 'pre': continue`

### Проблема: Beautiful Soup не находит блоки с классами
**Решение:** Использовать `soup.find_all('tag')` без селекторов классов

## Чеклист готовности к Phase 2.7

- [ ] Все 4 процессора реализованы и зарегистрированы
- [ ] Таблицы стилизованы Bootstrap классами
- [ ] Изображения центрированы и адаптивны
- [ ] Цитаты и Callouts корректно отображаются
- [ ] Inline-код выделен визуально
- [ ] 9 архитектурных постов обновлены
- [ ] Комплексный тест пройден

**Следующая фаза:** 2.7 — Frontend интерактивность (фуллскрин изображений, медиаплееры, кнопки копирования)
