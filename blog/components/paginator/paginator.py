"""
Paginator Component

SEO-friendly компонент пагинации с поддержкой HTMX.

Использование:
    {% component "paginator" page_obj=page_obj search_query=search_query %}

Параметры:
    - page_obj: Django Paginator page object
    - search_query: текущий поисковый запрос (опционально)
    - show_load_more: показывать кнопку "Загрузить еще" (по умолчанию True)
"""

from django_components import Component, register


@register("paginator")
class Paginator(Component):
    template_name = "paginator/paginator.html"

    def get_template_data(self, args, kwargs, slots, context):
        """
        Подготовка данных для пагинатора.

        Args:
            page_obj: Django Paginator page object (обязательно)
            search_query: текущий поисковый запрос
            show_load_more: показывать ли кнопку "Загрузить еще"
        """
        page_obj = kwargs.get("page_obj")
        search_query = kwargs.get("search_query", "")
        show_load_more = kwargs.get("show_load_more", True)

        if not page_obj:
            raise ValueError("Paginator component requires 'page_obj' argument")

        # Формируем параметры URL для поиска
        search_param = f"&search={search_query}" if search_query else ""

        # Определяем диапазон страниц для отображения
        current_page = page_obj.number
        total_pages = page_obj.paginator.num_pages

        # Показываем максимум 5 кнопок страниц
        page_range = []
        if total_pages <= 5:
            page_range = list(range(1, total_pages + 1))
        else:
            # Логика "умной" пагинации
            if current_page <= 3:
                page_range = list(range(1, 6))
            elif current_page >= total_pages - 2:
                page_range = list(range(total_pages - 4, total_pages + 1))
            else:
                page_range = list(range(current_page - 2, current_page + 3))

        return {
            "page_obj": page_obj,
            "current_page": current_page,
            "total_pages": total_pages,
            "page_range": page_range,
            "search_param": search_param,
            "show_load_more": show_load_more,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "previous_page": page_obj.previous_page_number()
            if page_obj.has_previous()
            else None,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        }

    class Media:
        css = "paginator/paginator.css"
