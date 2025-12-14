from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from .models import Post


@admin.register(Post)
class PostAdmin(ModelAdmin):
    """
    Административный интерфейс для модели Post с Unfold UI.
    """

    list_display = ("title", "slug", "display_created_at", "display_published")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        ("Основная информация", {"fields": ("title", "slug", "content")}),
        ("Статус", {"fields": ("is_published",)}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ("created_at", "updated_at")

    # Custom actions
    @admin.action(description="Опубликовать выбранные посты")
    def publish_posts(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description="Снять с публикации")
    def unpublish_posts(self, request, queryset):
        queryset.update(is_published=False)

    actions = [publish_posts, unpublish_posts]

    # Display methods with Unfold decorators
    @display(description="Дата создания")
    def display_created_at(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    @display(description="Статус", boolean=True)
    def display_published(self, obj):
        return obj.is_published
