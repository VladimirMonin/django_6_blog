"""
URL-маршруты приложения blog.

Определяет URL-паттерны для просмотра постов и страницы "О блоге".
"""

from django.urls import path

from .views import AboutView, PostDetailView, PostLikeToggleView, PostListView

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),
    path("post/<int:pk>/", PostDetailView.as_view(), name="post_detail"),
    path("post/<int:pk>/like/", PostLikeToggleView.as_view(), name="post_like_toggle"),
    path("about/", AboutView.as_view(), name="about"),
]
