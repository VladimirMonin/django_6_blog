from django.conf import settings


def site_identity(request):
    """Expose public site identity values to all templates."""

    return {
        "site_author": getattr(settings, "SITE_AUTHOR", "Владимир Монин"),
    }
