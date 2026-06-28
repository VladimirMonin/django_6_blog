import re
from io import BytesIO
from pathlib import PurePath

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.text import Truncator

from PIL import Image, ImageOps

from blog.content_import.timecodes import time_to_seconds
from blog.services import convert_markdown_to_html
from blog.slug_utils import build_slug, build_unique_slug


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
    stem = build_slug(path.stem, fallback="file")
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
            self.slug = build_unique_slug(self, self.name, fallback="category")
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
            self.slug = build_unique_slug(self, self.name, fallback="tag")
        super().save(*args, **kwargs)


class Series(models.Model):
    """Ordered group of posts — courses, podcast sequences, article series."""

    name = models.CharField(max_length=200, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=220, unique=True, verbose_name="URL-slug")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ["name"]
        verbose_name = "Серия"
        verbose_name_plural = "Серии"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.name, fallback="series")
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
        ARCHIVED = "archived", "В архиве"

    class ContentType(models.TextChoices):
        ARTICLE = "article", "Статья"
        VIDEO = "video", "Видео"
        AUDIO = "audio", "Аудио"
        PODCAST = "podcast", "Подкаст"

    title = models.CharField(max_length=200, verbose_name="Заголовок")
    description = models.TextField(verbose_name="Описание")
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.ARTICLE,
        db_index=True,
        verbose_name="Тип записи",
    )
    media_url = models.URLField(blank=True, verbose_name="URL основного медиа")
    timecodes = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Таймкоды",
        help_text="Список объектов: time, seconds, label.",
    )
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL-slug")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="Категория",
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="Серия",
    )
    series_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок в серии",
        help_text="Порядковый номер поста в серии (0, 1, 2, ...).",
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
    source_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
        unique=True,
        verbose_name="Внешний ID",
        help_text="Идемпотентный ключ для агентских публикаций.",
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Дата публикации",
        help_text="Заполняется при переходе в published. Для scheduled publishing.",
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Рекомендуемый",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Удалён",
        help_text="Soft delete timestamp. Null = active.",
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
        return reverse("post_detail", kwargs={"slug": self.slug})

    def soft_delete(self):
        """Mark this post as deleted without removing it from the database."""
        self.deleted_at = timezone.now()
        self.status = self.Status.ARCHIVED
        self.save(update_fields=["deleted_at", "status", "updated_at"])

    def hard_delete(self, *args, **kwargs):
        """Actually remove this post from the database."""
        return super().delete(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Default to soft delete. Use hard_delete() to truly remove."""
        self.soft_delete()

    def clean(self):
        super().clean()
        if self.content_type not in {
            self.ContentType.VIDEO,
            self.ContentType.AUDIO,
            self.ContentType.PODCAST,
        }:
            return
        if not self.timecodes:
            return
        if not isinstance(self.timecodes, list):
            raise ValidationError({"timecodes": "Invalid timecode data: expected a list."})
        for index, entry in enumerate(self.timecodes, start=1):
            if not isinstance(entry, dict):
                raise ValidationError({"timecodes": f"Invalid timecode #{index}: expected an object."})
            time_text = entry.get("time")
            label = entry.get("label")
            seconds = entry.get("seconds")
            if not isinstance(time_text, str) or not isinstance(label, str) or not label.strip():
                raise ValidationError({"timecodes": f"Invalid timecode #{index}: time and label are required."})
            try:
                expected_seconds = time_to_seconds(time_text)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"timecodes": f"Invalid timecode #{index}: {time_text!r}. {exc}"}) from exc
            if not isinstance(seconds, int) or seconds != expected_seconds:
                raise ValidationError(
                    {"timecodes": f"Invalid timecode #{index}: seconds must match {time_text!r}."}
                )

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
    def primary_media(self):
        """Return the first attached media file matching the post content type."""
        media_type_map = {
            self.ContentType.VIDEO: PostMedia.MediaType.VIDEO,
            self.ContentType.AUDIO: PostMedia.MediaType.AUDIO,
            self.ContentType.PODCAST: PostMedia.MediaType.AUDIO,
        }
        expected_type = media_type_map.get(self.content_type)
        if not expected_type:
            return None
        prefetched_media = getattr(self, "_prefetched_objects_cache", {}).get("media_files")
        if prefetched_media is not None:
            return next(
                (media for media in prefetched_media if media.media_type == expected_type),
                None,
            )
        return self.media_files.filter(media_type=expected_type).first()

    @property
    def player_media_url(self):
        """Return external media URL or uploaded primary media URL for players."""
        if self.media_url:
            return self.media_url
        media = self.primary_media
        return media.file.url if media else ""

    @property
    def has_media_player(self):
        return self.content_type in {
            self.ContentType.VIDEO,
            self.ContentType.AUDIO,
            self.ContentType.PODCAST,
        } and bool(self.player_media_url)

    @property
    def uses_video_player(self):
        return self.content_type == self.ContentType.VIDEO

    @property
    def uses_audio_player(self):
        return self.content_type in {self.ContentType.AUDIO, self.ContentType.PODCAST}

    @property
    def body_content_html(self):
        """Return rendered HTML without duplicate title or raw service media embeds.

        The result is cached per-post for 1 hour. The cache is invalidated
        in ``save()`` so stale HTML is never served after content changes.
        """
        if not self.pk:
            return ""
        cache_key = f"post:{self.pk}:body_html"
        return cache.get_or_set(
            cache_key,
            lambda: self._compute_body_content_html(),
            timeout=3600,
        )

    def _compute_body_content_html(self):
        """Compute body_content_html from ``content_html`` (uncached)."""
        html = self.content_html or ""
        match = re.match(r"\s*<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
        if match and strip_tags(match.group(1)).strip().casefold() == self.title.strip().casefold():
            html = html[match.end() :].lstrip()
        html = re.sub(
            r"\s*<p>\s*!\[\[[^\]]+\]\]\s*</p>\s*",
            "",
            html,
            flags=re.IGNORECASE,
        )
        return html

    @property
    def plain_text_excerpt(self):
        """Return a clean preview without raw Markdown, Obsidian embeds, or HTML tags."""
        text = self.content or ""
        text = re.sub(r"(?s)^---.*?---", " ", text)
        text = re.sub(r"(?s)```.*?```", " ", text)
        text = re.sub(r"(?m)^\s*\|.*\|\s*$", " ", text)
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
            self.slug = build_unique_slug(self, self.title, fallback="post")

        if self.content:
            self.content_html = convert_markdown_to_html(self.content, post=self)

        # Auto-fill published_at when transitioning to published
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        self.clean()
        super().save(*args, **kwargs)

        # Invalidate cached body_content_html so stale HTML is never served
        # after content changes.
        if self.pk:
            cache.delete(f"post:{self.pk}:body_html")


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
    thumbnail_og = models.FileField(
        upload_to="posts/thumbnails/",
        blank=True,
        null=True,
        verbose_name="OG-превью (1200×630)",
    )
    thumbnail_card = models.FileField(
        upload_to="posts/thumbnails/",
        blank=True,
        null=True,
        verbose_name="Карточное превью (400×300)",
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

    @property
    def thumbnail_og_url(self):
        """Return OG thumbnail URL if available, falling back to original file."""
        if self.thumbnail_og:
            return self.thumbnail_og.url
        return self.file.url

    @property
    def thumbnail_card_url(self):
        """Return card thumbnail URL if available, falling back to original file."""
        if self.thumbnail_card:
            return self.thumbnail_card.url
        return self.file.url

    def _generate_thumbnail(self, size, quality=85):
        """Generate a cover-cropped JPEG thumbnail ContentFile of the given size."""
        with Image.open(self.file.path) as img:
            img = img.convert("RGB")
            img = ImageOps.fit(img, size, method=Image.LANCZOS, centering=(0.5, 0.4))
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            return ContentFile(buffer.getvalue())

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = PurePath(self.file.name).name
        if self.original_filename and not self.file_slug:
            self.file_slug = build_file_slug(self.original_filename)
        self.media_type = self.detect_media_type()
        super().save(*args, **kwargs)

        # Generate thumbnails for images after the initial save, but avoid
        # recursion and skip SVG (Pillow cannot open SVG) and any file that
        # Pillow cannot read (e.g. test stubs with fake bytes).
        if getattr(self, "_generating_thumbnails", False):
            return
        if self.media_type != self.MediaType.IMAGE:
            return
        if not self.file:
            return
        if self.thumbnail_og and self.thumbnail_card:
            return
        extension = PurePath(self.file_slug or self.file.name).suffix.lower()
        if extension == ".svg":
            return
        try:
            self._generating_thumbnails = True
            update_fields = []
            if not self.thumbnail_og:
                og_thumb = self._generate_thumbnail((1200, 630))
                og_name = f"{self.file_slug}_og.jpg"
                self.thumbnail_og.save(og_name, og_thumb, save=False)
                update_fields.append("thumbnail_og")
            if not self.thumbnail_card:
                card_thumb = self._generate_thumbnail((400, 300))
                card_name = f"{self.file_slug}_card.jpg"
                self.thumbnail_card.save(card_name, card_thumb, save=False)
                update_fields.append("thumbnail_card")
            if update_fields:
                super().save(update_fields=update_fields)
        except Exception:
            # Pillow could not open the file (corrupt, fake bytes, etc.)
            # Silently skip — thumbnail fields stay empty and URL properties
            # fall back to the original file URL.
            pass
        finally:
            self._generating_thumbnails = False


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


class AuditLog(models.Model):
    """Append-only audit trail for API-driven post actions."""

    class Action(models.TextChoices):
        PUBLISHED = "published", "Опубликовано"
        UPDATED = "updated", "Обновлено"
        STATUS_CHANGED = "status_changed", "Смена статуса"
        DELETED = "deleted", "Удалено"
        RESTORED = "restored", "Восстановлено"

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        db_index=True,
        verbose_name="Действие",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name="Пост",
    )
    post_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Заголовок поста (снапшот)",
    )
    post_slug = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Slug поста (снапшот)",
    )
    api_key = models.ForeignKey(
        "api.ApiKey",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name="API ключ",
    )
    api_key_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Имя ключа (снапшот)",
    )
    detail = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Детали",
        help_text="Дополнительные данные: old_status, new_status, source_id и т.д.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Запись аудита"
        verbose_name_plural = "Записи аудита"

    def __str__(self):
        return f"{self.action} — {self.post_slug or self.post_title} — {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def log(cls, *, action, post=None, api_key=None, detail=None):
        """Create an audit entry with snapshot fields."""
        entry = cls(action=action, detail=detail or {})
        if post:
            entry.post = post
            entry.post_title = post.title
            entry.post_slug = post.slug
        if api_key:
            entry.api_key = api_key
            entry.api_key_name = api_key.name
        entry.save()
        return entry


class PostView(models.Model):
    """Individual post view event for analytics (one row per session+post+day)."""

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="view_events",
        verbose_name="Пост",
    )
    session_key = models.CharField(
        max_length=40,
        db_index=True,
        verbose_name="Ключ сессии",
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Дата просмотра",
    )
    read_depth = models.FloatField(
        default=0.0,
        verbose_name="Глубина чтения",
        help_text="Доля прочитанного контента: 0.0 — 1.0.",
    )

    class Meta:
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["post", "viewed_at"]),
            models.Index(fields=["session_key", "viewed_at"]),
        ]
        verbose_name = "Просмотр поста"
        verbose_name_plural = "Просмотры постов"

    def __str__(self):
        return f"{self.post_id} — {self.session_key[:8]} — {self.viewed_at:%Y-%m-%d}"
