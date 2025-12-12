from django.db import models
from django.urls import reverse
from transliterate import slugify


class Post(models.Model):
    """
    Модель поста блога.
    
    Attributes:
        title: Заголовок поста
        slug: URL-slug для SEO-дружественных адресов
        content: Содержимое поста (поддержка Markdown добавится позже)
        created_at: Дата и время создания
        updated_at: Дата и время последнего обновления
        is_published: Статус публикации (опубликован/черновик)
    """
    title = models.CharField(
        max_length=200,
        verbose_name='Заголовок'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='URL-slug'
    )
    content = models.TextField(
        verbose_name='Содержимое'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        """
        Возвращает абсолютный URL для детального просмотра поста.
        """
        return reverse('post_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """
        Автоматическая генерация slug из заголовка при сохранении.
        """
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

