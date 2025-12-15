# Фаза 3.22: Обновление templates для категорий и тегов

## Цель

Модифицировать [post_detail.html](../../../templates/blog/post_detail.html) и [post_card.html](../../../templates/blog/_post_cards_only.html) для отображения категории, тегов, обложки, excerpt.

## Контекст

**Текущее состояние:** Templates отображают только базовые поля Post.

**Проблема:** Новые данные (категория, теги, обложка) не отображаются на сайте.

## Задачи

### Обновление post_detail.html

- [ ] Добавить отображение category над заголовком:

```django
{% if post.category %}
<span class="badge bg-primary">{{ post.category.name }}</span>
{% endif %}
```

- [ ] Добавить теги под контентом:

```django
{% if post.tags.exists %}
<div class="tags">
  {% for tag in post.tags.all %}
    <a href="{% url 'tag_detail' tag.slug %}" class="badge bg-secondary">{{ tag.name }}</a>
  {% endfor %}
</div>
{% endif %}
```

### Обновление post_card.html

- [ ] Добавить обложку сверху карточки:

```django
{% if post.cover %}
<img src="{{ post.cover.file.url }}" class="card-img-top" alt="{{ post.title }}">
{% endif %}
```

- [ ] Использовать excerpt вместо обрезанного content

### Тестирование

- [ ] Открыть детальную страницу поста — проверить категорию и теги
- [ ] Открыть список постов — проверить обложки и excerpt в карточках

## Коммит

```
phase 3.22 feat: Обновлены templates для отображения категорий, тегов, обложек

- Добавлено отображение category в post_detail.html
- Добавлены теги под контентом
- Обновлён post_card.html для отображения cover и excerpt
```
