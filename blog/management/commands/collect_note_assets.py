"""Collect all local media referenced by a Markdown/Obsidian note."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from blog.content_import.media_bundle import collect_note_media_bundle


class Command(BaseCommand):
    help = (
        "Copy all local media referenced by a Markdown/Obsidian note into one "
        "flat assets directory, optionally copying the note itself."
    )

    def add_arguments(self, parser):
        parser.add_argument("note", type=Path, help="Path to the source Markdown/Obsidian note")
        parser.add_argument("output_dir", type=Path, help="Destination assets directory")
        parser.add_argument(
            "--vault-root",
            type=Path,
            default=None,
            help="Obsidian vault root for resolving vault-relative wikilinks such as 999_files/img.webp.",
        )
        parser.add_argument(
            "--no-copy-note",
            action="store_false",
            dest="copy_note",
            help="Copy only media files, not the Markdown note.",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove the destination directory before copying.",
        )
        parser.add_argument(
            "--title",
            default=None,
            help="Add or replace the copied note frontmatter title.",
        )
        parser.add_argument(
            "--description",
            default=None,
            help="Add or replace the copied note frontmatter description for blog cards.",
        )

    def handle(self, *args, **options):
        try:
            result = collect_note_media_bundle(
                options["note"],
                options["output_dir"],
                vault_root=options["vault_root"],
                copy_note=options["copy_note"],
                clean=options["clean"],
                title=options["title"],
                description=options["description"],
            )
        except (FileNotFoundError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        for item in result.copied:
            self.stdout.write(f"copied: {item.source_name} -> {item.copied_path.name}")

        if result.note_path is not None:
            self.stdout.write(f"note: {result.note_path}")

        summary = (
            f"assets_dir={result.assets_dir}, assets_copied={len(result.copied)}, "
            f"missing={len(result.missing)}"
        )
        if result.missing:
            self.stderr.write("missing: " + ", ".join(result.missing))
            raise CommandError("Some local media references were not found: " + summary)

        self.stdout.write(self.style.SUCCESS("Collected note assets: " + summary))
