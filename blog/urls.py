"""
URL-маршруты приложения blog.

Определяет URL-паттерны для просмотра постов и страницы "О блоге".
"""

from django.urls import path
from . import views

urlpatterns = [
    # Главная страница - список постов
    path("", views.post_list, name="post_list"),
    # Детальный просмотр поста
    path("post/<int:pk>/", views.post_detail, name="post_detail"),
    # Страница "О блоге"
    path("about/", views.about, name="about"),
]
