"""Canonical URL and structured-data helpers for public blog pages."""

import json
from urllib.parse import urlencode

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.utils.safestring import mark_safe


SCHEMA_CONTEXT = "https://schema.org"
SITE_NAME = "Django 6 Blog"
_JSON_SCRIPT_ESCAPES = {
    ord("<"): "\\u003C",
    ord(">"): "\\u003E",
    ord("&"): "\\u0026",
}


def canonical_url(request):
    """Return this request's absolute, query-free canonical URL."""

    return request.build_absolute_uri(request.path)


def site_entities(request):
    """Return the public WebSite and Person entities shared by all pages."""

    site_url = request.build_absolute_uri(reverse("post_list"))
    author_url = request.build_absolute_uri(reverse("about"))
    author_name = getattr(settings, "SITE_AUTHOR", "Владимир Монин")
    person = {
        "@type": "Person",
        "@id": f"{author_url}#person",
        "name": author_name,
        "url": author_url,
    }
    website = {
        "@type": "WebSite",
        "@id": f"{site_url}#website",
        "name": SITE_NAME,
        "url": site_url,
        "publisher": {"@id": person["@id"]},
    }
    return {"website": website, "person": person}


def _serialize_json_ld(graph, *, document_properties=None):
    """Serialize a JSON-LD graph without allowing user text to close its script."""

    document = {"@context": SCHEMA_CONTEXT, "@graph": graph}
    if document_properties:
        document.update(document_properties)
    serialized = json.dumps(document, cls=DjangoJSONEncoder, indent=2)
    return mark_safe(serialized.translate(_JSON_SCRIPT_ESCAPES))


def _breadcrumb_list(request, items, *, canonical):
    """Build a truthful BreadcrumbList from visible breadcrumb labels and URLs."""

    elements = []
    for position, item in enumerate(items, start=1):
        item_url = item.get("url") or canonical
        elements.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": item["title"],
                "item": request.build_absolute_uri(item_url),
            }
        )
    return {
        "@type": "BreadcrumbList",
        "@id": f"{canonical}#breadcrumb",
        "itemListElement": elements,
    }


def build_home_json_ld(request):
    """Build the structured-data graph for the public home page."""

    entities = site_entities(request)
    return _serialize_json_ld([entities["website"], entities["person"]])


def build_about_json_ld(request):
    """Build the ProfilePage and Person graph for the canonical author page."""

    canonical = canonical_url(request)
    entities = site_entities(request)
    profile_page = {
        "@type": "ProfilePage",
        "@id": f"{canonical}#profile-page",
        "url": canonical,
        "name": "О блоге",
        "isPartOf": {"@id": entities["website"]["@id"]},
        "mainEntity": {"@id": entities["person"]["@id"]},
    }
    return _serialize_json_ld([entities["website"], entities["person"], profile_page])


def build_post_json_ld(request, post, breadcrumbs):
    """Build a safe Article, AudioObject, or VideoObject graph for one post."""

    canonical = canonical_url(request)
    entities = site_entities(request)
    schema_type = {
        post.ContentType.VIDEO: "VideoObject",
        post.ContentType.AUDIO: "AudioObject",
        post.ContentType.PODCAST: "AudioObject",
    }.get(post.content_type, "Article")
    post_node = {
        "@type": schema_type,
        "@id": f"{canonical}#content",
        "url": canonical,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "headline": post.title,
        "description": post.description,
        "datePublished": post.created_at,
        "dateModified": post.updated_at,
        "author": {"@id": entities["person"]["@id"]},
        "publisher": {"@id": entities["person"]["@id"]},
        "isPartOf": {"@id": entities["website"]["@id"]},
    }
    player_media_url = post.player_media_url
    if player_media_url and post.content_type != post.ContentType.ARTICLE:
        post_node["contentUrl"] = player_media_url
    cover = post.cover_media
    if cover:
        post_node["image"] = request.build_absolute_uri(cover.thumbnail_og_url)

    graph = [
        entities["website"],
        entities["person"],
        post_node,
        _breadcrumb_list(request, breadcrumbs, canonical=canonical),
    ]
    # Keep the established top-level URL/image fields available to existing
    # HTML consumers while the graph is the canonical structured-data model.
    document_properties = {"url": canonical}
    if "image" in post_node:
        document_properties["image"] = post_node["image"]
    return _serialize_json_ld(graph, document_properties=document_properties)


def build_series_json_ld(request, series):
    """Build a CollectionPage graph for a public series landing page."""

    canonical = canonical_url(request)
    entities = site_entities(request)
    series_node = {
        "@type": "CollectionPage",
        "@id": f"{canonical}#series",
        "url": canonical,
        "name": series.name,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "isPartOf": {"@id": entities["website"]["@id"]},
    }
    if series.description:
        series_node["description"] = series.description
    breadcrumbs = [
        {"title": "Главная", "url": reverse("post_list")},
        {"title": f"Серия: {series.name}"},
    ]
    return _serialize_json_ld(
        [
            entities["website"],
            entities["person"],
            series_node,
            _breadcrumb_list(request, breadcrumbs, canonical=canonical),
        ]
    )
