from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from blog.models import Post
from blog.services import convert_markdown_to_html


class Command(BaseCommand):
    help = "Rebuild persisted post HTML using the active public media URL policy."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--slug", help="Rebuild exactly one existing post by slug.")

    def handle(self, *args, **options):
        changed = skipped = errors = 0
        posts = Post.objects.all()
        slug = options["slug"]
        if slug:
            posts = posts.filter(slug=slug)
            if not posts.exists():
                raise CommandError(f"No post found for slug: {slug}")

        for post in posts.iterator(chunk_size=max(1, options["batch_size"])):
            try:
                rendered = convert_markdown_to_html(post.content, post=post)
                if rendered == post.content_html:
                    skipped += 1
                    continue
                changed += 1
                if not options["dry_run"]:
                    Post.objects.filter(pk=post.pk).update(
                        content_html=rendered,
                        updated_at=timezone.now(),
                    )
            except Exception:
                errors += 1
        self.stdout.write(
            "candidates="
            f"{changed + skipped + errors} changed={changed} skipped={skipped} "
            f"errors={errors} dry_run={options['dry_run']}"
        )
