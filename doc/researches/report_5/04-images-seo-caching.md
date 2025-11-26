# Работа с изображениями, SEO и кэширование

## Работа с изображениями в Markdown

### Базовая интеграция изображений

```markdown
![Альтернативный текст]({{ MEDIA_URL }}blog/images/example.jpg "Заголовок изображения")

![Логотип Django](/static/images/django-logo.png){width=200 height=100}
```

### Автоматическая обработка изображений

```python
# blog/utils/image_processing.py
from PIL import Image
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def process_uploaded_image(image_file, max_size=(1200, 800), quality=85):
    """Обработка загруженного изображения"""
    
    try:
        # Открытие изображения
        img = Image.open(image_file)
        
        # Конвертация в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Изменение размера с сохранением пропорций
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Сохранение в буфер
        from io import BytesIO
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        
        # Создание имени файла
        filename = f"processed_{image_file.name}"
        
        # Сохранение в storage
        file_content = ContentFile(buffer.getvalue())
        saved_path = default_storage.save(f'blog/images/{filename}', file_content)
        
        return saved_path
        
    except Exception as e:
        print(f"Ошибка обработки изображения: {e}")
        return None
```

### Responsive изображения в Markdown

```python
# blog/markdown_extensions/responsive_images.py
import markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import LinkInlineProcessor, IMAGE_LINK_RE
from markdown.util import etree

class ResponsiveImageExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            ResponsiveImageProcessor(IMAGE_LINK_RE, md), 
            'image_link', 
            150
        )

class ResponsiveImageProcessor(LinkInlineProcessor):
    def handleMatch(self, m, data):
        text, index, handled = self.getText(data, m.end(0))
        
        if not handled:
            return None, None, None
        
        src, title, index, handled = self.getLink(data, index)
        
        if not handled:
            return None, None, None
        
        # Создание responsive изображения
        img = etree.Element('img')
        img.set('src', src)
        img.set('alt', self.unescape(text))
        
        if title:
            img.set('title', self.unescape(title))
        
        # Добавление классов для responsive
        img.set('class', 'img-fluid')
        img.set('loading', 'lazy')
        
        return img, m.start(0), index

def makeExtension(**kwargs):
    return ResponsiveImageExtension(**kwargs)
```

### Интеграция с Django-Markdownx

```python
# settings.py
# Настройки для загрузки изображений
MARKDOWNX_UPLOAD_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
MARKDOWNX_IMAGE_MAX_SIZE = {
    'size': (2000, 2000),
    'quality': 90
}
MARKDOWNX_MEDIA_PATH = 'markdownx/'
MARKDOWNX_UPLOAD_PATH = 'markdownx/'

# blog/views.py
from markdownx.views import ImageUploadView
from django.http import JsonResponse

class CustomImageUploadView(ImageUploadView):
    def post(self, request, *args, **kwargs):
        """Кастомная загрузка изображений"""
        
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            
            # Проверка размера
            if image_file.size > 10 * 1024 * 1024:  # 10MB
                return JsonResponse({
                    'error': 'Файл слишком большой. Максимальный размер: 10MB'
                }, status=400)
            
            # Обработка изображения
            processed_path = process_uploaded_image(image_file)
            
            if processed_path:
                image_url = default_storage.url(processed_path)
                
                return JsonResponse({
                    'image_code': f'![{image_file.name}]({image_url})',
                    'image_url': image_url
                })
        
        return JsonResponse({'error': 'Ошибка загрузки'}, status=400)
```

## SEO оптимизация

### Извлечение метаданных из Markdown

```python
# blog/utils/seo.py
import frontmatter
import markdown
from django.utils.text import slugify

def extract_metadata_from_markdown(content):
    """Извлечение метаданных из markdown с front matter"""
    
    try:
        # Парсинг front matter
        post = frontmatter.loads(content)
        
        metadata = {
            'title': post.get('title', ''),
            'description': post.get('description', ''),
            'keywords': post.get('keywords', ''),
            'author': post.get('author', ''),
            'date': post.get('date', ''),
            'tags': post.get('tags', []),
            'image': post.get('image', ''),
            'content': post.content  # Контент без front matter
        }
        
        # Если title не указан, извлекаем из первого заголовка
        if not metadata['title']:
            lines = metadata['content'].split('\n')
            for line in lines:
                if line.startswith('# '):
                    metadata['title'] = line[2:].strip()
                    break
        
        # Генерация slug
        if metadata['title']:
            metadata['slug'] = slugify(metadata['title'])
        
        # Генерация meta description если не указан
        if not metadata['description']:
            # Берем первые 160 символов контента
            plain_text = markdown.markdown(metadata['content'])
            # Удаляем HTML теги
            import re
            clean_text = re.sub('<[^<]+?>', '', plain_text)
            metadata['description'] = clean_text[:160].strip()
        
        return metadata
        
    except Exception as e:
        print(f"Ошибка извлечения метаданных: {e}")
        return {}
```

### Пример markdown с front matter

```markdown
---
title: "Python-Markdown в Django 6: Полное руководство"
description: "Изучите интеграцию Python-Markdown с Django 6 для создания блога с подсветкой кода, таблицами и SEO оптимизацией."
author: "Ваше Имя"
date: 2025-11-26
tags: ["python", "django", "markdown", "блог"]
image: "/static/images/python-markdown-django.jpg"
keywords: "python markdown, django 6, блог, подсветка кода"
---

# Введение

Python-Markdown - это мощная библиотека для работы с markdown в Python...
```

