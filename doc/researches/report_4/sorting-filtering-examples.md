# Пример 8: Sorting/Filtering (Сортировка и фильтрация)

## Сортировка таблицы

### Template

```html
<!-- table_sorting.html -->
<table class="sortable-table">
    <thead>
        <tr>
            <th>
                <button hx-get="{% url 'sort_table' %}?sort=name&order=asc"
                        hx-target="#table-body"
                        class="sort-header">
                    Имя ▲
                </button>
            </th>
            <th>
                <button hx-get="{% url 'sort_table' %}?sort=date&order=desc"
                        hx-target="#table-body"
                        class="sort-header">
                    Дата ▼
                </button>
            </th>
            <th>
                <button hx-get="{% url 'sort_table' %}?sort=price&order=asc"
                        hx-target="#table-body"
                        class="sort-header">
                    Цена ▲
                </button>
            </th>
        </tr>
    </thead>
    
    <tbody id="table-body">
        {% include 'table/partial_body.html' with items=items %}
    </tbody>
</table>
```

### View

```python
# views.py
from django.db.models import F

def table_view(request):
    items = Item.objects.all()
    return render(request, 'table/full.html', {'items': items})

def sort_table(request):
    sort_field = request.GET.get('sort', 'name')
    order = request.GET.get('order', 'asc')
    
    # Валидация полей для сортировки
    valid_fields = ['name', 'date', 'price']
    if sort_field not in valid_fields:
        sort_field = 'name'
    
    # Определение направления сортировки
    if order == 'desc':
        sort_field = f'-{sort_field}'
    
    items = Item.objects.all().order_by(sort_field)
    
    return render(request, 'table/partial_body.html', {
        'items': items,
        'current_sort': sort_field.replace('-', ''),
        'current_order': order
    })
```

### Partial Template

```html
<!-- table/partial_body.html -->
{% for item in items %}
    <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.created_at|date:"d.m.Y" }}</td>
        <td>{{ item.price }} руб.</td>
    </tr>
{% empty %}
    <tr>
        <td colspan="3">Нет данных</td>
    </tr>
{% endfor %}
```

## Фильтрация с множественными критериями

### Template

```html
<!-- filtering.html -->
<div class="filters">
    <div class="filter-group">
        <label>Категория:</label>
        <select name="category" 
                hx-get="{% url 'filter_items' %}"
                hx-trigger="change"
                hx-target="#filtered-results"
                hx-include="[name='status']">
            <option value="">Все категории</option>
            {% for category in categories %}
                <option value="{{ category.id }}">{{ category.name }}</option>
            {% endfor %}
        </select>
    </div>
    
    <div class="filter-group">
        <label>Статус:</label>
        <select name="status" 
                hx-get="{% url 'filter_items' %}"
                hx-trigger="change"
                hx-target="#filtered-results"
                hx-include="[name='category']">
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="inactive">Неактивные</option>
        </select>
    </div>
    
    <div class="filter-group">
        <input type="text" 
               name="search" 
               placeholder="Поиск..."
               hx-get="{% url 'filter_items' %}"
               hx-trigger="keyup changed delay:500ms"
               hx-target="#filtered-results"
               hx-include="[name='category'], [name='status']">
    </div>
</div>

<div id="filtered-results">
    {% include 'items/partial_list.html' with items=items %}
</div>
```

### View

```python
# views.py
from django.db.models import Q

def filter_items(request):
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    items = Item.objects.all()
    
    # Применяем фильтры
    if category_id:
        items = items.filter(category_id=category_id)
    
    if status:
        items = items.filter(status=status)
    
    if search:
        items = items.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    return render(request, 'items/partial_list.html', {'items': items})
```

## Динамические фильтры с обновлением счетчиков

### Template

