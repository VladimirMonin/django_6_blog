"""Parse Markdown timecode fences into normalized seek targets."""

from __future__ import annotations

import re
from typing import Any

TIMECODE_FENCE_RE = re.compile(
    r"(?ms)^```timecodes\s*\n(?P<body>.*?)\n```\s*$"
)
TIMECODE_LINE_RE = re.compile(
    r"^\s*(?P<time>\d{1,2}:\d{2}(?::\d{2})?)\s*(?:[-–—|:]\s*)?(?P<label>.+?)\s*$"
)


class TimecodeParseError(ValueError):
    """Raised when a timecode block contains malformed lines in strict mode."""



def parse_timecodes(raw_text: str, *, strict: bool = False) -> list[dict[str, Any]]:
    """Return normalized timecode entries from a multiline text block.

    Supported input lines:
    - ``00:00 Intro``
    - ``01:23 — Main section``
    - ``1:02:03 | Questions``

    By default invalid lines are ignored for backwards-compatible draft parsing.
    In strict mode every non-empty line must match the format and contain a
    valid MM:SS or H:MM:SS value. CLI/media imports use strict mode.
    """

    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate((raw_text or "").splitlines(), start=1):
        if not line.strip():
            continue
        match = TIMECODE_LINE_RE.match(line)
        if not match:
            if strict:
                raise TimecodeParseError(
                    f"Invalid timecode on line {line_number}: {line.strip()!r}. "
                    "Expected 'MM:SS Label' or 'H:MM:SS Label'."
                )
            continue
        time_text = match.group("time")
        label = match.group("label").strip()
        if not label:
            if strict:
                raise TimecodeParseError(
                    f"Invalid timecode on line {line_number}: label is required."
                )
            continue
        try:
            seconds = time_to_seconds(time_text)
        except ValueError as exc:
            if strict:
                raise TimecodeParseError(
                    f"Invalid timecode on line {line_number}: {time_text!r}. {exc}"
                ) from exc
            continue
        entries.append(
            {
                "time": time_text,
                "seconds": seconds,
                "label": label,
            }
        )
    return entries


def extract_timecode_blocks(
    markdown_text: str, *, strict: bool = False
) -> tuple[str, list[dict[str, Any]]]:
    """Remove ```timecodes fences from Markdown and return parsed entries."""

    entries: list[dict[str, Any]] = []

    def replace(match: re.Match[str]) -> str:
        entries.extend(parse_timecodes(match.group("body"), strict=strict))
        return ""

    cleaned_markdown = TIMECODE_FENCE_RE.sub(replace, markdown_text or "")
    cleaned_markdown = re.sub(r"\n{3,}", "\n\n", cleaned_markdown).strip()
    return cleaned_markdown, entries


def time_to_seconds(time_text: str) -> int:
    """Convert MM:SS or H:MM:SS text into seconds."""

    parts = [int(part) for part in time_text.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        if seconds >= 60:
            raise ValueError("seconds must be between 00 and 59")
        return minutes * 60 + seconds
    hours, minutes, seconds = parts
    if minutes >= 60:
        raise ValueError("minutes must be between 00 and 59")
    if seconds >= 60:
        raise ValueError("seconds must be between 00 and 59")
    return hours * 3600 + minutes * 60 + seconds
