from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Category, Post, PostMedia, SessionPostInteraction, Tag


class PostMediaInline(admin.TabularInline):
    """Prototype uploader for post-scoped media files."""

    model = PostMedia
    extra = 1
    fields = (
        "file",
        "original_filename",
        "file_slug",
        "media_type",
        "display_markdown_link",
        "display_preview",
    )
    readonly_fields = (
        "original_filename",
        "file_slug",
        "media_type",
        "display_markdown_link",
        "display_preview",
    )

    @display(description="Markdown-ссылка")
    def display_markdown_link(self, obj):
        if obj and obj.pk:
            return obj.markdown_link
        return "—"

    @display(description="Предпросмотр")
    def display_preview(self, obj):
        if not obj or not obj.pk:
            return "—"
        if obj.media_type == PostMedia.MediaType.IMAGE:
            return format_html(
                '<img src="{}" alt="{}" style="max-width: 160px; max-height: 90px; object-fit: contain;" />',
                obj.file.url,
                obj.original_filename,
            )
        return format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, obj.original_filename)


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PostMedia)
class PostMediaAdmin(ModelAdmin):
    list_display = ("original_filename", "post", "media_type", "created_at")
    list_filter = ("media_type", "created_at")
    search_fields = ("original_filename", "file_slug", "post__title")
    readonly_fields = ("original_filename", "file_slug", "media_type", "created_at")


@admin.register(SessionPostInteraction)
class SessionPostInteractionAdmin(ModelAdmin):
    list_display = ("session_key", "post", "viewed_at", "liked_at", "updated_at")
    list_filter = ("viewed_at", "liked_at", "updated_at")
    search_fields = ("session_key", "post__title")
    readonly_fields = ("session_key", "post", "viewed_at", "liked_at", "created_at", "updated_at")


@admin.register(Post)
class PostAdmin(ModelAdmin):
    """
    Административный интерфейс для модели Post с Unfold UI.
    """

    list_display = ("title", "category", "status", "view_count", "like_count", "display_created_at")
    list_filter = ("status", "category", "tags", "created_at")
    search_fields = ("title", "description", "content", "category__name", "tags__name")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    filter_horizontal = ("tags",)
    inlines = [PostMediaInline]

    fieldsets = (
        ("Основная информация", {"fields": ("title", "slug", "description", "category", "tags", "content")}),
        (
            "HTML предпросмотр",
            {"fields": ("display_html_preview",), "classes": ("collapse",)},
        ),
        ("Статус и реакции", {"fields": ("status", "view_count", "like_count")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ("created_at", "updated_at", "view_count", "like_count", "display_html_preview")

    # Custom actions
    @admin.action(description="Опубликовать выбранные посты")
    def publish_posts(self, request, queryset):
        queryset.update(status=Post.Status.PUBLISHED)

    @admin.action(description="Перевести в черновики")
    def unpublish_posts(self, request, queryset):
        queryset.update(status=Post.Status.DRAFT)

    actions = [publish_posts, unpublish_posts]

    # Display methods with Unfold decorators
    @display(description="Дата создания")
    def display_created_at(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    @display(description="HTML контент")
    def display_html_preview(self, obj):
        """Предпросмотр сгенерированного HTML контента."""
        if obj.content_html:
            return format_html(
                '<div style="max-height: 400px; overflow: auto; padding: 15px; '
                'background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px;">'
                "{}</div>",
                obj.content_html,
            )
        return "—"
