"""
PostCard Component

Компонент карточки поста для отображения в списке.

Использование:
    {% component "post_card" post=post %}
"""

from django_components import Component, register


@register("post_card")
class PostCard(Component):
    template_name = "post_card/post_card.html"

    def get_template_data(self, args, kwargs, slots, context):
        """
        Подготовка данных для шаблона.

        Args:
            post (Post): Объект поста из модели
        """
        post = kwargs.get("post")

        if not post:
            raise ValueError("PostCard component requires 'post' argument")

        return {
            "post": post,
        }

    class Media:
        css = "post_card/post_card.css"
