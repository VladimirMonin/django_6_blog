"""
Button Component

Переиспользуемый компонент кнопки с поддержкой:
- Разных стилей (dark, warning, outline-dark)
- Иконок Bootstrap Icons
- Ссылок и обычных кнопок
- Active состояния

Использование:
    {% component "button" text="Читать далее" url="/post/1/" %}
    {% component "button" text="Назад" url="/" icon="arrow-left" %}
    {% component "button" text="Главная" url="/" style="warning" active=True %}
"""

from django_components import Component, register


@register("button")
class Button(Component):
    template_file = "button/button.html"
    
    def get_template_data(self, args, kwargs, slots, context):
        """
        Подготовка данных для шаблона.
        
        Args:
            text (str): Текст кнопки
            url (str): URL для ссылки (по умолчанию "#")
            style (str): Стиль кнопки - dark/warning/outline-dark (по умолчанию "dark")
            icon (str): Имя иконки Bootstrap Icons (опционально)
            active (bool): Активное состояние (желтая обводка)
            size (str): Размер - sm/md/lg (по умолчанию None)
        """
        # Получаем параметры с значениями по умолчанию
        text = kwargs.get("text", "Button")
        url = kwargs.get("url", "#")
        style = kwargs.get("style", "dark")
        icon = kwargs.get("icon")
        active = kwargs.get("active", False)
        size = kwargs.get("size")
        
        # Формируем CSS классы
        css_classes = [f"btn btn-{style}"]
        
        if size:
            css_classes.append(f"btn-{size}")
        
        if active:
            css_classes.append("border-warning border-2")
        
        return {
            "text": text,
            "url": url,
            "css_class": " ".join(css_classes),
            "icon": icon,
        }
    
    class Media:
        css = "button/button.css"
