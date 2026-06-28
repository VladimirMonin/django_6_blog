from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(ModelAdmin):
    list_display = ("name", "display_token", "is_active", "created_at", "revoked_at", "last_used_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "notes")
    readonly_fields = ("token", "created_at", "revoked_at", "last_used_at")
    actions = ["revoke_keys"]

    fieldsets = (
        ("Основное", {"fields": ("name", "token", "notes")}),
        ("Статус", {"fields": ("is_active", "created_at", "revoked_at", "last_used_at")}),
    )

    @display(description="Токен")
    def display_token(self, obj):
        if obj and obj.token:
            return obj.token[:8] + "…" + obj.token[-4:]
        return "—"

    @admin.action(description="Отозвать выбранные ключи")
    def revoke_keys(self, request, queryset):
        for key in queryset:
            key.revoke()