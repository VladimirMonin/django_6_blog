"""Management command to dump blog data as a backup.

Usage:
    uv run python manage.py backup
    uv run python manage.py backup --output backup.json

Default: print JSON of all posts (including soft-deleted) to stdout.
With --output FILE: write JSON to the given file path.
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import serialize

from blog.models import Post


class Command(BaseCommand):
    help = "Dump all posts and list media files as a JSON backup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            dest="output",
            default=None,
            help="Write backup JSON to the given file path instead of stdout.",
        )

    def handle(self, *args, **options):
        output_file = options.get("output")

        # Serialize all posts (including soft-deleted) via Django's serializer
        posts_json = serialize(
            "json",
            Post.objects.all().order_by("pk"),
            use_natural_foreign_keys=True,
        )

        # Collect media file list
        media_root = settings.MEDIA_ROOT
        media_files = []
        if media_root and media_root.exists():
            for entry in sorted(media_root.rglob("*")):
                if entry.is_file():
                    media_files.append(str(entry.relative_to(media_root)))

        backup_data = {
            "posts": json.loads(posts_json),
            "media_files": media_files,
            "post_count": Post.objects.count(),
        }

        result = json.dumps(backup_data, ensure_ascii=False, indent=2)

        if output_file:
            from pathlib import Path

            path = Path(output_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result, encoding="utf-8")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backup written to {path} ({len(backup_data['posts'])} posts)"
                )
            )
        else:
            self.stdout.write(result)