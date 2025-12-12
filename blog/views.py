from django.shortcuts import render, get_object_or_404
from .models import Post


def post_list(request):
    """
    Список постов блога (главная страница).
    
    Отображает все опубликованные посты, отсортированные по дате создания.
    """
    posts = Post.objects.filter(is_published=True)
    return render(request, 'blog/post_list.html', {
        'posts': posts,
        'is_post_list': True,
        'is_about': False,
    })


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

