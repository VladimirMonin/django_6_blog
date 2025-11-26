# Python-Markdown в Django 6 Blog

## Введение

Markdown - это легковесный язык разметки, который позволяет авторам создавать форматированный контент с использованием простого синтаксиса. Для Django-блога это идеальное решение, так как:
- Авторы могут писать контент в простом текстовом формате
- Контент легко версионируется в Git
- Поддерживается подсветка кода для технических статей
- Автоматически генерируется оглавление для длинных статей

## Установка и настройка

### Основные зависимости

```bash
pip install markdown
pip install pygments  # для подсветки синтаксиса
pip install bleach    # для безопасности
pip install django-markdownx  # редактор для админки
```

### Дополнительные пакеты

```bash
pip install python-frontmatter  # для извлечения метаданных
pip install django-bleach       # интеграция bleach с Django
```

## Архитектура решения

### Вариант A: Рендеринг при запросе

```python
# Храним только markdown в БД
class Post(models.Model):
    title = models.CharField(max_length=200)
    content_markdown = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def content_html(self):
        """Рендеринг markdown в HTML при каждом запросе"""
        return markdown.markdown(
            self.content_markdown,
            extensions=['extra', 'codehilite', 'toc']
        )
```

**Плюсы:**
- Простая модель данных
- Всегда актуальный HTML
- Легко обновлять расширения

**Минусы:**
- Вычислительная нагрузка при каждом запросе
- Медленнее для больших документов

### Вариант B: Предварительный рендеринг

```python
# Храним markdown и кэшированный HTML
class Post(models.Model):
    title = models.CharField(max_length=200)
    content_markdown = models.TextField()
    content_html = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        """Рендеринг markdown при сохранении"""
        if self.content_markdown:
            self.content_html = markdown.markdown(
                self.content_markdown,
                extensions=['extra', 'codehilite', 'toc']
            )
        super().save(*args, **kwargs)
```

**Плюсы:**
- Быстрый доступ к HTML
- Меньше нагрузки на сервер
- Легко кэшировать

**Минусы:**
- Дополнительное место в БД
- Нужно пересохранять при изменении расширений

## Базовая интеграция

### Вариант 1: Template Filter

```python
# blog/templatetags/markdown_extras.py
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdown')
def markdown_format(text):
    """Конвертирует markdown в HTML"""
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ]
    return mark_safe(markdown.markdown(text, extensions=extensions))
```

Использование в шаблоне:

```django
{% load markdown_extras %}

<article>
    <h1>{{ post.title }}</h1>
    <div class="content">
        {{ post.content_markdown|markdown }}
    </div>
</article>
```

### Вариант 2: Модель с предварительным рендерингом

```python
# blog/models.py
import markdown
from django.db import models

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content_markdown = models.TextField()
    content_html = models.TextField(blank=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Рендеринг markdown при сохранении"""
        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.fenced_code',
        ]
        
        if self.content_markdown:
            self.content_html = markdown.markdown(
                self.content_markdown,
                extensions=extensions,
                extension_configs={
                    'markdown.extensions.codehilite': {
                        'css_class': 'highlight'
                    },
                    'markdown.extensions.toc': {
                        'title': 'Содержание'
                    }
                }
            )
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
```

### Вариант 3: Django-Markdownx (готовое решение)

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'markdownx',
    'blog',
]

# Настройки markdownx
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.toc',
]

MARKDOWNX_UPLOAD_MAX_SIZE = 50 * 1024 * 1024  # 50MB
MARKDOWNX_MEDIA_PATH = 'markdownx/'

# blog/models.py
from markdownx.models import MarkdownxField

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = MarkdownxField()
    
    def __str__(self):
        return self.title
```

## Модель для блог-поста

```python
# blog/models.py
import markdown
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

class BlogPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    excerpt = models.TextField(max_length=500, blank=True, verbose_name='Краткое описание')
    content_markdown = models.TextField(verbose_name='Содержание (Markdown)')
    content_html = models.TextField(blank=True, verbose_name='Содержание (HTML)')
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name='Статус'
    )
    featured_image = models.ImageField(
        upload_to='blog/images/', 
        blank=True, 
        null=True,
        verbose_name='Изображение'
    )
    tags = models.CharField(max_length=200, blank=True, verbose_name='Теги')
    meta_description = models.CharField(max_length=160, blank=True, verbose_name='Meta описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='Опубликован')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Пост блога'
        verbose_name_plural = 'Посты блога'
    
    def save(self, *args, **kwargs):
        # Автоматическое создание slug
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Рендеринг markdown в HTML
        if self.content_markdown:
            extensions = [
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.footnotes',
            ]
            
            extension_configs = {
                'markdown.extensions.codehilite': {
                    'css_class': 'codehilite',
                    'linenums': False,
                },
                'markdown.extensions.toc': {
                    'title': 'Содержание',
                    'permalink': True,
                }
            }
            
            self.content_html = markdown.markdown(
                self.content_markdown,
                extensions=extensions,
                extension_configs=extension_configs
            )
        
        # Установка времени публикации
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return self.title
```

## Расширения Python-Markdown

### Таблицы

```python
# Использование расширения tables
import markdown

text = """
| Заголовок 1 | Заголовок 2 |
|-------------|-------------|
| Ячейка 1    | Ячейка 2    |
| Ячейка 3    | Ячейка 4    |
"""

html = markdown.markdown(text, extensions=['markdown.extensions.tables'])
```

### Блоки кода с подсветкой

```python
# Настройка codehilite с Pygments
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

text = """
```python
def hello_world():
    print("Hello, World!")
    return True
```
"""

html = markdown.markdown(
    text,
    extensions=[
        'markdown.extensions.fenced_code',
        CodeHiliteExtension(
            css_class='highlight',
            linenums=False,
            pygments_style='default'
        )
    ]
)
```

### Оглавление (TOC)

```python
# Автоматическое оглавление
import markdown

text = """
[TOC]

# Заголовок 1
Содержание раздела 1

## Подраздел 1.1
Содержание подраздела

## Подраздел 1.2
Еще содержание

# Заголовок 2
Содержание раздела 2
"""

html = markdown.markdown(
    text,
    extensions=[
        'markdown.extensions.toc',
        'markdown.extensions.headerid'
    ],
    extension_configs={
        'markdown.extensions.toc': {
            'title': 'Содержание статьи',
            'permalink': True,
            'baselevel': 1,
            'slugify': lambda value, separator: value.lower().replace(' ', '-')
        }
    }
)
```

### Другие полезные расширения

```python
# Полный набор расширений
extensions = [
    'markdown.extensions.extra',           # Включает tables, fenced_code, footnotes
    'markdown.extensions.abbr',            # Аббревиатуры
    'markdown.extensions.attr_list',       # Атрибуты для элементов
    'markdown.extensions.def_list',        # Списки определений
    'markdown.extensions.fenced_code',     # Блоки кода с тройными кавычками
    'markdown.extensions.footnotes',       # Сноски
    'markdown.extensions.tables',          # Таблицы
    'markdown.extensions.smart_strong',    # Умное выделение жирным
    'markdown.extensions.admonition',      # Блоки предупреждений
    'markdown.extensions.codehilite',      # Подсветка кода
    'markdown.extensions.toc',             # Оглавление
]
```

## Редактор в админке

### Django-Markdownx

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'markdownx',
]

# Настройки markdownx
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.toc',
    'markdown.extensions.fenced_code',
    'markdown.extensions.tables',
]

MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS = {
    'markdown.extensions.codehilite': {
        'use_pygments': True,
        'css_class': 'highlight',
    }
}

MARKDOWNX_UPLOAD_MAX_SIZE = 50 * 1024 * 1024  # 50MB
MARKDOWNX_MEDIA_PATH = 'markdownx/'
MARKDOWNX_IMAGE_MAX_SIZE = {'size': (2000, 2000), 'quality': 90}

# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('markdownx/', include('markdownx.urls')),
]

# blog/admin.py
from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import BlogPost

@admin.register(BlogPost)
class BlogPostAdmin(MarkdownxModelAdmin):
    list_display = ['title', 'status', 'created_at', 'published_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'content_markdown']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = [
        ('Основная информация', {
            'fields': ['title', 'slug', 'excerpt', 'status']
        }),
        ('Содержание', {
            'fields': ['content_markdown', 'content_html']
        }),
        ('SEO и метаданные', {
            'fields': ['meta_description', 'tags', 'featured_image']
        }),
        ('Даты', {
            'fields': ['created_at', 'updated_at', 'published_at'],
            'classes': ['collapse']
        }),
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'content_html']
```

### Django-MDEditor

```python
# Альтернатива - django-mdeditor
INSTALLED_APPS = [
    # ...
    'mdeditor',
]

# blog/models.py
from mdeditor.fields import MDTextField

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = MDTextField()
```

## Безопасность

### Sanit