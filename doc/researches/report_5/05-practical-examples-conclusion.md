# Практические примеры и заключение

## Полный пример реализации

### Модель BlogPost с полной функциональностью

```python
# blog/models.py
import markdown
import bleach
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.cache import cache

class BlogPost(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
    ]
    
    # Основные поля
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    excerpt = models.TextField(max_length=500, blank=True, verbose_name='Краткое описание')
    content_markdown = models.TextField(verbose_name='Содержание (Markdown)')
    content_html = models.TextField(blank=True, verbose_name='Содержание (HTML)')
    
    # Статус и даты
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='Опубликован')
    
    # SEO и метаданные
    meta_description = models.CharField(max_length=160, blank=True, verbose_name='Meta описание')
    meta_keywords = models.CharField(max_length=255, blank=True, verbose_name='Ключевые слова')
    featured_image = models.ImageField(
        upload_to='blog/images/', 
        blank=True, 
        null=True,
        verbose_name='Изображение'
    )
    
    # Статистика
    views_count = models.PositiveIntegerField(default=0, verbose_name='Просмотры')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Пост блога'
        verbose_name_plural = 'Посты блога'
    
    def save(self, *args, **kwargs):
        # Автоматическое создание slug
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Рендеринг markdown в HTML с безопасностью
        if self.content_markdown:
            self.content_html = self.render_safe_markdown(self.content_markdown)
        
        # Установка времени публикации
        if self.status == 'published' and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        
        # Инвалидация кэша
        if self.pk:
            cache_key = f'post_html_{self.pk}'
            cache.delete(cache_key)
        
        super().save(*args, **kwargs)
    
    def render_safe_markdown(self, text):
        """Безопасный рендеринг markdown"""
        from markdown.extensions.codehilite import CodeHiliteExtension
        
        extensions = [
            'markdown.extensions.extra',
            'markdown.extensions.fenced_code',
            CodeHiliteExtension(
                css_class='highlight',
                linenums=False,
                guess_lang=True,
                pygments_style='monokai'
            ),
            'markdown.extensions.toc',
            'markdown.extensions.tables',
            'markdown.extensions.footnotes',
        ]
        
        # Рендеринг markdown
        html = markdown.markdown(text, extensions=extensions)
        
        # Очистка HTML
        allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 's', 'blockquote', 'code', 'pre',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img', 'span', 'div',
            'abbr', 'acronym', 'sub', 'sup',
        ]
        
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height', 'class'],
            'code': ['class'],
            'pre': ['class'],
            'span': ['class'],
            'div': ['class'],
        }
        
        clean_html = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attributes,
            protocols=['http', 'https', 'mailto'],
            strip=True
        )
        
        return clean_html
    
    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})
    
    def get_cached_html(self):
        """Получение кэшированного HTML"""
        cache_key = f'post_html_{self.id}'
        cached_html = cache.get(cache_key)
        
        if cached_html:
            return cached_html
        
        # Кэширование на 1 час
        cache.set(cache_key, self.content_html, 60 * 60)
        return self.content_html
    
    def get_tags_list(self):
        """Получение списка тегов"""
        if self.meta_keywords:
            return [tag.strip() for tag in self.meta_keywords.split(',')]
        return []
    
    def __str__(self):
        return self.title
```

### Views для блога

```python
# blog/views.py
from django.views.generic import ListView, DetailView
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import BlogPost

class BlogPostListView(ListView):
    model = BlogPost
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        return BlogPost.objects.filter(
            status='published'
        ).select_related().prefetch_related()

@method_decorator(cache_page(60 * 15), name='dispatch')
class BlogPostDetailView(DetailView):
    model = BlogPost
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return BlogPost.objects.filter(status='published')
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Обновление счетчика просмотров
        obj.views_count += 1
        obj.save(update_fields=['views_count'])
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Добавление SEO данных
        context['meta_title'] = f"{self.object.title} - Мой Блог"
        context['meta_description'] = self.object.meta_description or self.object.excerpt
        context['meta_keywords'] = self.object.meta_keywords
        
        return context
```

### Полный шаблон поста

