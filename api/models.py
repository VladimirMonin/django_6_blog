"""API key and publishing ledger models for agent authentication."""

import secrets

from django.db import models
from django.utils import timezone


class ApiKey(models.Model):
    """API key for agent access to blog API endpoints."""

    name = models.CharField(max_length=100, verbose_name="Название")
    token = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Токен")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="Отозван")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="Последнее использование")
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Истекает",
        help_text="Пусто = бессрочно.",
    )
    permissions = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Разрешения",
        help_text='Список: ["read", "publish", "delete", "status", "stats"].',
    )
    notes = models.TextField(blank=True, verbose_name="Заметки")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API ключ"
        verbose_name_plural = "API ключи"

    def __str__(self):
        masked = self.token[:8] + "…" if len(self.token) > 8 else self.token
        return f"{self.name} ({masked})"

    DEFAULT_PERMISSIONS = ["read", "publish", "delete", "status", "stats"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.permissions:
            self.permissions = list(self.DEFAULT_PERMISSIONS)
        super().save(*args, **kwargs)

    def revoke(self):
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at"])

    def touch(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    @property
    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def has_permission(self, perm: str) -> bool:
        return perm in (self.permissions or [])

    @classmethod
    def verify(cls, token: str) -> "ApiKey | None":
        """Return active, non-expired ApiKey for token, or None if invalid/revoked/expired."""
        if not token:
            return None
        try:
            key = cls.objects.get(token=token, is_active=True)
            if key.is_expired:
                return None
            key.touch()
            return key
        except cls.DoesNotExist:
            return None


class PublishPackage(models.Model):
    """Durable idempotency ledger for multipart post publication."""

    class State(models.TextChoices):
        PENDING = "pending", "В обработке"
        DONE = "done", "Завершён"
        FAILED = "failed", "Ошибка"

    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name="publish_packages")
    idempotency_key = models.CharField(max_length=128)
    payload_sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING, db_index=True)
    storage_names = models.JSONField(default=list, blank=True)
    response = models.JSONField(default=dict, blank=True)
    post = models.ForeignKey(
        "blog.Post",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publish_packages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["api_key", "idempotency_key"],
                name="unique_publish_package_key",
            )
        ]
        ordering = ["-created_at"]
