from pathlib import PurePath

from django.db import models
from django.urls import reverse
from transliterate import slugify as transliterate_slugify
from django.utils.text import slugify as django_slugify

from blog.services import convert_markdown_to_html


def post_media_upload_to(instance, filename):
    """Return post-scoped media path for uploaded files."""
    post_slug = instance.post.slug or "unslugged-post"
    filename = instance.file_slug or PurePath(filename).name
    return f"posts/{post_slug}/{filename}"


def build_file_slug(filename):
    """Create a URL-safe filename while preserving the original extension."""
    path = PurePath(filename)
    stem = django_slugify(path.stem) or "file"
    extension = path.suffix.lower()
    return f"{stem}{extension}"


class Category(models.Model):
    """Public category used to group blog posts."""

    name = models.CharField(max_length=120, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=140, unique=True, verbose_name="URL-slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ["name"]
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = transliterate_slugify(self.name) or django_slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Public tag used for cross-cutting post topics."""

    name = models.CharField(max_length=80, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL-slug")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ["name"]
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = transliterate_slugify(self.name) or django_slugify(self.name)
        super().save(*args, **kwargs)


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
        category: Основная категория поста
        tags: Тематические теги поста
        status: Статус публикации (published/draft)
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        PUBLISHED = "published", "Опубликовано"

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-slug")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="Категория",
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
        verbose_name="Теги",
    )
    content = models.TextField(verbose_name="Содержимое (Markdown)")
    content_html = models.TextField(
        blank=True, editable=False, verbose_name="HTML контент"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PUBLISHED,
        db_index=True,
        verbose_name="Статус",
    )

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
            self.slug = transliterate_slugify(self.title) or django_slugify(self.title)

        # Конвертация Markdown → HTML при каждом сохранении
        if self.content:
            self.content_html = convert_markdown_to_html(self.content, post=self)

        super().save(*args, **kwargs)


class PostMedia(models.Model):
    """Media file attached to a single blog post."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Изображение"
        VIDEO = "video", "Видео"
        AUDIO = "audio", "Аудио"
        DOCUMENT = "document", "Документ"
        OTHER = "other", "Другое"

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".opus", ".m4a", ".flac"}
    DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx"}

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="media_files",
        verbose_name="Пост",
    )
    file = models.FileField(upload_to=post_media_upload_to, verbose_name="Файл")
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Оригинальное имя файла",
    )
    file_slug = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="URL-имя файла",
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        default=MediaType.OTHER,
        verbose_name="Тип медиа",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["post", "original_filename"],
                name="unique_media_filename_per_post",
            ),
            models.UniqueConstraint(
                fields=["post", "file_slug"],
                name="unique_media_slug_per_post",
            ),
        ]
        verbose_name = "Медиафайл поста"
        verbose_name_plural = "Медиафайлы постов"

    def __str__(self):
        return self.original_filename or self.file.name

    @property
    def markdown_link(self):
        return f"![{self.original_filename}]({self.file.url})"

    def detect_media_type(self):
        extension = PurePath(self.file_slug or self.file.name).suffix.lower()
        if extension in self.IMAGE_EXTENSIONS:
            return self.MediaType.IMAGE
        if extension in self.VIDEO_EXTENSIONS:
            return self.MediaType.VIDEO
        if extension in self.AUDIO_EXTENSIONS:
            return self.MediaType.AUDIO
        if extension in self.DOCUMENT_EXTENSIONS:
            return self.MediaType.DOCUMENT
        return self.MediaType.OTHER

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = PurePath(self.file.name).name
        if self.original_filename and not self.file_slug:
            self.file_slug = build_file_slug(self.original_filename)
        self.media_type = self.detect_media_type()
        super().save(*args, **kwargs)
