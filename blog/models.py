import re
from pathlib import PurePath

from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator, slugify as django_slugify
from transliterate import slugify as transliterate_slugify

from blog.services import convert_markdown_to_html


def format_ru_count(value, forms):
    """Return a Russian pluralized counter label, e.g. '21 просмотр'."""
    value = int(value or 0)
    last_two = value % 100
    last = value % 10
    if 11 <= last_two <= 14:
        form = forms[2]
    elif last == 1:
        form = forms[0]
    elif 2 <= last <= 4:
        form = forms[1]
    else:
        form = forms[2]
    return f"{value} {form}"


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
    view_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    like_count = models.PositiveIntegerField(default=0, verbose_name="Лайки")

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

    @property
    def cover_media(self):
        """Return the first attached image as the public cover for list/detail UI."""
        prefetched_media = getattr(self, "_prefetched_objects_cache", {}).get("media_files")
        if prefetched_media is not None:
            return next(
                (media for media in prefetched_media if media.media_type == PostMedia.MediaType.IMAGE),
                None,
            )
        return self.media_files.filter(media_type=PostMedia.MediaType.IMAGE).first()

    @property
    def body_content_html(self):
        """Return rendered HTML without a leading H1 that duplicates the post title."""
        html = self.content_html or ""
        match = re.match(r"\s*<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
        if match and strip_tags(match.group(1)).strip().casefold() == self.title.strip().casefold():
            return html[match.end() :].lstrip()
        return html

    @property
    def plain_text_excerpt(self):
        """Return a clean preview without raw Markdown, Obsidian embeds, or HTML tags."""
        text = self.content or ""
        text = re.sub(r"(?s)^---.*?---", " ", text)
        text = re.sub(r"(?s)```.*?```", " ", text)
        text = re.sub(r"!\[\[[^\]]+\]\]", " ", text)
        text = re.sub(r"\[\[[^\]]+\]\]", " ", text)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
        text = re.sub(r"(?m)^\s{0,3}>\s?", "", text)
        text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
        text = strip_tags(text)
        text = re.sub(r"[#*_>`~\-]{2,}", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if self.title and text.lower().startswith(self.title.lower()):
            text = text[len(self.title) :].strip(" —-:·")
        return Truncator(text).words(42)

    @property
    def view_count_label(self):
        return format_ru_count(self.view_count, ("просмотр", "просмотра", "просмотров"))

    @property
    def like_count_label(self):
        return format_ru_count(self.like_count, ("лайк", "лайка", "лайков"))

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


class SessionPostInteraction(models.Model):
    """Central history of anonymous session interactions with public posts."""

    session_key = models.CharField(max_length=40, db_index=True, verbose_name="Ключ сессии")
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="session_interactions",
        verbose_name="Пост",
    )
    viewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Первый просмотр")
    liked_at = models.DateTimeField(null=True, blank=True, verbose_name="Лайк поставлен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session_key", "post"],
                name="unique_session_interaction_per_post",
            )
        ]
        indexes = [
            models.Index(fields=["session_key", "liked_at"]),
            models.Index(fields=["post", "viewed_at"]),
        ]
        ordering = ["-updated_at"]
        verbose_name = "Сессионное действие с постом"
        verbose_name_plural = "Сессионные действия с постами"

    def __str__(self):
        return f"{self.session_key}: {self.post_id}"

    @property
    def is_liked(self):
        return self.liked_at is not None

    def mark_viewed(self):
        if self.viewed_at is None:
            self.viewed_at = timezone.now()
            self.save(update_fields=["viewed_at", "updated_at"])
            return True
        return False

    def toggle_like(self):
        if self.liked_at is None:
            self.liked_at = timezone.now()
            self.save(update_fields=["liked_at", "updated_at"])
            return True
        self.liked_at = None
        self.save(update_fields=["liked_at", "updated_at"])
        return False
