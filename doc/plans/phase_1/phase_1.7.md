# Фаза 1.7: Внедрение django-components

## Цель

Установить и настроить `django-components`, создать первые переиспользуемые компоненты для замены повторяющихся элементов UI.

## Контекст

`django-components` позволяет создавать инкапсулированные, переиспользуемые UI-компоненты с собственными шаблонами, стилями и логикой. Это идеально подходит для сложных элементов интерфейса, которые используются в разных частях приложения.

**Важно:** django-components примерно в 4 раза медленнее стандартных шаблонов. Используем их **стратегически** для сложных UI-элементов, а не для всего подряд.

**Когда использовать:**
- ✅ Сложные UI компоненты с логикой
- ✅ Переиспользуемые элементы (кнопки, карточки, модалки)
- ✅ Компоненты с собственными стилями и JS
- ❌ Простой статический контент
- ❌ Элементы без собственной логики

## Задачи

### 1. Установка и настройка

- [ ] Установить django-components через Poetry:
  ```bash
  poetry add django-components
  ```
- [ ] Добавить в `INSTALLED_APPS` в settings.py:
  ```python
  INSTALLED_APPS = [
      # ...
      'django_components',
  ]
  ```
- [ ] Добавить в `TEMPLATES` в settings.py:
  ```python
  TEMPLATES = [
      {
          'OPTIONS': {
              'context_processors': [
                  # ...
              ],
              'builtins': [
                  'django_components.templatetags.component_tags',
              ],
          },
      },
  ]
  ```
- [ ] Создать структуру папок:
  ```
  blog/
    components/
      __init__.py
      button/
        button.py
        button.html
        button.css
      post_card/
        post_card.py
        post_card.html
        post_card.css
  ```

### 2. Создание компонента Button

- [ ] Создать компонент `blog/components/button/button.py`:
  - Базовый класс компонента
  - Props: text, style (primary/secondary), url, icon
  - Логика определения CSS классов
- [ ] Создать шаблон `button.html`:
  - Кнопка с поддержкой разных стилей
  - Поддержка иконок Bootstrap Icons
- [ ] Создать стили `button.css`:
  - Hover эффекты
  - Желтый акцент для active состояния
- [ ] Использовать компонент в существующих шаблонах

### 3. Создание компонента PostCard

- [ ] Создать компонент `blog/components/post_card/post_card.py`:
  - Props: post (объект Post)
  - Методы форматирования даты
  - Логика обрезки контента
- [ ] Создать шаблон `post_card.html`:
  - Bootstrap card структура
  - Отображение заголовка, даты, превью
  - Кнопка "Читать далее" через Button компонент
- [ ] Создать стили `post_card.css`:
  - Hover эффекты для карточки
  - Плавные переходы
- [ ] Заменить карточки в `post_list.html` на компонент

### 4. Создание компонента Alert

- [ ] Создать компонент `blog/components/alert/alert.py`:
  - Props: message, type (success/warning/error/info)
  - Метод определения иконки по типу
  - Логика отображения
- [ ] Создать шаблон `alert.html`:
  - Bootstrap alert структура
  - Поддержка иконок
  - Кнопка закрытия (подготовка к HTMX)
- [ ] Создать стили `alert.css`:
  - Кастомизация цветов согласно style_guide
  - Анимация появления/скрытия

### 5. Обновление базовых шаблонов

- [ ] Обновить `post_list.html`:
  - Использовать PostCard компонент вместо HTML
  - Передавать объект post в props
- [ ] Обновить навигацию в `base.html`:
  - Использовать Button компонент для навигационных кнопок
  - Сохранить активное состояние с желтым акцентом
- [ ] Добавить примеры Alert компонента (для будущих уведомлений)

### 6. Тестирование и оптимизация

- [ ] Проверить корректность отображения всех компонентов
- [ ] Убедиться что CSS изолирован и не конфликтует
- [ ] Проверить производительность (не должна сильно упасть)
- [ ] Документировать props каждого компонента

### 7. Документация компонентов

- [ ] Создать `blog/components/README.md`:
  - Список всех компонентов
  - Описание props и методов
  - Примеры использования
  - Best practices

## Технические детали

### Структура компонента (на примере Button)

**button.py:**
```python
from django_components import Component, register

@register("button")
class Button(Component):
    template_name = "button/button.html"
    
    def get_context_data(self, text, url="#", style="dark", icon=None):
        css_class = f"btn btn-{style}"
        if style == "active":
            css_class += " border-warning"
        
        return {
            "text": text,
            "url": url,
            "css_class": css_class,
            "icon": icon,
        }
    
    class Media:
        css = "button/button.css"
```

**button.html:**
```django
<a href="{{ url }}" class="{{ css_class }}">
    {% if icon %}
        <i class="bi bi-{{ icon }}"></i>
    {% endif %}
    {{ text }}
</a>
```

**button.css:**
```css
.btn-dark:hover {
    background-color: #000;
    transform: translateY(-2px);
    transition: all 0.2s ease;
}
```

### Использование в шаблонах

```django
{% load component_tags %}

{# Простая кнопка #}
{% component "button" text="Читать далее" url=post.get_absolute_url %}

{# Кнопка с иконкой #}
{% component "button" text="Назад" url="{% url 'blog:post_list' %}" icon="arrow-left" %}

{# Карточка поста #}
{% component "post_card" post=post %}
```

## Результат

✅ Установлен и настроен django-components  
✅ Созданы 3 базовых компонента: Button, PostCard, Alert  
✅ Компоненты используются в существующих шаблонах  
✅ Код стал более модульным и переиспользуемым  
✅ Подготовлена база для создания новых компонентов  
✅ Документация компонентов готова

## Производительность

⚠️ **Важно:** Мониторим производительность. django-components медленнее на 4x, но для нашего случая (блог с небольшим трафиком) это приемлемо. Основные страницы должны загружаться быстро.

## Связанная документация

- [Django Components Research](../../researches/report_3/django-components-research.md)
- [Practical Examples](../../researches/report_3/practical-examples.md)
- [Performance Best Practices](../../researches/report_3/performance-best-practices.md)
- [Style Guide](style_guide_html.md)

## Следующий шаг

[Фаза 1.8](phase_1.8.md): Интеграция HTMX для динамических взаимодействий
