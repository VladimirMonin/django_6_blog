"""Import a local Obsidian Markdown note with media assets into the blog."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from blog.content_import import collect_broken_local_links, collect_local_media_references
from blog.models import Post
from blog.content_import.obsidian import title_from_leading_h1
from blog.services.obsidian_importer import import_obsidian_note_to_post, split_frontmatter
from blog.slug_utils import build_slug


class Command(BaseCommand):
    help = "Import a local Obsidian/Markdown note and its copied assets into a blog post."

    def add_arguments(self, parser):
        parser.add_argument("note", type=Path, help="Path to the copied Markdown note")
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
            "--title",
            default=None,
            help="Override the post title instead of using frontmatter title or filename.",
        )
        parser.add_argument(
            "--description",
            default=None,
            help="Override the post description instead of using frontmatter description.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete an existing post with the same slug before import.",
        )
        parser.add_argument(
            "--check-links",
            action="store_true",
            dest="check_links",
            help="Validate local Markdown/Obsidian media links and exit without creating a post.",
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

        raw_markdown = note_path.read_text(encoding="utf-8")
        metadata, markdown_body = split_frontmatter(raw_markdown)
        title = options["title"] or metadata.get("title") or title_from_leading_h1(markdown_body) or note_path.stem
        slug = options["slug"] or build_slug(title, fallback="post")
        if not slug:
            raise CommandError("Could not generate a post slug; pass --slug explicitly.")

        link_report = collect_local_media_references(markdown_body, assets_dir)
        broken_links = collect_broken_local_links(markdown_body, assets_dir)
        if broken_links:
            missing = ", ".join(broken_links)
            raise CommandError(f"Broken local links: {missing}")

        if options["check_links"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Local links are valid: "
                    f"found={len(link_report.found)}, missing=0"
                )
            )
            return

        existing = Post.objects.filter(slug=slug)
        if existing.exists() and not options["replace"]:
            raise CommandError(
                f"Post with slug '{slug}' already exists. Re-run with --replace to overwrite it."
            )
        if options["replace"]:
            deleted_count, _deleted = existing.delete()
            if deleted_count:
                self.stdout.write(f"Deleted existing post with slug '{slug}'.")

        try:
            post = import_obsidian_note_to_post(
                note_path,
                assets_dir=assets_dir,
                slug=slug,
                title=options["title"],
                description=options["description"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        media_counts = {}
        for media in post.media_files.all():
            media_counts[media.media_type] = media_counts.get(media.media_type, 0) + 1

        self.stdout.write(
            self.style.SUCCESS(
                "Imported Obsidian note: "
                f"url={post.get_absolute_url()}, slug={post.slug}, title={post.title!r}, "
                f"description={post.description!r}, "
                f"media={post.media_files.count()}, media_by_type={media_counts}"
            )
        )
