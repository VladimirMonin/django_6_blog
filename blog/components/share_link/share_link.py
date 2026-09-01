"""Reusable copy-link control for public post cards and detail pages."""

from django_components import Component, register


@register("share_link")
class ShareLink(Component):
    """Render an accessible button handled by the shared share-link script."""

    template_name = "share_link/share_link.html"

    def get_template_data(self, args, kwargs, slots, context):
        """Prepare the URL, label, and layout variant for the component."""
        url = kwargs.get("url")
        if not url:
            raise ValueError("ShareLink component requires 'url' argument")

        variant = kwargs.get("variant", "card")
        label = kwargs.get("label", "Скопировать ссылку")
        return {
            "url": url,
            "label": label,
            "variant": variant,
            "aria_label": kwargs.get("aria_label", label),
        }

    class Media:
        css = "share_link/share_link.css"