```django
<!-- blog/templates/blog/post_detail.html -->
{% extends 'base.html' %}
{% load static %}

{% block meta %}
<meta name="description" content="{{ post.meta_description }}">
<meta name="keywords" content="{{ post.meta_keywords }}">
<meta name="author" content="Автор">

<!-- Open Graph -->
<meta property="og:title" content="{{ post.title }}">
<meta property="og:description" content="{{ post.meta_description }}">
<meta property="og:type" content="article">
<meta property="og:url" content="{{ request.build_absolute_uri }}">
{% if post.featured_image %}
<meta property="og:image" content="{{ request.scheme }}://{{ request.get_host }}{{ post.featured_image.url }}">
{% endif %}

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ post.title }}">
<meta name="twitter:description" content="{{ post.meta_description }}">
{% endblock %}

{% block title %}{{ post.title }} - Мой Блог{% endblock %}

{% block content %}
<article class="blog-post">
    <header class="post-header">
        <h1 class="post-title">{{ post.title }}</h1>
        
        <div class="post-meta">
            <time datetime="{{ post.published_at|date:'c' }}" class="post-date">
                {{ post.published_at|date:"d E Y" }}
            </time>
            <span class="post-views">👁 {{ post.views_count }}</span>
        </div>
        
        {% if post.featured_image %}
        <div class="post-image">
            <img src="{{ post.featured_image.url }}" 
                 alt="{{ post.title }}" 
                 class="img-fluid"
                 loading="lazy">
        </div>
        {% endif %}
    </header>
    
    <div class="post-content">
        {{ post.get_cached_html|safe }}
    </div>
    
    <footer class="post-footer">
        <div class="post-tags">
            <strong>Теги:</strong>
            {% for tag in post.get_tags_list %}
                <a href="{% url 'blog:tag' tag %}" class="tag badge badge-secondary">
                    {{ tag }}
                </a>
            {% endfor %}
        </div>
    </footer>
</article>

<style>
    .blog-post {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }
    
    .post-header {
        margin-bottom: 2rem;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 1rem;
    }
    
    .post-title {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #333;
    }
    
    .post-meta {
        display: flex;
        gap: 1rem;
        color: #6c757d;
        font-size: 0.9rem;
    }
    
    .post-image img {
        width: 100%;
        height: auto;
        border-radius: 8px;
        margin-top: 1rem;
    }
    
    .post-content {
        line-height: 1.7;
        font-size: 1.1rem;
    }
    
    .post-content h1, .post-content h2, .post-content h3 {
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    .post-content code {
        background: #f8f9fa;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-size: 0.9em;
    }
    
    .post-content pre {
        background: #2d2d2d;
        color: #f8f8f2;
        padding: 1rem;
        border-radius: 5px;
        overflow-x: auto;
        margin: 1rem 0;
    }
    
    .post-content table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }
    
    .post-content table th,
    .post-content table td {
        border: 1px solid #dee2e6;
        padding: 0.75rem;
        text-align: left;
    }
    
    .post-content table th {
        background: #f8f9fa;
        font-weight: bold;
    }
    
    .post-footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e9ecef;
    }
    
    .post-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
    }
    
    .tag {
        text-decoration: none;
        padding: 0.25rem 0.5rem;
        background: #007bff;
        color: white;
        border-radius: 3px;
        font-size: 0.8rem;
    }
    
    .tag:hover {
        background: #0056b3;
        text-decoration: none;
        color: white;
    }
</style>

<script>
    // Ленивая загрузка изображений
    document.addEventListener('DOMContentLoaded', function() {
        const images = document.querySelectorAll('.post-content img');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.add('loaded');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => {
                if (!img.classList.contains('loaded')) {
                    imageObserver.observe(img);
                }
            });
        }
        
        // Копирование кода
        document.querySelectorAll('.post-content pre').forEach(block => {
            const button = document.createElement('button');
            button.className = 'copy-code';
            button.textContent = 'Копировать';
            button.style.cssText = `
                position: absolute;
                top: 0.5rem;
                right: 0.5rem;
                background: rgba(255,255,255,0.2);
                border: none;
                color: white;
                padding: 0.25rem 0.5rem;
                border-radius: 3px;
                cursor: pointer;
                font-size: 0.8rem;
            `;
            
            block.style.position = 'relative';
            block.appendChild(button);
            
            button.addEventListener('click', async () => {
                const code = block.querySelector('code').textContent;
                try {
                    await navigator.clipboard.writeText(code);
                    button.textContent = 'Скопировано!';
                    setTimeout(() => {
                        button.textContent = 'Копировать';
                    }, 2000);
                } catch (err) {
                    console.error('Ошибка копирования:', err);
                }
            });
        });
    });
</script>
{% endblock %}
```

## Best Practices и рекомендации

### Архитектурные решения

1. **Выбор стратегии рендеринга:**
   - Для блогов с частыми обновлениями - рендеринг при запросе
   - Для высоконагруженных сайтов - предварительный рендеринг
   - Для смешанного использования - кэширование

2. **Безопасность:**
   - Всегда используйте sanitization
   - Ограничивайте разрешенные теги и атрибуты
   - Проверяйте URL в ссылках
   - Используйте Content Security Policy

3. **Производительность:**
   - Кэшируйте рендеренный HTML
   - Используйте ленивую загрузку изображений
   - Оптимизируйте размеры изображений
   - Минимизируйте использование расширений

### Рекомендуемая структура проекта

```
blog/
├── models.py              # Модели
├── views.py               # Представления
├── urls.py                # URL конфи