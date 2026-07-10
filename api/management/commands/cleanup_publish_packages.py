"""Remove storage objects owned by stale incomplete publish packages."""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.models import PublishPackage
from blog.models import PostMedia


class Command(BaseCommand):
    help = "Delete files recorded by stale pending/failed publish packages."

    def add_arguments(self, parser):
        parser.add_argument("--older-than-hours", type=int, default=24)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        hours = options["older_than_hours"]
        if hours < 1:
            raise CommandError("--older-than-hours must be at least 1")
        cutoff = timezone.now() - timedelta(hours=hours)
        packages = PublishPackage.objects.filter(
            state__in=[PublishPackage.State.PENDING, PublishPackage.State.FAILED],
            updated_at__lt=cutoff,
        )
        storage = PostMedia._meta.get_field("file").storage
        package_count = 0
        file_count = 0
        for package in packages.iterator():
            package_count += 1
            names = list(package.storage_names or [])
            file_count += len(names)
            if options["dry_run"]:
                continue
            for name in names:
                try:
                    storage.delete(name)
                except Exception as exc:
                    raise CommandError(f"Storage cleanup failed for package {package.pk}") from exc
            package.storage_names = []
            package.state = PublishPackage.State.FAILED
            package.save(update_fields=["storage_names", "state", "updated_at"])
        mode = "Would clean" if options["dry_run"] else "Cleaned"
        self.stdout.write(f"{mode} {package_count} packages and {file_count} files")
