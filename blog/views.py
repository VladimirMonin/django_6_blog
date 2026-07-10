import hashlib
import json
import re

from django.conf import settings
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.decorators.http import condition
from django.views.generic import DetailView, ListView, TemplateView, View

from .models import Category, Post, Series, Tag
from .session_interactions import SessionInteractionMixin


POST_DETAIL_RENDER_VERSION = "social-image-v7"

_JSON_SCRIPT_ESCAPES = {
    ord("<"): "\\u003C",
    ord(">"): "\\u003E",
    ord("&"): "\\u0026",
}


def _build_post_json_ld(request, post):
    """Serialize post structured data as HTML-safe, valid JSON."""
    schema_type = {
        Post.ContentType.VIDEO: "VideoObject",
        Post.ContentType.AUDIO: "AudioObject",
        Post.ContentType.PODCAST: "AudioObject",
    }.get(post.content_type, "Article")
    data = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "headline": post.title,
        "description": post.description,
        "url": request.build_absolute_uri(),
        "datePublished": post.created_at,
        "dateModified": post.updated_at,
        "author": {
            "@type": "Person",
            "name": getattr(settings, "SITE_AUTHOR", "Владимир Монин"),
        },
    }
    player_media_url = post.player_media_url
    if player_media_url and post.content_type != Post.ContentType.ARTICLE:
        data["contentUrl"] = player_media_url
    cover = post.cover_media
    if cover:
        data["image"] = request.build_absolute_uri(cover.thumbnail_og_url)

    serialized = json.dumps(data, cls=DjangoJSONEncoder, indent=2)
    return mark_safe(serialized.translate(_JSON_SCRIPT_ESCAPES))


def _post_detail_probe(request, slug):
    """Single lightweight DB probe shared by etag/last-modified funcs.

    Returns ``(pk, updated_at)`` for the published post with ``slug``, cached
    on the request object so the ``condition`` decorator does not run two
    separate ``values_list`` queries on every fresh request.
    """
    cache_attr = f"_post_detail_probe_{slug}"
    if not hasattr(request, cache_attr):
        row = Post.objects.filter(
            slug=slug,
            status=Post.Status.PUBLISHED,
            deleted_at__isnull=True,
        ).values_list("pk", "updated_at").first()
        setattr(request, cache_attr, row)
    return getattr(request, cache_attr)


def _post_detail_last_modified(request, *args, **kwargs):
    """Last-Modified probe for PostDetailView conditional rendering.

    Runs BEFORE the view body; shares a single ``values_list`` query with
    ``_post_detail_etag`` via ``_post_detail_probe``.
    """
    slug = kwargs.get("slug")
    if not slug:
        return None
    row = _post_detail_probe(request, slug)
    return row[1] if row else None


def _post_detail_etag(request, *args, **kwargs):
    """ETag probe for PostDetailView conditional rendering.

    Returns an md5 of post state plus the detail-render version. The render
    version intentionally invalidates browser HTML caches when templates or
    TOC/header behaviour changes without touching the post row.
    """
    slug = kwargs.get("slug")
    if not slug:
        return None
    row = _post_detail_probe(request, slug)
    if row is None:
        return None
    pk, updated_at = row
    raw = f"post:{pk}:{updated_at.isoformat()}:{POST_DETAIL_RENDER_VERSION}"
    return hashlib.md5(raw.encode()).hexdigest()


def _needs_python_casefold(value):
    """SQLite icontains is ASCII-centric; Cyrillic search needs Python casefold."""
    return any(ord(char) > 127 for char in value)


def _post_matches_casefold(post, needle):
    """Return True if a post matches the search text with Unicode-aware casefold."""
    chunks = [post.title, post.content]
    if post.category:
        chunks.append(post.category.name)
    chunks.extend(tag.name for tag in post.tags.all())
    return needle in " ".join(filter(None, chunks)).casefold()


def _build_body_html_and_toc(html_content):
    """Return body HTML with heading ids plus a TOC for h2/h3 headings.

    TOC links and rendered headings must be produced in the same pass. Use
    deterministic ASCII ids instead of text-derived Cyrillic ids so native
    anchors, copied links and JS scrolling behave the same across browsers.
    """
    heading_re = re.compile(
        r"<h([23])(?P<attrs>[^>]*)>(?P<body>.*?)</h\1>",
        re.IGNORECASE | re.DOTALL,
    )
    id_re = re.compile(r'\sid=["\']([^"\']+)["\']', re.IGNORECASE)
    entries = []
    used_ids = set()

    def unique_id(index):
        stem = f"post-section-{index + 1}"
        candidate = stem
        counter = 2
        while candidate in used_ids:
            candidate = f"{stem}-{counter}"
            counter += 1
        used_ids.add(candidate)
        return candidate

    def replace_heading(match):
        level = int(match.group(1))
        attrs = match.group("attrs") or ""
        body = match.group("body") or ""
        text = re.sub(r"<[^>]+>", "", body).strip()
        existing_id = id_re.search(attrs)
        entry_id = unique_id(len(entries))
        if existing_id:
            attrs_with_id = id_re.sub(f' id="{entry_id}"', attrs, count=1)
        else:
            attrs_with_id = f'{attrs} id="{entry_id}"'
        entries.append({"level": level, "text": text, "id": entry_id})
        return f"<h{level}{attrs_with_id}>{body}</h{level}>"

    html_with_ids = heading_re.sub(replace_heading, html_content or "")
    toc = entries if len(entries) >= 3 else []
    return html_with_ids, toc


