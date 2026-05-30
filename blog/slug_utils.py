"""Slug generation helpers for Cyrillic-heavy blog content."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, cast

from django.db import models
from django.db.models import QuerySet
from django.utils.text import slugify as django_slugify

CYRILLIC_TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
        "А": "A",
        "Б": "B",
        "В": "V",
        "Г": "G",
        "Д": "D",
        "Е": "E",
        "Ё": "Yo",
        "Ж": "Zh",
        "З": "Z",
        "И": "I",
        "Й": "Y",
        "К": "K",
        "Л": "L",
        "М": "M",
        "Н": "N",
        "О": "O",
        "П": "P",
        "Р": "R",
        "С": "S",
        "Т": "T",
        "У": "U",
        "Ф": "F",
        "Х": "H",
        "Ц": "Ts",
        "Ч": "Ch",
        "Ш": "Sh",
        "Щ": "Shch",
        "Ъ": "",
        "Ы": "Y",
        "Ь": "",
        "Э": "E",
        "Ю": "Yu",
        "Я": "Ya",
    }
)


def transliterate_cyrillic(value: str) -> str:
    """Return a readable ASCII transliteration for Russian/Cyrillic text."""

    return value.translate(CYRILLIC_TRANSLITERATION)


def build_slug(value: str, fallback: str = "item", max_length: int | None = None) -> str:
    """Build a stable ASCII slug from mixed Cyrillic/Latin text."""

    transliterated = transliterate_cyrillic(value or "")
    normalized = unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"[’'`]+", "", normalized)
    slug = django_slugify(normalized) or django_slugify(value or "") or fallback
    if max_length:
        slug = slug[:max_length].rstrip("-") or fallback[:max_length]
    return slug


def build_unique_slug(
    instance: models.Model,
    value: str,
    *,
    slug_field: str = "slug",
    fallback: str = "item",
    queryset: models.QuerySet[Any] | None = None,
) -> str:
    """Build a unique slug for a model instance by appending numeric suffixes."""

    field = instance._meta.get_field(slug_field)
    max_length = getattr(field, "max_length", None)
    base_slug = build_slug(value, fallback=fallback, max_length=max_length)
    model_queryset = cast(QuerySet[Any], queryset if queryset is not None else instance.__class__._default_manager.all())
    if instance.pk:
        model_queryset = model_queryset.exclude(pk=instance.pk)

    candidate = base_slug
    suffix = 2
    while model_queryset.filter(**{slug_field: candidate}).exists():
        suffix_text = f"-{suffix}"
        if max_length:
            trimmed_base = base_slug[: max_length - len(suffix_text)].rstrip("-") or fallback[: max_length - len(suffix_text)]
        else:
            trimmed_base = base_slug
        candidate = f"{trimmed_base}{suffix_text}"
        suffix += 1
    return candidate
