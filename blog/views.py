from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView, View

from .models import Category, Post, Tag
from .session_interactions import SessionInteractionMixin


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


class PostDetailView(SessionInteractionMixin, DetailView):
    """Detail page for a published post with session-based view counting."""

    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"
    slug_url_kwarg = "slug"

    def get_queryset(self):
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
