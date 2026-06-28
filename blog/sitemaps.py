"""Sitemap classes for published blog posts and static pages."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Post


class PostSitemap(Sitemap):
    """Published blog posts — changefreq weekly, priority 0.8."""

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED)

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    """Static pages (home, about) — changefreq daily, priority 0.5."""

    changefreq = "daily"
    priority = 0.5

    def items(self):
        return ["post_list", "about"]

    def location(self, item):
        return reverse(item)