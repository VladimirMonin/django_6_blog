from django.shortcuts import render
from django.http import HttpResponse


def post_list(request):
    """
    Список постов блога (главная страница).
    
    Временная заглушка для проверки маршрутизации.
    """
    return HttpResponse("<h1>Список постов</h1><p>Здесь будет список всех постов блога.</p>")


def post_detail(request, pk):
    """
    Детальный просмотр поста.
    
    Args:
        pk: Primary key поста
    
    Временная заглушка для проверки маршрутизации.
    """
    return HttpResponse(f"<h1>Пост #{pk}</h1><p>Здесь будет детальный просмотр поста с ID {pk}.</p>")


def about(request):
    """
    Страница "О блоге".
    
    Временная заглушка для проверки маршрутизации и навигации.
    """
    return HttpResponse("<h1>О блоге</h1><p>Информация о блоге на Django 6 + HTMX + Bootstrap 5.</p>")

