# Подсветка синтаксиса и расширения Python-Markdown

## Подсветка синтаксиса с Pygments

### Установка и базовая настройка

```bash
pip install pygments
```

```python
# blog/utils.py
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

def render_markdown_with_syntax_highlighting(text):
    """Рендеринг markdown с подсветкой синтаксиса"""
    
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.fenced_code',
        CodeHiliteExtension(
            css_class='highlight',
            linenums=False,
            guess_lang=True,
            pygments_style='default'
        ),
        'markdown.extensions.toc',
    ]
    
    return markdown.markdown(text, extensions=extensions)
```

### Настройка стилей Pygments

```python
# Генерация CSS стилей для Pygments
from pygments.formatters import HtmlFormatter

# Генерация CSS для темной темы
dark_css = HtmlFormatter(style='monokai').get_style_defs('.highlight')

# Генерация CSS для светлой темы
light_css = HtmlFormatter(style='default').get_style_defs('.highlight')

# Сохранение CSS в файл
with open('static/css/pygments-dark.css', 'w') as f:
    f.write(dark_css)

with open('static/css/pygments-light.css', 'w') as f:
    f.write(light_css)
```

### Интеграция с шаблонами

```django
<!-- blog/templates/blog/post_detail.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{{ post.title }}</title>
    <!-- CSS для подсветки синтаксиса -->
    <link rel="stylesheet" href="{% static 'css/pygments-dark.css' %}">
    <style>
        .highlight {
            background: #2d2d2d;
            color: #f8f8f2;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
            overflow-x: auto;
        }
        
        .highlight pre {
            margin: 0;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.9rem;
            line-height: 1.4;
        }
        
        .codehilite {
            position: relative;
        }
        
        .copy-button {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #fff;
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            cursor: pointer;
            font-size: 0.8rem;
        }
        
        .copy-button:hover {
            background: rgba(255, 255, 255, 0.2);
        }
    </style>
</head>
<body>
    <article class="post-content">
        {{ post.content_html|safe }}
    </article>
    
    <!-- JavaScript для копирования кода -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Добавление кнопок копирования
            document.querySelectorAll('.highlight').forEach(function(block) {
                const button = document.createElement('button');
                button.className = 'copy-button';
                button.textContent = 'Копировать';
                button.addEventListener('click', function() {
                    const code = block.querySelector('code');
                    navigator.clipboard.writeText(code.textContent)
                        .then(() => {
                            button.textContent = 'Скопировано!';
                            setTimeout(() => {
                                button.textContent = 'Копировать';
                            }, 2000);
                        });
                });
                block.style.position = 'relative';
                block.appendChild(button);
            });
        });
    </script>
</body>
</html>
```

## Расширения Python-Markdown

### Полный набор расширений

```python
# blog/utils.py
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

def render_full_markdown(text):
    """Рендеринг markdown со всеми расширениями"""
    
    extensions = [
        # Основные расширения
        'markdown.extensions.extra',
        
        # Подсветка кода
        'markdown.extensions.fenced_code',
        CodeHiliteExtension(
            css_class='codehilite',
            linenums=True,
            linenum_start=1,
            guess_lang=True,
            pygments_style='monokai'
        ),
        
        # Оглавление
        'markdown.extensions.toc',
        
        # Таблицы
        'markdown.extensions.tables',
        
        # Сноски
        'markdown.extensions.footnotes',
        
        # Аббревиатуры
        'markdown.extensions.abbr',
        
        # Списки определений
        'markdown.extensions.def_list',
        
        # Атрибуты
        'markdown.extensions.attr_list',
        
        # Умные кавычки и тире
        'markdown.extensions.smarty',
    ]
    
    extension_configs = {
        'markdown.extensions.toc': {
            'title': 'Содержание',
            'permalink': True,
            'baselevel': 1,
            'slugify': lambda value, separator: (
                value.lower()
                .replace(' ', '-')
                .replace('_', '-')
                .replace('.', '-')
            )
        },
        'markdown.extensions.codehilite': {
            'css_class': 'highlight',
            'linenums': True,
            'linenum_start': 1,
            'guess_lang': True,
            'pygments_style': 'monokai',
        },
        'markdown.extensions.footnotes': {
            'PLACE_MARKER': '///FOOTNOTES GO HERE///',
            'UNIQUE_IDS': True,
        },
    }
    
    return markdown.markdown(
        text,
        extensions=extensions,
        extension_configs=extension_configs
    )
```

### Примеры использования расширений

#### Таблицы

```markdown
| Функция | Описание | Пример |
|---------|----------|--------|
| `markdown()` | Основная функция рендеринга | `markdown.markdown(text)` |
| `extensions` | Список расширений | `['extra', 'codehilite']` |
| `output_format` | Формат вывода | `'html5'` |

*Таблица 1: Основные функции Python-Markdown*
```

