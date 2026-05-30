"""Small frontmatter parser for local Markdown imports."""

from __future__ import annotations

import re

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def split_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    """Return simple frontmatter key/value metadata and Markdown body."""

    match = FRONTMATTER_RE.match(markdown_text)
    if not match:
        return {}, markdown_text

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"\'')
        if value and not value.startswith(("{", ">")):
            metadata[key.strip()] = value

    return metadata, markdown_text[match.end():]