### SEO теги в шаблонах

```django
<!-- blog/templates/blog/post_detail.html -->
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Основные SEO теги -->
    <title>{{ post.title }} - Мой Блог</title>
    <meta name="description" content="{{ post.meta_description }}">
    <meta name="keywords" content="{{ post.tags }}">
    <meta name="author" content="{{ post.author }}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{{ post.title }}">
    <meta property="og:description" content="{{ post.meta_description }}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{{ request.build_absolute_uri }}">
    {% if post.featured_image %}
    <meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.featured_image.url }}">
    {% endif %}
    <meta property="og:site_name" content="Мой Блог">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{{ post.title }}">
    <meta name="twitter:description" content="{{ post.meta_description }}">
    {% if post.featured_image %}
    <meta name="twitter:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.featured_image.url }}">
    {% endif %}
    
    <!-- Структурированные данные -->
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": "{{ post.title }}",
        "description": "{{ post.meta_description }}",
        "author": {
            "@type": "Person",
            "name": "{{ post.author }}"
        },
        "datePublished": "{{ post.published_at|date:'c' }}",
        "dateModified": "{{ post.updated_at|date:'c' }}",
        {% if post.featured_image %}
        "image": "{{ request.scheme }}://{{ request.get_host }}{{ post.featured_image.url }}",
        {% endif %}
        "publisher": {
            "@type": "Organization",
            "name": "Мой Блог",
            "logo": {
                "@type": "ImageObject",
                "url": "{{ request.scheme }}://{{ request.get_host }}{% static 'images/logo.png' %}"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": "{{ request.build_absolute_uri }}"
        }
    }
    </script>
</head>
<body>
    <!-- Контент поста -->
    <article>
        <h1>{{ post.title }}</h1>
        <div class="post-meta">
            <time datetime="{{ post.published_at|date:'c' }}">
                {{ post.published_at|date:"d E Y" }}
            </time>
            <span>Автор: {{ post.author }}</span>
        </div>
        
        <div class="post-content">
            {{ post.content_html|safe }}
        </div>
        
        <div class="post-tags">
            {% for tag in post.get_tags_list %}
                <a href="{% url 'blog:tag' tag %}" class="tag">#{{ tag }}</a>
            {% endfor %}
        </div>
    </article>
</body>
</html>
```

## Кэширование

### Стратегии кэширования

```python
# blog/utils/caching.py
from django.core.cache import cache
from django.conf import settings

def get_cached_post_html(post_id, content_markdown):
    """Получение кэшированного HTML поста"""
    
    cache_key = f'post_html_{post_id}'
    cached_html = cache.get(cache_key)
    
    if cached_html:
        return cached_html
    
    # Рендеринг markdown
    from .markdown_utils import render_full_markdown
    html = render_full_markdown(content_markdown)
    
    # Кэширование на 1 час
    cache.set(cache_key, html, 60 * 60)
    
    return html

def invalidate_post_cache(post_id):
    """Инвалидация кэша поста"""
    cache_key = f'post_html_{post_id}'
    cache.delete(cache_key)
```

### Кэширование в моделях

```python
# blog/models.py
from django.core.cache import cache
from django.db import models

class BlogPost(models.Model):
    # ... поля модели
    
    def save(self, *args, **kwargs):
        # Инвалидация кэша при сохранении
        if self.pk:
            cache_key = f'post_html_{self.pk}'
            cache.delete(cache_key)
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Инвалидация кэша при удалении
        cache_key = f'post_html_{self.pk}'
        cache.delete(cache_key)
        
        super().delete(*args, **kwargs)
    
    @property
    def cached_html(self):
        """Кэшированный HTML контент"""
        return get_cached_post_html(self.id, self.content_markdown)
```

### Template fragment caching

```django
<!-- blog/templates/blog/post_detail.html -->
{% load cache %}

<article class="post">
    <header>
        <h1>{{ post.title }}</h1>
        <!-- Не кэшируемая часть -->
    </header>
    
    <!-- Кэшируемая часть контента -->
    {% cache 3600 post_content post.id post.updated_at.timestamp %}
    <div class="post-content">
        {{ post.content_html|safe }}
    </div>
    {% endcache %}
    
    <footer>
        <!-- Не кэшируемая часть -->
    </footer>
</article>
```

### View-level caching

```python
# blog/views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Кэширование на 15 минут
class PostDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/post_detail.html'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Обновление счетчика просмотров (не кэшируется)
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        
        return obj
```

## Производительность

### Ленивая загрузка изображений

```django
<!-- blog/templates/blog/post_detail.html -->
<style>
    .post-content img {
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .post-content img.lazy-loaded {
        opacity: 1;
    }
</style>

<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Ленивая загрузка изображений
        const lazyImages = [].slice.call(document.querySelectorAll('.post-content img'));
        
        if ('IntersectionObserver' in window) {
            const lazyImageObserver = new IntersectionObserver(function(entries, observer) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.dataset.src;
                        lazyImage.classList.add('lazy-loaded');
                        lazyImageObserver.unobserve(lazyImage);
                    }
                });
            });
            
            lazyImages.forEach(function(lazyImage) {
                lazyImageObserver.observe(lazyImage);
            });
        }
    });
</script>
```

### Оптимизация для больших документов

```python
# blog/utils/performance.py
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension

def render