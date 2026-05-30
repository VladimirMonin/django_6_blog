"""
Button Component

Переиспользуемый компонент кнопки с поддержкой:
- Разных стилей (dark, warning, outline-dark)
- Иконок Bootstrap Icons
- Ссылок и обычных кнопок
- Active состояния

Использование:
    {% component "button" text="Читать далее" url="/post/1/" %}
    {% component "button" text="Назад" url="post_list" icon="arrow-left" %}
    {% component "button" text="Главная" url="post_list" style="warning" active=True %}
"""

from django_components import Component, register
from django.urls import reverse, NoReverseMatch


@register("button")
class Button(Component):
    template_name = "button/button.html"

    def get_template_data(self, args, kwargs, slots, context):
        """
        Подготовка данных для шаблона.

        Args:
            text (str): Текст кнопки
            url (str): URL для ссылки или имя маршрута (по умолчанию "#")
            style (str): Стиль кнопки - dark/warning/outline-dark (по умолчанию "dark")
            icon (str): Имя иконки Bootstrap Icons (опционально)
            active (bool): Активное состояние (желтая обводка)
            size (str): Размер - sm/md/lg (по умолчанию None)
        """
        # Получаем параметры с значениями по умолчанию
        text = kwargs.get("text", "Button")
        url_or_name = kwargs.get("url", "#")
        style = kwargs.get("style", "dark")
        icon = kwargs.get("icon")
        active = kwargs.get("active", False)
        size = kwargs.get("size")
        mobile_icon_only = kwargs.get("mobile_icon_only", False)

        # Разрешаем URL - если это имя маршрута, используем reverse()
        url = url_or_name
        if url_or_name and url_or_name != "#" and not url_or_name.startswith("/"):
            try:
                url = reverse(url_or_name)
            except NoReverseMatch:
                # Если не получилось разрешить как имя маршрута, оставляем как есть
                url = url_or_name

        # Формируем CSS классы
        css_classes = [f"btn btn-{style}"]

        if size:
            css_classes.append(f"btn-{size}")

        if active:
            css_classes.append("border-warning border-2")

        # Формируем полный класс иконки (если есть). Поддерживаем и "arrow-left",
        # и уже готовый Bootstrap Icons формат "bi-arrow-left".
        if icon:
            icon_name = icon if icon.startswith("bi-") else f"bi-{icon}"
            icon_class = f"bi {icon_name}"
        else:
            icon_class = None

        text_class = "button-text"
        if mobile_icon_only:
            text_class += " d-none d-sm-inline"

        return {
            "text": text,
            "url": url,
            "css_class": " ".join(css_classes),
            "icon_class": icon_class,
            "text_class": text_class,
            "aria_label": text,
        }

    class Media:
        css = "button/button.css"