```html
<!-- dynamic_filters.html -->
<div class="filter-panel">
    <div class="filter-section">
        <h4>Категории</h4>
        {% for category in categories %}
            <label>
                <input type="checkbox" 
                       name="categories" 
                       value="{{ category.id }}"
                       hx-get="{% url 'dynamic_filter' %}"
                       hx-trigger="change"
                       hx-target="#results-section"
                       hx-include="[name='tags']">
                {{ category.name }} 
                <span id="category-{{ category.id }}-count">
                    ({{ category.item_count }})
                </span>
            </label>
        {% endfor %}
    </div>
    
    <div class="filter-section">
        <h4>Теги</h4>
        {% for tag in tags %}
            <label>
                <input type="checkbox" 
                       name="tags" 
                       value="{{ tag.id }}"
                       hx-get="{% url 'dynamic_filter' %}"
                       hx-trigger="change"
                       hx-target="#results-section"
                       hx-include="[name='categories']">
                {{ tag.name }}
                <span id="tag-{{ tag.id }}-count">
                    ({{ tag.item_count }})
                </span>
            </label>
        {% endfor %}
    </div>
</div>

<div id="results-section">
    {% include 'items/results_with_counts.html' with items=items %}
</div>
```

### View

```python
# views.py
from django.db.models import Count

def dynamic_filter(request):
    selected_categories = request.GET.getlist('categories')
    selected_tags = request.GET.getlist('tags')
    
    items = Item.objects.all()
    
    # Применяем фильтры
    if selected_categories:
        items = items.filter(category_id__in=selected_categories)
    
    if selected_tags:
        items = items.filter(tags__id__in=selected_tags)
    
    # Получаем обновленные счетчики
    categories = Category.objects.annotate(
        item_count=Count('item', filter=Q(item__in=items))
    )
    
    tags = Tag.objects.annotate(
        item_count=Count('item', filter=Q(item__in=items))
    )
    
    return render(request, 'items/results_with_counts.html', {
        'items': items,
        'categories': categories,
        'tags': tags
    })
```

### Partial Template с обновлением счетчиков

```html
<!-- items/results_with_counts.html -->
<div id="results">
    <h3>Найдено {{ items.count }} элементов</h3>
    
    {% for item in items %}
        <div class="item">
            <h4>{{ item.name }}</h4>
            <p>{{ item.description }}</p>
        </div>
    {% empty %}
        <p>Нет элементов, соответствующих фильтрам</p>
    {% endfor %}
</div>

<!-- Обновление счетчиков через OOB swaps -->
{% for category in categories %}
    <span id="category-{{ category.id }}-count" 
          hx-swap-oob="true">
        ({{ category.item_count }})
    </span>
{% endfor %}

{% for tag in tags %}
    <span id="tag-{{ tag.id }}-count" 
          hx-swap-oob="true">
        ({{ tag.item_count }})
    </span>
{% endfor %}
```

## Range фильтр (диапазон цен)

### Template

```html
<!-- range_filter.html -->
<div class="range-filters">
    <div class="range-group">
        <label>Цена от:</label>
        <input type="number" 
               name="min_price" 
               placeholder="0"
               hx-get="{% url 'range_filter' %}"
               hx-trigger="keyup changed delay:500ms"
               hx-target="#range-results"
               hx-include="[name='max_price']">
    </div>
    
    <div class="range-group">
        <label>Цена до:</label>
        <input type="number" 
               name="max_price" 
               placeholder="10000"
               hx-get="{% url 'range_filter' %}"
               hx-trigger="keyup changed delay:500ms"
               hx-target="#range-results"
               hx-include="[name='min_price']">
    </div>
</div>

<div id="range-results">
    {% include 'items/range_results.html' with items=items %}
</div>
```

### View

```python
# views.py
def range_filter(request):
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    items = Item.objects.all()
    
    if min_price:
        items = items.filter(price__gte=min_price)
    
    if max_price:
        items = items.filter(price__lte=max_price)
    
    return render(request, 'items/range_results.html', {'items': items})
```