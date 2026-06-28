import hashlib
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import condition
from django.views.generic import DetailView, ListView, TemplateView, View

from .models import Category, Post, Tag
from .session_interactions import SessionInteractionMixin


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

    Returns an md5 of ``post:{pk}:{updated_at.isoformat()}`` so the tag
    changes whenever the post is saved (``updated_at`` is ``auto_now=True``).
    Shares the probe query with ``_post_detail_last_modified``.
    """
    slug = kwargs.get("slug")
    if not slug:
        return None
    row = _post_detail_probe(request, slug)
    if row is None:
        return None
    pk, updated_at = row
    raw = f"post:{pk}:{updated_at.isoformat()}"
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


def _filter_query_string(*, search="", category="", tag=""):
    """Build a stable query string for links that should preserve filters."""
    params = {}
    if search:
        params["search"] = search
    if category:
        params["category"] = category
    if tag:
        params["tag"] = tag
    return urlencode(params)


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
        self.active_category = None
        self.active_tag = None
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        posts = (
            Post.objects.filter(status=Post.Status.PUBLISHED)
            .select_related("category")
            .prefetch_related("tags", "media_files")
        )

        if self.category_slug:
            self.active_category = get_object_or_404(Category, slug=self.category_slug)
            posts = posts.filter(category=self.active_category)

        if self.tag_slug:
            self.active_tag = get_object_or_404(Tag, slug=self.tag_slug)
            posts = posts.filter(tags=self.active_tag)

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
                "filter_query": _filter_query_string(
                    search=self.search,
                    category=self.category_slug,
                    tag=self.tag_slug,
                ),
                "active_category": self.active_category,
                "active_tag": self.active_tag,
                "categories": Category.objects.all(),
                "tags": Tag.objects.all(),
                "tag_map": Tag.objects.annotate(
                    public_post_count=Count(
                        "posts",
                        filter=Q(posts__status=Post.Status.PUBLISHED),
                        distinct=True,
                    )
                ).filter(public_post_count__gt=0),
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
            Post.objects.filter(status=Post.Status.PUBLISHED)
            .select_related("category")
            .prefetch_related("tags", "media_files")
        )

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        return self.register_post_view(post)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "post_is_liked": self.is_post_liked(self.object),
                "is_post_list": False,
                "is_about": False,
            }
        )
        return context


class PostLikeToggleView(SessionInteractionMixin, View):
    """Toggle one anonymous like per session for a published post."""

    def post(self, request, slug):
        post = get_object_or_404(
            Post.objects.filter(status=Post.Status.PUBLISHED),
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
