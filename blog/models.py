from django.db import models
from django.urls import reverse
from transliterate import slugify

from blog.services import convert_markdown_to_html


class Post(models.Model):
    """
    Модель поста блога.

    Attributes:
        title: Заголовок поста
        slug: URL-slug для SEO-дружественных адресов
        content: Содержимое поста в формате Markdown
        content_html: HTML-версия содержимого (генерируется автоматически)
        created_at: Дата и время создания
        updated_at: Дата и время последнего обновления
        is_published: Статус публикации (опубликован/черновик)
    """

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-slug")
    content = models.TextField(verbose_name="Содержимое (Markdown)")
    content_html = models.TextField(
        blank=True, editable=False, verbose_name="HTML контент"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Пост"
        verbose_name_plural = "Посты"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """
        Возвращает абсолютный URL для детального просмотра поста.
        """
        return reverse("post_detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """
        Автоматическая генерация slug и HTML контента при сохранении.

        1. Генерирует slug из заголовка (если не указан)
        2. Конвертирует Markdown → HTML (всегда, при create и update)
        """
        if not self.slug:
            self.slug = slugify(self.title)

        # Конвертация Markdown → HTML при каждом сохранении
        if self.content:
            self.content_html = convert_markdown_to_html(self.content)

        super().save(*args, **kwargs)
