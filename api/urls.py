from django.urls import path

from .views import (
    bulk_publish,
    health,
    list_posts,
    post_detail_api,
    publish_post,
    read_depth,
    stats,
    update_post_status,
)

app_name = "api"

urlpatterns = [
    path("health/", health, name="health"),
    path("posts/publish/", publish_post, name="publish_post"),
    path("posts/bulk/", bulk_publish, name="bulk_publish"),
    path("posts/", list_posts, name="list_posts"),
    path("posts/<slug:slug>/", post_detail_api, name="post_detail_api"),
    path("posts/<slug:slug>/status/", update_post_status, name="update_post_status"),
    path("posts/<slug:slug>/read-depth/", read_depth, name="read_depth"),
    path("stats/", stats, name="stats"),
]