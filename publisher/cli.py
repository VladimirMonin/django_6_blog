#!/usr/bin/env python3
"""Blog publisher CLI — post Markdown/Obsidian notes via the blog API.

Usage:
    python -m publisher.cli publish note.md [--url URL] [--key TOKEN] [options]
    python -m publisher.cli publish note.md --dry-run

Configuration:
    --url    Blog base URL (or BLOG_API_URL env var)
    --key    API key token  (or BLOG_API_KEY env var)

Examples:
    # Publish a note with defaults (published, URL/key from env)
    python -m publisher.cli publish path/to/note.md

    # Dry run — print payload without sending
    python -m publisher.cli publish note.md --dry-run

    # Publish as draft
    python -m publisher.cli publish note.md --status draft

    # Replace existing post with same slug
    python -m publisher.cli publish note.md --replace

    # Override frontmatter
    python -m publisher.cli publish note.md --title "Custom Title" --content-type video
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .client import ApiError, publish_post
from .parser import parse_markdown_file


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="publisher",
        description="Post Markdown/Obsidian notes to a blog via API.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pub = subparsers.add_parser(
        "publish",
        help="Parse and publish a Markdown note via the blog API.",
    )
    pub.add_argument(
        "file",
        type=Path,
        help="Path to the Markdown/Obsidian note file.",
    )
    pub.add_argument(
        "--url",
        default=os.environ.get("BLOG_API_URL", ""),
        help="Blog base URL (or BLOG_API_URL env var). Example: http://127.0.0.1:8036",
    )
    pub.add_argument(
        "--key",
        default=os.environ.get("BLOG_API_KEY", ""),
        help="API key token (or BLOG_API_KEY env var).",
    )
    pub.add_argument("--title", default=None, help="Override post title.")
    pub.add_argument("--description", default=None, help="Override post description.")
    pub.add_argument(
        "--content-type",
        default=None,
        choices=["article", "video", "audio", "podcast"],
        help="Override content type (default: from frontmatter or article).",
    )
    pub.add_argument("--media-url", default=None, help="Override media URL.")
    pub.add_argument(
        "--status",
        default=None,
        choices=["published", "draft"],
        help="Override post status (default: from frontmatter or published).",
    )
    pub.add_argument("--slug", default=None, help="Override post slug.")
    pub.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing post with the same slug.",
    )
    pub.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print the payload without sending to API.",
    )

    return parser


def cmd_publish(args: argparse.Namespace) -> int:
    """Execute the publish command."""
    if not args.file.exists():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 1

    try:
        payload = parse_markdown_file(
            args.file,
            title=args.title,
            description=args.description,
            content_type=args.content_type,
            media_url=args.media_url,
            status=args.status,
            slug=args.slug,
        )
    except ValueError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if not args.url:
        print("Error: --url is required (or set BLOG_API_URL env var).", file=sys.stderr)
        return 1
    if not args.key:
        print("Error: --key is required (or set BLOG_API_KEY env var).", file=sys.stderr)
        return 1

    try:
        result = publish_post(
            url=args.url,
            api_key=args.key,
            payload=payload,
            replace=args.replace,
        )
    except ApiError as exc:
        print(f"API error ({exc.status_code}): {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        return 1

    print(f"✓ Published: {result.get('title', '?')}")
    print(f"  Slug: {result.get('slug', '?')}")
    print(f"  Status: {result.get('status', '?')}")
    print(f"  URL: {args.url.rstrip('/')}{result.get('url', '')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "publish":
        return cmd_publish(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())