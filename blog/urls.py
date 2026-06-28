"""
URL-маршруты приложения blog.

Определяет URL-паттерны для просмотра постов и страницы "О блоге".
"""

from django.urls import path

from .views import (
    AboutView,
    PostDetailView,
    PostLikeToggleView,
    PostListView,
    SeriesDetailView,
)

urlpatterns = [
    path("", PostListView.as_view(), name="post_list"),
    path("post/<slug:slug>/", PostDetailView.as_view(), name="post_detail"),
    path("post/<slug:slug>/like/", PostLikeToggleView.as_view(), name="post_like_toggle"),
    path("series/<slug:slug>/", SeriesDetailView.as_view(), name="series_detail"),
    path("about/", AboutView.as_view(), name="about"),
]
