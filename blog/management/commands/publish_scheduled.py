"""Management command to publish scheduled drafts.

Posts with status=draft and published_at <= now are published.
Run via cron or manually: uv run python manage.py publish_scheduled
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Post


class Command(BaseCommand):
    help = "Publish scheduled draft posts whose published_at has arrived."

    def handle(self, *args, **options):
        now = timezone.now()
        scheduled = Post.objects.filter(
            status=Post.Status.DRAFT,
            published_at__isnull=False,
            published_at__lte=now,
            deleted_at__isnull=True,
        )
        count = scheduled.count()
        if count == 0:
            self.stdout.write("No scheduled posts to publish.")
            return

        for post in scheduled:
            post.status = Post.Status.PUBLISHED
            post.save(update_fields=["status", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(f"Published {count} scheduled post(s).")
        )