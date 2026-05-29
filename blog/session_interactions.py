from django.db import transaction
from django.db.models import F

from .models import Post, SessionPostInteraction


class SessionInteractionMixin:
    """Centralized helpers for anonymous session-based post interactions."""

    interaction_model = SessionPostInteraction

    def get_session_key(self):
        """Ensure the current anonymous visitor has a durable session key."""
        if not self.request.session.session_key:
            self.request.session.save()
        return self.request.session.session_key

    def get_interaction(self, post):
        interaction, _ = self.interaction_model.objects.get_or_create(
            session_key=self.get_session_key(),
            post=post,
        )
        return interaction

    def register_post_view(self, post):
        """Count only the first detail-page view of a post per session."""
        with transaction.atomic():
            interaction = self.get_interaction(post)
            if interaction.mark_viewed():
                Post.objects.filter(pk=post.pk).update(view_count=F("view_count") + 1)
                post.view_count = (post.view_count or 0) + 1
        return post

    def is_post_liked(self, post):
        if not self.request.session.session_key:
            return False
        return self.interaction_model.objects.filter(
            session_key=self.request.session.session_key,
            post=post,
            liked_at__isnull=False,
        ).exists()

    def toggle_post_like(self, post):
        """Toggle one anonymous like per session and return the new liked state."""
        with transaction.atomic():
            interaction = self.get_interaction(post)
            liked = interaction.toggle_like()
            delta = 1 if liked else -1
            Post.objects.filter(pk=post.pk).update(like_count=F("like_count") + delta)
            post.like_count = max((post.like_count or 0) + delta, 0)
        return liked
