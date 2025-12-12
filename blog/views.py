from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Post


def post_list(request):
    """
    Список постов блога (главная страница).
    
    Отображает все опубликованные посты с поддержкой:
    - Пагинации (5 постов на страницу)
    - Поиска по заголовку и контенту
    - HTMX для динамической загрузки
    - Режим "Загрузить еще" (load_more)
    """
    posts = Post.objects.filter(is_published=True)
    
    # Поиск
    search = request.GET.get('search', '').strip()
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(posts, 5)  # 5 постов на страницу
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Режим "Загрузить еще" (только карточки без пагинатора)
    load_more = request.GET.get('load_more') == 'true'
    
    context = {
        'posts': page_obj,
        'page_obj': page_obj,
        'search_query': search,
        'is_post_list': True,
        'is_about': False,
    }
    
    # HTMX запрос с load_more - возвращаем только карточки
    if request.htmx and load_more:
        return render(request, 'blog/_post_cards_only.html', context)
    
    # HTMX запрос обычный - возвращаем карточки + пагинатор
    if request.htmx:
        return render(request, 'blog/_post_list_partial.html', context)
    
    # Обычный запрос - полная страница
    return render(request, 'blog/post_list.html', context)


def post_detail(request, pk):
    """
    Детальный просмотр поста.
    
    Args:
        pk: Primary key поста
        
    Returns:
        Детальную страницу поста или 404 если пост не найден.
    """
    post = get_object_or_404(Post, pk=pk, is_published=True)
    return render(request, 'blog/post_detail.html', {
        'post': post,
        'is_post_list': False,
        'is_about': False,
    })


def about(request):
    """
    Страница "О блоге".
    
    Статическая страница с информацией о проекте.
    """
    return render(request, 'blog/about.html', {
        'is_post_list': False,
        'is_about': True,
    })

