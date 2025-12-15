# Фаза 3.25: Tom Select для категорий и других селекторов

## Цель

Применить Tom Select к ForeignKey полям (category, author) для автокомплита и единообразного UI всех селекторов в админке.

## Контекст

**Текущее состояние:** Поле category использует autocomplete_fields, author использует стандартный select.

**Проблема:** Разные стили виджетов в одной форме — filter_horizontal для тегов, autocomplete для категории, обычный select для автора. Нужна унификация.

**Решение:** Tom Select для всех селекторов — единый стиль, поиск, плавная анимация.

## Задачи

### Обновление PostAdminForm

- [ ] Добавить виджеты для category и author:

```python
from django_tomselect.widgets import TomSelectWidget

widgets = {
    'tags': TomSelectMultiple(
        attrs={'create': True, 'placeholder': 'Теги'}
    ),
    'category': TomSelectWidget(
        attrs={'placeholder': 'Выберите категорию'}
    ),
    'author': TomSelectWidget(
        attrs={'placeholder': 'Выберите автора'}
    ),
}
```

### Настройка поиска

- [ ] Убедиться что в CategoryAdmin и UserAdmin есть search_fields
- [ ] Tom Select автоматически использует search_fields для autocomplete

### Стилизация под Unfold

- [ ] Проверить что Tom Select корректно отображается в Unfold теме
- [ ] При необходимости добавить кастомный CSS в `static/admin/css/custom_admin.css`

### Тестирование

- [ ] Открыть форму поста — все селекты должны использовать Tom Select
- [ ] Проверить поиск категорий
- [ ] Проверить поиск авторов
- [ ] Проверить что стили единообразны

## Коммит

```
phase 3.25 feat: Применён Tom Select ко всем селекторам в PostAdmin

- Добавлен Tom Select для category и author
- Настроен автокомплит для ForeignKey полей
- Унифицирован UI всех селекторов в админке
- Стилизация под Unfold тему
```
