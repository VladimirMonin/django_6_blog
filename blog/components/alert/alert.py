"""
Alert Component

Компонент уведомлений с поддержкой разных типов.

Использование:
    {% component "alert" message="Успешно!" type="success" %}
    {% component "alert" message="Ошибка!" type="danger" %}
    {% component "alert" message="Внимание!" type="warning" %}
"""

from django_components import Component, register


@register("alert")
class Alert(Component):
    template_name = "alert/alert.html"

    # Маппинг типов на иконки
    ICON_MAP = {
        "success": "check-circle",
        "danger": "exclamation-triangle",
        "warning": "exclamation-circle",
        "info": "info-circle",
    }

    def get_template_data(self, args, kwargs, slots, context):
        """
        Подготовка данных для шаблона.

        Args:
            message (str): Текст сообщения
            type (str): Тип alert - success/danger/warning/info (по умолчанию "info")
            dismissible (bool): Возможность закрытия (по умолчанию False)
        """
        message = kwargs.get("message", "Alert message")
        alert_type = kwargs.get("type", "info")
        dismissible = kwargs.get("dismissible", False)

        # Получаем иконку для типа
        icon = self.ICON_MAP.get(alert_type, "info-circle")
        icon_class = f"bi bi-{icon}"

        # Формируем CSS классы
        css_classes = [f"alert alert-{alert_type}"]
        if dismissible:
            css_classes.append("alert-dismissible fade show")

        return {
            "message": message,
            "css_class": " ".join(css_classes),
            "icon_class": icon_class,
            "dismissible": dismissible,
        }

    class Media:
        css = "alert/alert.css"
