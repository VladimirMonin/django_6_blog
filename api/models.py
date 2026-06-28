"""API key model for token-based agent authentication."""

import secrets

from django.db import models
from django.utils import timezone


class ApiKey(models.Model):
    """API key for agent access to blog API endpoints."""

    name = models.CharField(max_length=100, verbose_name="Название")
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Токен",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="Отозван")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="Последнее использование")
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API ключ"
        verbose_name_plural = "API ключи"

    def __str__(self):
        masked = self.token[:8] + "…" if len(self.token) > 8 else self.token
        return f"{self.name} ({masked})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def revoke(self):
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])

    def touch(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    @classmethod
    def verify(cls, token: str) -> "ApiKey | None":
        """Return active ApiKey for token, or None if invalid/revoked."""
        if not token:
            return None
        try:
            key = cls.objects.get(token=token, is_active=True)
            key.touch()
            return key
        except cls.DoesNotExist:
            return None