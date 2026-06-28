from django.urls import path

from .views import list_posts, post_detail_api, publish_post, update_post_status

app_name = "api"

urlpatterns = [
    path("posts/publish/", publish_post, name="publish_post"),
    path("posts/", list_posts, name="list_posts"),
    path("posts/<slug:slug>/", post_detail_api, name="post_detail_api"),
    path("posts/<slug:slug>/status/", update_post_status, name="update_post_status"),
]