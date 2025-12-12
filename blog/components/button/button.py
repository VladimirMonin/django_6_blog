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
        
        # Разрешаем URL - если это имя маршрута, используем reverse()
        url = url_or_name
        if url_or_name and url_or_name != "#" and not url_or_name.startswith('/'):
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
        
        # Формируем полный класс иконки (если есть)
        icon_class = f"bi bi-{icon}" if icon else None
        
        return {
            "text": text,
            "url": url,
            "css_class": " ".join(css_classes),
            "icon_class": icon_class,
        }
    
    class Media:
        css = "button/button.css"
