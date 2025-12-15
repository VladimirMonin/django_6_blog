# Фаза 3.24: Интеграция Tom Select для тегов

## Цель

Заменить виджет поля tags в PostAdmin на Tom Select с поддержкой создания тегов "на лету" (create=True).

## Контекст

**Текущее состояние:** В [blog/admin.py](../../../blog/admin.py) поле tags использует filter_horizontal.

**Проблема:** filter_horizontal неудобен — нет поиска, нельзя создать тег прямо в форме. Нужен Tom Select с create=True.

## Задачи

### Создание кастомной формы

- [ ] В [blog/admin.py](../../../blog/admin.py) создать PostAdminForm:

```python
from django import forms
from django_tomselect.widgets import TomSelectMultiple
from blog.models import Post, Tag

class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'
        widgets = {
            'tags': TomSelectMultiple(
                attrs={
                    'create': True,
                    'create-on-blur': True,
                    'placeholder': 'Выберите или создайте теги',
                }
            )
        }
```

### Применение формы к PostAdmin

- [ ] В PostAdmin добавить: `form = PostAdminForm`
- [ ] Удалить `filter_horizontal = ['tags']` (конфликт с Tom Select)

### Обработка создания тегов

- [ ] Tom Select автоматически создаёт теги при вводе нового значения
- [ ] Slug генерируется в `Tag.save()` через slugify

### Тестирование

- [ ] Открыть форму редактирования поста
- [ ] Проверить что поле tags использует Tom Select
- [ ] Ввести название нового тега — должен создаться автоматически
- [ ] Проверить поиск по существующим тегам
- [ ] Проверить множественный выбор

## Коммит

```
phase 3.24 feat: Интегрирован Tom Select для тегов с созданием на лету

- Создан PostAdminForm с TomSelectMultiple виджетом для tags
- Настроен create=True для создания тегов на лету
- Удалён filter_horizontal в пользу Tom Select
```
