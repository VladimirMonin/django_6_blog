"""Import a local Obsidian Markdown note with media assets into the blog."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify as django_slugify
from transliterate import slugify as transliterate_slugify

from blog.models import Post
from blog.services.obsidian_importer import import_obsidian_note_to_post, split_frontmatter


class Command(BaseCommand):
    help = "Import a local Obsidian note and its copied assets into a blog post."

    def add_arguments(self, parser):
        parser.add_argument("note", type=Path, help="Path to the copied Obsidian .md note")
        parser.add_argument(
            "--assets-dir",
            type=Path,
            default=None,
            help="Directory with copied assets. Defaults to the note directory.",
        )
        parser.add_argument(
            "--slug",
            default=None,
            help="Post slug to use. Defaults to a slug generated from frontmatter title or filename.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete an existing post with the same slug before import.",
        )

    def handle(self, *args, **options):
        note_path: Path = options["note"].expanduser().resolve()
        assets_dir: Path = (options["assets_dir"] or note_path.parent).expanduser().resolve()

        if not note_path.exists() or not note_path.is_file():
            raise CommandError(f"Note file not found: {note_path}")
        if note_path.suffix.lower() != ".md":
            raise CommandError(f"Expected a Markdown file: {note_path}")
        if not assets_dir.exists() or not assets_dir.is_dir():
            raise CommandError(f"Assets directory not found: {assets_dir}")

        metadata, _body = split_frontmatter(note_path.read_text(encoding="utf-8"))
        title = metadata.get("title") or note_path.stem
        slug = options["slug"] or transliterate_slugify(title) or django_slugify(title)
        if not slug:
            raise CommandError("Could not generate a post slug; pass --slug explicitly.")

        existing = Post.objects.filter(slug=slug)
        if existing.exists() and not options["replace"]:
            raise CommandError(
                f"Post with slug '{slug}' already exists. Re-run with --replace to overwrite it."
            )
        if options["replace"]:
            deleted_count, _deleted = existing.delete()
            if deleted_count:
                self.stdout.write(f"Deleted existing post with slug '{slug}'.")

        post = import_obsidian_note_to_post(note_path, assets_dir=assets_dir, slug=slug)

        media_counts = {}
        for media in post.media_files.all():
            media_counts[media.media_type] = media_counts.get(media.media_type, 0) + 1

        self.stdout.write(
            self.style.SUCCESS(
                "Imported Obsidian note: "
                f"id={post.pk}, slug={post.slug}, title={post.title!r}, "
                f"media={post.media_files.count()}, media_by_type={media_counts}"
            )
        )
