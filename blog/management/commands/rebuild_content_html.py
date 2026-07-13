from django.core.management.base import BaseCommand
from blog.models import Post
from blog.services import convert_markdown_to_html

class Command(BaseCommand):
    help = "Rebuild persisted post HTML using the active storage URL policy."
    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)
    def handle(self, *args, **options):
        changed = skipped = errors = 0
        for post in Post.objects.iterator(chunk_size=max(1, options["batch_size"])):
            try:
                rendered = convert_markdown_to_html(post.content, post=post)
                if rendered == post.content_html: skipped += 1; continue
                changed += 1
                if not options["dry_run"]:
                    Post.objects.filter(pk=post.pk).update(content_html=rendered)
            except Exception: errors += 1
        self.stdout.write(f"candidates={changed+skipped+errors} changed={changed} skipped={skipped} errors={errors} dry_run={options['dry_run']}")
