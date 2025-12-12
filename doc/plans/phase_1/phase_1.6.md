# Фаза 1.6: Внедрение Django 6 Template Partials

## Цель

Внедрить частичные шаблоны Django 6 (Template Partials) для оптимизации структуры шаблонов и подготовки к интеграции с HTMX.

## Контекст

Django 6 представляет новую киллер-фичу — **Template Partials**, которая позволяет определять фрагменты HTML прямо внутри основного файла шаблона. Это уменьшает количество файлов, упрощает поддержку и идеально работает с HTMX для частичного обновления страниц.

**Преимущества:**
- Меньше файлов — все фрагменты в одном месте
- Легче понять структуру страницы
- Идеальная интеграция с HTMX (возврат только части страницы)
- Сохранение читаемости кода

## Задачи

### 1. Рефакторинг шаблона списка постов

- [x] Обновить `templates/blog/post_list.html`:
  - Выделить карточку поста в partial `{% partialdef post_card %}`
  - Выделить пустое состояние в partial `{% partialdef empty_state %}`
  - Сохранить основную структуру страницы
- [x] Проверить корректность отображения

### 2. Рефакторинг шаблона детального просмотра

- [x] Обновить `templates/blog/post_detail.html`:
  - Выделить заголовок поста в partial `{% partialdef post_header %}`
  - Выделить контент поста в partial `{% partialdef post_content %}`
  - Выделить метаданные в partial `{% partialdef post_meta %}`
- [x] Проверить корректность отображения

### 3. Создание базовых partials

- [x] В `base.html` создать переиспользуемые partials:
  - `{% partialdef navigation %}` — навигационное меню
  - Оставить footer без partial (не будет переиспользоваться)
  - Оставить основную структуру нетронутой

### 4. Документация использования

- [x] Создать комментарии в шаблонах:
  - Объяснить назначение каждого partial
  - Указать где и как используется
  - Добавить примеры вызова

### 5. Тестирование

- [x] Проверить все страницы работают корректно
- [x] Убедиться что стили применяются правильно
- [x] Готовность partials для вызова отдельно (подготовка к HTMX)

## Технические детали

### Синтаксис Template Partials

```django
{# Определение partial #}
{% #partial post_card %}
<div class="card mb-3">
  <div class="card-body">
    <h5 class="card-title">{{ post.title }}</h5>
    <p class="card-text">{{ post.content|truncatewords:30 }}</p>
  </div>
</div>
{% /partial %}

{# Использование partial в том же файле #}
{% for post in posts %}
  {% partial post_card %}
{% endfor %}
```

### Пример рефакторинга post_list.html

**Было:**
```django
{% for post in posts %}
  <div class="card mb-3">
    <div class="card-body">
      <!-- Много кода карточки -->
    </div>
  </div>
{% endfor %}
```

**Стало:**
```django
{% #partial post_card %}
  <div class="card mb-3">
    <div class="card-body">
      <!-- Много кода карточки -->
    </div>
  </div>
{% /partial %}

{% for post in posts %}
  {% partial post_card %}
{% endfor %}
```

## Результат

✅ Шаблоны переведены на использование Django 6 Template Partials  
✅ Код стал более структурированным и читаемым  
✅ Готова инфраструктура для работы с HTMX  
✅ Уменьшено количество файлов шаблонов  
✅ Сохранена вся функциональность приложения

## Связанная документация

- [Django 6 Template Innovations](../../researches/report_2/django6-templates-innovations.md)
- [Style Guide](style_guide_html.md)

## Следующий шаг

[Фаза 1.7](phase_1.7.md): Внедрение django-components для переиспользуемых UI-компонентов
