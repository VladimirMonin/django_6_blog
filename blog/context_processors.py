from .seo import canonical_url, site_entities


def seo_context(request):
    """Expose canonical and truthful shared SEO identity values to templates."""

    entities = site_entities(request)
    return {
        "canonical_url": canonical_url(request),
        "site_author": entities["person"]["name"],
        "author_url": entities["person"]["url"],
        "site_url": entities["website"]["url"],
        "site_web_site": entities["website"],
        "site_person": entities["person"],
    }
