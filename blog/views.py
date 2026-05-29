from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Post, Tag


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


def post_list(request):
    """
    Список постов блога (главная страница).

    Отображает опубликованные посты с поддержкой:
    - статуса публикации/черновика;
    - категорий и тегов;
    - поиска по заголовку, контенту, категории и тегам;
    - SEO-friendly пагинации обычными ссылками;
    - HTMX-поиска и догрузки карточек без перезагрузки страницы.
    """
    posts = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("category")
        .prefetch_related("tags", "media_files")
    )

    search = request.GET.get("search", "").strip()
    category_slug = request.GET.get("category", "").strip()
    tag_slug = request.GET.get("tag", "").strip()

    active_category = None
    active_tag = None

    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug)
        posts = posts.filter(category=active_category)

    if tag_slug:
        active_tag = get_object_or_404(Tag, slug=tag_slug)
        posts = posts.filter(tags=active_tag)

    if search:
        search_filter = (
            Q(title__icontains=search)
            | Q(content__icontains=search)
            | Q(category__name__icontains=search)
            | Q(tags__name__icontains=search)
        )
        if _needs_python_casefold(search):
            needle = search.casefold()
            casefold_matches = [
                post.pk for post in posts if _post_matches_casefold(post, needle)
            ]
            posts = posts.filter(search_filter | Q(pk__in=casefold_matches)).distinct()
        else:
            posts = posts.filter(search_filter).distinct()

    paginator = Paginator(posts, 5)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    load_more = request.GET.get("load_more") == "true"
    filter_query = _filter_query_string(
        search=search,
        category=category_slug,
        tag=tag_slug,
    )

    context = {
        "posts": page_obj,
        "page_obj": page_obj,
        "search_query": search,
        "category_slug": category_slug,
        "tag_slug": tag_slug,
        "filter_query": filter_query,
        "active_category": active_category,
        "active_tag": active_tag,
        "categories": Category.objects.all(),
        "tags": Tag.objects.all(),
        "is_post_list": True,
        "is_about": False,
    }

    if request.htmx and load_more:
        return render(request, "blog/_post_cards_only.html", context)

    if request.htmx:
        return render(request, "blog/_post_list_partial.html", context)

    return render(request, "blog/post_list.html", context)


def post_detail(request, pk):
    """
    Детальный просмотр опубликованного поста.
    """
    post = get_object_or_404(
        Post.objects.select_related("category").prefetch_related("tags", "media_files"),
        pk=pk,
        status=Post.Status.PUBLISHED,
    )
    return render(
        request,
        "blog/post_detail.html",
        {
            "post": post,
            "is_post_list": False,
            "is_about": False,
        },
    )


def about(request):
    """
    Страница "О блоге".
    """
    return render(
        request,
        "blog/about.html",
        {
            "is_post_list": False,
            "is_about": True,
        },
    )