def _get_related_posts(post, limit=3):
    """Return up to ``limit`` published, non-deleted posts related to ``post``.

    Related = same category OR shared tags, excluding the current post.
    """
    related = (
        Post.objects.filter(
            status=Post.Status.PUBLISHED,
            deleted_at__isnull=True,
        )
        .exclude(pk=post.pk)
        .select_related("category")
        .prefetch_related("tags")
    )
    category_q = Q(category=post.category) if post.category_id else Q()
    tag_q = Q(tags__in=post.tags.all()) if post.tags.exists() else Q()
    combined = category_q | tag_q
    if not combined:
        return []
    # Use distinct to avoid duplicates from tag join; annotate for stable order
    return list(
        related.filter(combined)
        .distinct()
        .order_by("-created_at")[:limit]
    )


class PostListView(ListView):
    """Public post list with filters, SEO pagination, and HTMX partials."""

    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 5

    def dispatch(self, request, *args, **kwargs):
        self.search = request.GET.get("search", "").strip()
        self.category_slug = request.GET.get("category", "").strip()
        self.tag_slug = request.GET.get("tag", "").strip()
        self.content_type_filter = request.GET.get("type", "").strip()
        self.active_category = None
        self.active_tag = None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        posts = (
            Post.objects.filter(status=Post.Status.PUBLISHED, deleted_at__isnull=True)
            .select_related("category")
            .prefetch_related("tags", "media_files")
        )

        if self.category_slug:
            self.active_category = get_object_or_404(Category, slug=self.category_slug)
            posts = posts.filter(category=self.active_category)

        if self.tag_slug:
            self.active_tag = get_object_or_404(Tag, slug=self.tag_slug)
            posts = posts.filter(tags=self.active_tag)

        if self.content_type_filter:
            valid_types = dict(Post.ContentType.choices).keys()
            if self.content_type_filter in valid_types:
                posts = posts.filter(content_type=self.content_type_filter)

        if self.search:
            search_filter = (
                Q(title__icontains=self.search)
                | Q(content__icontains=self.search)
                | Q(category__name__icontains=self.search)
                | Q(tags__name__icontains=self.search)
            )
            if _needs_python_casefold(self.search):
                needle = self.search.casefold()
                casefold_matches = [
                    post.pk for post in posts if _post_matches_casefold(post, needle)
                ]
                posts = posts.filter(search_filter | Q(pk__in=casefold_matches)).distinct()
            else:
                posts = posts.filter(search_filter).distinct()

        return posts

    def paginate_queryset(self, queryset, page_size):
        paginator = Paginator(queryset, page_size)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        return paginator, page_obj, page_obj.object_list, page_obj.has_other_pages()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "search_query": self.search,
                "category_slug": self.category_slug,
                "tag_slug": self.tag_slug,
                "content_type_filter": self.content_type_filter,
                # One QueryDict contract drives every SSR/HTMX navigation URL.
                # Templates override the parameter they own and drop stale
                # pagination state via Django's built-in ``querystring`` tag.
                "filter_params": self.request.GET,
                "active_category": self.active_category,
                "active_tag": self.active_tag,
                "categories": Category.objects.all(),
                "tags": Tag.objects.all(),
                "tag_map": Tag.objects.annotate(
                    public_post_count=Count(
                        "posts",
                        filter=Q(
                            posts__status=Post.Status.PUBLISHED,
                            posts__deleted_at__isnull=True,
                        ),
                        distinct=True,
                    )
                ).filter(public_post_count__gt=0),
                "content_type_choices": Post.ContentType.choices,
                "is_post_list": True,
                "is_about": False,
            }
        )
        return context

    def get_template_names(self):
        load_more = self.request.GET.get("load_more") == "true"
        if self.request.htmx and load_more:
            return ["blog/_post_cards_only.html"]
        if self.request.htmx:
            return ["blog/_post_list_partial.html"]
        return [self.template_name]


