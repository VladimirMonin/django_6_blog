# Безопасность и Sanitization в Python-Markdown

## Защита от XSS атак

### Проблема безопасности в Markdown

Markdown может содержать опасный HTML и JavaScript:

```markdown
[Опасная ссылка](javascript:alert('XSS'))

<img src="x" onerror="alert('XSS')">

<script>alert('XSS')</script>
```

### Решение: Использование bleach

```python
# blog/utils.py
import markdown
import bleach
from django.utils.safestring import mark_safe

def safe_markdown(text):
    """Безопасный рендеринг markdown с очисткой HTML"""
    
    # Разрешенные HTML теги
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'blockquote', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img', 'span', 'div',
        'abbr', 'acronym', 'sub', 'sup',
    ]
    
    # Разрешенные атрибуты
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
        'span': ['class'],
        'div': ['class'],
        'table': ['class'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan'],
    }
    
    # Разрешенные протоколы для ссылок
    allowed_protocols = ['http', 'https', 'mailto', 'tel']
    
    # Рендеринг markdown
    html = markdown.markdown(
        text,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
        ]
    )
    
    # Очистка HTML
    clean_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols,
        strip=True
    )
    
    # Добавление rel="nofollow noopener" для внешних ссылок
    from urllib.parse import urlparse
    
    def link_callback(attrs, new=False):
        href = attrs.get('href', '')
        
        # Проверка на внешние ссылки
        if href.startswith('http'):
            domain = urlparse(href).netloc
            # Если это не наш домен
            if domain and domain not in ['example.com', 'localhost']:
                attrs['rel'] = 'nofollow noopener'
                attrs['target'] = '_blank'
        
        return attrs
    
    clean_html = bleach.linkify(clean_html, callbacks=[link_callback])
    
    return mark_safe(clean_html)
```

### Интеграция с моделью

```python
# blog/models.py
from django.db import models
from .utils import safe_markdown

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content_markdown = models.TextField()
    content_html = models.TextField(blank=True)
    
    def save(self, *args, **kwargs):
        if self.content_markdown:
            self.content_html = safe_markdown(self.content_markdown)
        super().save(*args, **kwargs)
    
    @property
    def safe_content(self):
        """Безопасный контент для шаблонов"""
        return safe_markdown(self.content_markdown)
```

### Template filter с безопасностью

```python
# blog/templatetags/markdown_safe.py
import markdown
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdown_safe')
def markdown_safe_filter(text):
    """Безопасный markdown filter"""
    
    # Настройки безопасности
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 's', 'blockquote', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img', 'span', 'div',
    ]
    
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
    }
    
    # Рендеринг markdown
    html = markdown.markdown(
        text,
        extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
        ]
    )
    
    # Очистка
    clean_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=['http', 'https', 'mailto'],
        strip=True
    )
    
    return mark_safe(clean_html)
```

## Django-Bleach интеграция

### Установка и настройка

```bash
pip install django-bleach
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'django_bleach',
]

# Настройки bleach
BLEACH_ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'blockquote', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a', 'img', 'span', 'div',
]

BLEACH_ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre': ['class'],
    'span': ['class'],
    'div': ['class'],
}

BLEACH_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'tel']

BLEACH_STRIP_TAGS = True
BLEACH_STRIP_COMMENTS = True
```

### Использование в моделях

```python
# blog/models.py
from django.db import models
from django_bleach.models import BleachField

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content_markdown = models.TextField()
    content_html = BleachField(blank=True)
    
    def save(self, *args, **kwargs):
        import markdown
        
        if self.content_markdown:
            # Рендеринг markdown
            html = markdown.markdown(
                self.content_markdown,
                extensions=['extra', 'codehilite', 'toc']
            )
            # Bleach автоматически очистит HTML при сохранении
            self.content_html = html
        
        super().save(*args, **kwargs)
```

## Защита от других угроз

### Ограничение размера файлов

```python
# settings.py
# Для django-markdownx
MARKDOWNX_UPLOAD_MAX_SIZE = 10 * 1024 * 1024  # 10MB
MARKDOWNX_IMAGE_MAX_SIZE = {'size': (1920, 1080), 'quality': 85}
```

### Валидация URL

```python
# blog/utils.py
from urllib.parse import urlparse

def is_safe_url(url):
    """Проверка безопасности URL"""
    try:
        parsed = urlparse(url)
        
        # Разрешенные протоколы
        allowed_schemes = ['http', 'https', 'mailto', 'tel']
        
        # Запрещенные домены
        blocked_domains = ['malicious.com', 'spam.com']
        
        if parsed.scheme not in allowed_schemes:
            return False
        
        if parsed.netloc in blocked_domains:
            return False
        
        return True
    except:
        return False
```

### Content Security Policy (CSP)

```python
# settings.py
# Для дополнительной защиты
MIDDLEWARE = [
    # ...
    'csp.middleware.CSPMiddleware',
]

CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]  # для подсветки синтаксиса
CSP_IMG_SRC = ["'self'", "data:", "https:"]
CSP_FONT_SRC = ["'self'"]
```

## Тестирование безопасности

```python
# blog/tests/test_security.py
from django.test import TestCase
from .utils import safe_markdown

class SecurityTests(TestCase):
    
    def test_xss_protection(self):
        """Тестирование защиты от XSS"""
        
        # Опасный markdown
        dangerous_content = """
        [Опасная ссылка](javascript:alert('XSS'))
        
        <script>alert('XSS')</script>
        
        <img src="x" onerror="alert('XSS')">
        """
        
        safe_html = safe_markdown(dangerous_content)
        
        # Проверка, что опасный код удален
        self.assertNotIn('javascript:', safe_html)
        self.assertNotIn('<script>', safe_html)
        self.assertNotIn('onerror', safe_html)
    
    def test_safe_tags_preserved(self):
        """Проверка, что безопасные теги сохраняются"""
        
        safe_content = """
        # Заголовок
        
        **Жирный текст** и *курсив*.
        
        [Безопасная ссылка](https://example.com)
        
        ```python
        print("Безопасный код")
        ```
        """
        
        safe_html = safe_markdown(safe_content)
        
        # Проверка сохранения безопасных элементов
        self.assertIn('<h1>', safe_html)
        self.assertIn('<strong>', safe_html)
        self.assertIn('<em>', safe_html)
        self.assertIn('href="https://example.com"', safe_html)
        self.assertIn('<code', safe_html)
```

## Best Practices безопасности

1. **Всегда используйте sanitization** - никогда не доверяйте пользовательскому вводу
2. **Ограничивайте разрешенные теги** - разрешайте только необходимые
3. **Проверяйте URL** - запрещайте опасные протоколы
4. **Используйте CSP** - дополнительный уровень защиты
5. **Тестируйте безопасность** - регулярно проверяйте на уязвимости
6. **Обновляйте зависимости** - следите за обновлениями безопасности
7. **Логируйте подозрительную активность** - мониторинг попыток XSS