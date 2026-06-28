from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import (
    AuditLog,
    Category,
    Post,
    PostMedia,
    PostView,
    Series,
    SessionPostInteraction,
    Tag,
)


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


@admin.register(Series)
class SeriesAdmin(ModelAdmin):
    list_display = ("name", "slug", "post_count", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}

    @display(description="Постов")
    def post_count(self, obj):
        return obj.posts.count()


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

    list_display = ("title", "content_type", "category", "status", "is_featured", "view_count", "like_count", "display_created_at")
    list_filter = ("content_type", "status", "is_featured", "category", "tags", "created_at")
    search_fields = ("title", "description", "content", "category__name", "tags__name")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    filter_horizontal = ("tags",)
    inlines = [PostMediaInline]

    fieldsets = (
        ("Основная информация", {"fields": ("title", "slug", "description", "category", "series", "series_order", "tags", "content")}),
        ("Тип и медиа", {"fields": ("content_type", "media_url", "timecodes")}),
        (
            "HTML предпросмотр",
            {"fields": ("display_html_preview",), "classes": ("collapse",)},
        ),
        ("Статус и публикации", {"fields": ("status", "published_at", "is_featured", "source_id", "view_count", "like_count")}),
        ("Даты", {"fields": ("created_at", "updated_at", "deleted_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ("created_at", "updated_at", "deleted_at", "published_at", "view_count", "like_count", "display_html_preview")

    # Custom actions
    @admin.action(description="Опубликовать выбранные посты")
    def publish_posts(self, request, queryset):
        from django.utils import timezone
        for post in queryset:
            post.status = Post.Status.PUBLISHED
            if not post.published_at:
                post.published_at = timezone.now()
            post.save(update_fields=["status", "published_at", "updated_at"])

    @admin.action(description="Перевести в черновики")
    def unpublish_posts(self, request, queryset):
        queryset.update(status=Post.Status.DRAFT)

    @admin.action(description="В архив")
    def archive_posts(self, request, queryset):
        queryset.update(status=Post.Status.ARCHIVED)

    @admin.action(description="Отметить как рекомендуемые")
    def feature_posts(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Снять отметку «рекомендуемый»")
    def unfeature_posts(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="Мягко удалить (в архив + deleted_at)")
    def soft_delete_posts(self, request, queryset):
        from django.utils import timezone
        now = timezone.now()
        for post in queryset:
            post.deleted_at = now
            post.status = Post.Status.ARCHIVED
            post.save(update_fields=["deleted_at", "status", "updated_at"])

    actions = [publish_posts, unpublish_posts, archive_posts, feature_posts, unfeature_posts, soft_delete_posts]

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


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ("action", "post_slug", "api_key_name", "created_at")
    list_filter = ("action", "created_at", "api_key")
    search_fields = ("post_slug", "post_title", "api_key_name")
    readonly_fields = ("action", "post", "post_title", "post_slug", "api_key", "api_key_name", "detail", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(PostView)
class PostViewAdmin(ModelAdmin):
    list_display = ("post", "session_key", "viewed_at", "read_depth")
    list_filter = ("viewed_at",)
    search_fields = ("post__title", "session_key")
    readonly_fields = ("post", "session_key", "viewed_at", "read_depth")
    date_hierarchy = "viewed_at"
    ordering = ("-viewed_at",)

    def has_add_permission(self, request):
        return False
