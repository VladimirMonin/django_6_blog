"""RSS 2.0 and Atom 1.0 syndication feeds for published blog posts."""

from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from .models import Post


class LatestPostsFeed(Feed):
    """RSS 2.0 feed of the 20 most recent published posts."""

    title = "Django 6 Blog"
    link = "/"
    description = "Заметки, эксперименты и материалы разработки Владимира Монина."

    def items(self):
        return Post.objects.filter(status=Post.Status.PUBLISHED)[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.created_at

    def item_updatedate(self, item):
        return item.updated_at

    def item_author_name(self):
        return "Владимир Монин"


class AtomLatestPostsFeed(LatestPostsFeed):
    """Atom 1.0 feed — same content, different format."""

    feed_type = Atom1Feed
    subtitle = LatestPostsFeed.description