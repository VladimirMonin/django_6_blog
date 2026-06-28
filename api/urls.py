from django.urls import path

from .views import publish_post

app_name = "api"

urlpatterns = [
    path("posts/publish/", publish_post, name="publish_post"),
]