@method_decorator(
    condition(
        last_modified_func=_post_detail_last_modified,
        etag_func=_post_detail_etag,
    ),
    name="dispatch",
)
class PostDetailView(SessionInteractionMixin, DetailView):
    """Detail page for a published post with session-based view counting.

    Conditional rendering (ETag / Last-Modified) is applied via the
    ``condition`` decorator on ``dispatch``. When the client sends a matching
    ``If-None-Match`` or ``If-Modified-Since`` header, Django short-circuits
    the response to 304 *before* the view body runs — which means
    ``register_post_view`` is skipped on cached re-requests. This is the
    intended behaviour: view counting is a first-visit signal, while 304s
    serve browser-cache revalidation.
    """

    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # prefetch_related("media_files") is correct for the detail view:
        # ``Post.cover_media`` and ``Post.primary_media`` iterate the
        # prefetched cache (_prefetched_objects_cache) to pick the cover
        # image and the primary audio/video player, avoiding extra queries.
        # A typical post has 1-3 media items, so fetching all of them in a
        # single prefetch is cheaper and simpler than two targeted filtered
        # prefetches. No optimization is needed here.
        return (
            Post.objects.filter(status=Post.Status.PUBLISHED, deleted_at__isnull=True)
            .select_related("category")
            .prefetch_related("tags", "media_files")
        )

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        return self.register_post_view(post)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cover = self.object.cover_media
        context.update(
            {
                "post_is_liked": self.is_post_liked(self.object),
                "post_json_ld": _build_post_json_ld(self.request, self.object),
                "social_image_url": (
                    self.request.build_absolute_uri(cover.thumbnail_og_url)
                    if cover
                    else ""
                ),
                "is_post_list": False,
                "is_about": False,
            }
        )
        # Series navigation: prev/next posts in the same series
        post = self.object
        if post.series:
            series_posts = list(
                post.series.posts.filter(
                    status=Post.Status.PUBLISHED,
                    deleted_at__isnull=True,
                )
                .order_by("series_order", "created_at")
                .values_list("pk", "slug", "title")
            )
            current_index = next(
                (i for i, (pk, _, _) in enumerate(series_posts) if pk == post.pk),
                None,
            )
            if current_index is not None:
                if current_index > 0:
                    _, prev_slug, prev_title = series_posts[current_index - 1]
                    context["series_prev"] = {"slug": prev_slug, "title": prev_title}
                if current_index < len(series_posts) - 1:
                    _, next_slug, next_title = series_posts[current_index + 1]
                    context["series_next"] = {"slug": next_slug, "title": next_title}
                context["series_total"] = len(series_posts)
                context["series_position"] = current_index + 1

        # Related posts (same category or shared tags, excluding current)
        context["related_posts"] = _get_related_posts(post, limit=3)

        # Breadcrumbs: Home > Category (if any) > Title
        breadcrumbs = [{"url": "/", "title": "Главная"}]
        if post.category:
            breadcrumbs.append(
                {
                    "url": f"/?category={post.category.slug}",
                    "title": post.category.name,
                }
            )
        breadcrumbs.append({"title": post.title})
        context["breadcrumbs"] = breadcrumbs

        # Body HTML and table of contents are built together so TOC anchors
        # always point to actual heading ids in the rendered article.
        body_html, toc = _build_body_html_and_toc(post.body_content_html)
        context["body_html"] = body_html
        context["toc"] = toc

        return context


class PostLikeToggleView(SessionInteractionMixin, View):
    """Toggle one anonymous like per session for a published post."""

    def post(self, request, slug):
        post = get_object_or_404(
            Post.objects.filter(
                status=Post.Status.PUBLISHED,
                deleted_at__isnull=True,
            ),
            slug=slug,
        )
        post_is_liked = self.toggle_post_like(post)
        post.refresh_from_db(fields=["like_count", "view_count"])
        context = {"post": post, "post_is_liked": post_is_liked}
        if request.htmx:
            return render(request, "blog/_post_reactions.html", context)
        return redirect(post.get_absolute_url())


class AboutView(TemplateView):
    """Static about page."""

    template_name = "blog/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"is_post_list": False, "is_about": True})
        return context


class SeriesDetailView(DetailView):
    """Landing page for a Series — lists all published posts in order."""

    model = Series
    template_name = "blog/series_detail.html"
    context_object_name = "series"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = (
            self.object.posts.filter(
                status=Post.Status.PUBLISHED,
                deleted_at__isnull=True,
            )
            .select_related("category")
            .prefetch_related("tags")
            .order_by("series_order", "created_at")
        )
        context["series_posts"] = posts
        context["is_post_list"] = False
        context["is_about"] = False
        return context


def robots_txt(request):
    """Serve robots.txt with sitemap reference."""

    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /api/",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