#### Блоки кода с указанием языка

````markdown
```python
import markdown

def render_blog_post(content):
    """Рендеринг поста блога"""
    html = markdown.markdown(
        content,
        extensions=['extra', 'codehilite', 'toc']
    )
    return html
```

```javascript
// Пример JavaScript кода
function highlightCode() {
    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });
}
```

```bash
# Установка зависимостей
pip install markdown pygments bleach
```
````

#### Сноски

```markdown
Python-Markdown поддерживает сноски[^1].

Вы можете использовать несколько сносок[^2] в одном документе.

[^1]: Это первая сноска
[^2]: Это вторая сноска с [ссылкой](https://example.com)
```

#### Аббревиатуры

```markdown
*[HTML]: HyperText Markup Language
*[CSS]: Cascading Style Sheets
*[JS]: JavaScript

Мы используем HTML, CSS и JS для веб-разработки.
```

#### Списки определений

```markdown
Markdown
: Легковесный язык разметки

Python-Markdown
: Реализация Markdown на Python

Django
: Веб-фреймворк для Python
```

#### Атрибуты элементов

```markdown
# Заголовок {#custom-id}

Этот абзац будет иметь класс "important" {.important}

![Изображение](image.jpg){width=800 height=600}
```

## Кастомные расширения

### Создание простого расширения

```python
# blog/markdown_extensions/custom.py
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor

class CustomExtension(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(CustomPreprocessor(md), 'custom', 175)

class CustomPreprocessor(Preprocessor):
    def run(self, lines):
        new_lines = []
        for line in lines:
            # Замена [INFO] на блок информации
            if line.strip().startswith('[INFO]'):
                content = line.replace('[INFO]', '').strip()
                new_lines.append(f'<div class="info-block">{content}</div>')
            else:
                new_lines.append(line)
        return new_lines

def makeExtension(**kwargs):
    return CustomExtension(**kwargs)
```

### Использование кастомного расширения

```python
# blog/utils.py
from blog.markdown_extensions.custom import CustomExtension

def render_with_custom_extensions(text):
    """Рендеринг с кастомными расширениями"""
    
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        CustomExtension(),  # Наше кастомное расширение
    ]
    
    return markdown.markdown(text, extensions=extensions)
```

### Пример markdown с кастомным расширением

```markdown
# Статья о Python-Markdown

[INFO] Это важная информация, которая будет отображена в специальном блоке

Основной контент статьи...

```python
print("Пример кода")
```
```

## Настройка для разных типов контента

### Для технических статей

```python
def render_technical_article(text):
    """Рендеринг для технических статей"""
    
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.fenced_code',
        CodeHiliteExtension(
            css_class='codehilite',
            linenums=True,
            guess_lang=True,
            pygments_style='monokai'
        ),
        'markdown.extensions.tables',
        'markdown.extensions.footnotes',
        'markdown.extensions.toc',
    ]
    
    return markdown.markdown(text, extensions=extensions)
```

### Для простых постов

```python
def render_simple_post(text):
    """Рендеринг для простых постов"""
    
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.smarty',
    ]
    
    return markdown.markdown(text, extensions=extensions)
```

## Производительность и оптимизация

### Кэширование рендеринга

```python
from django.core.cache import cache

def get_cached_markdown(text, cache_key):
    """Получение кэшированного markdown"""
    
    cached_html = cache.get(cache_key)
    if cached_html:
        return cached_html
    
    # Рендеринг markdown
    html = render_full_markdown(text)
    
    # Кэширование на 1 час
    cache.set(cache_key, html, 60 * 60)
    
    return html
```

### Ленивая загрузка Pygments

```python
import importlib

def render_markdown_with_optional_pygments(text, use_pygments=True):
    """Рендеринг с опциональной подсветкой синтаксиса"""
    
    extensions = ['markdown.extensions.extra', 'markdown.extensions.fenced_code']
    
    if use_pygments:
        try:
            # Проверка доступности Pygments
            importlib.import_module('pygments')
            from markdown.extensions.codehilite import CodeHiliteExtension
            extensions.append(CodeHiliteExtension())
        except ImportError:
            # Pygments не установлен, используем базовый рендеринг
            pass
    
    return markdown.markdown(text, extensions=extensions)
```

## Best Practices

1. **Используйте fenced_code** для блоков кода с тройными кавычками
2. **Настройте Pygments стиль** в соответствии с дизайном сайта
3. **Добавьте кнопки копирования** для удобства пользователей
4. **Используйте guess_lang** для автоматического определения языка
5. **Кэшируйте рендеренный HTML** для производительности
6. **Тестируйте разные расширения** на предмет конфликтов
7. **Создавайте кастомные расширения** для специфических нужд