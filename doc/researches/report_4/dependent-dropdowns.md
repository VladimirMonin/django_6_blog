# Пример 9: Dependent Dropdowns (Зависимые выпадающие списки)

## Базовый пример: Страна → Город

### Template

```html
<!-- dependent_dropdowns.html -->
<form>
    <div class="form-group">
        <label for="country">Страна:</label>
        <select id="country" 
                name="country"
                hx-get="{% url 'get_cities' %}"
                hx-trigger="change"
                hx-target="#city-select">
            <option value="">Выберите страну</option>
            {% for country in countries %}
                <option value="{{ country.id }}">{{ country.name }}</option>
            {% endfor %}
        </select>
    </div>
    
    <div class="form-group">
        <label for="city">Город:</label>
        <div id="city-select">
            <select id="city" name="city" disabled>
                <option value="">Сначала выберите страну</option>
            </select>
        </div>
    </div>
</form>
```

### Views

```python
# views.py
from django.shortcuts import render
from .models import Country, City

def dependent_dropdowns_view(request):
    countries = Country.objects.all()
    return render(request, 'forms/dependent_dropdowns.html', {
        'countries': countries
    })

def get_cities(request):
    country_id = request.GET.get('country')
    
    if country_id:
        cities = City.objects.filter(country_id=country_id)
        return render(request, 'forms/city_dropdown.html', {
            'cities': cities
        })
    else:
        return render(request, 'forms/empty_dropdown.html')
```

### Partial Templates

```html
<!-- forms/city_dropdown.html -->
<select id="city" name="city">
    <option value="">Выберите город</option>
    {% for city in cities %}
        <option value="{{ city.id }}">{{ city.name }}</option>
    {% endfor %}
</select>

<!-- forms/empty_dropdown.html -->
<select id="city" name="city" disabled>
    <option value="">Сначала выберите страну</option>
</select>
```

## Многоуровневые зависимые списки

### Template

```html
<!-- multi_level_dropdowns.html -->
<form>
    <div class="form-group">
        <label>Категория:</label>
        <select name="category"
                hx-get="{% url 'get_subcategories' %}"
                hx-trigger="change"
                hx-target="#subcategory-select">
            <option value="">Выберите категорию</option>
            {% for category in categories %}
                <option value="{{ category.id }}">{{ category.name }}</option>
            {% endfor %}
        </select>
    </div>
    
    <div class="form-group">
        <label>Подкатегория:</label>
        <div id="subcategory-select">
            <select name="subcategory" disabled>
                <option value="">Сначала выберите категорию</option>
            </select>
        </div>
    </div>
    
    <div class="form-group">
        <label>Продукт:</label>
        <div id="product-select">
            <select name="product" disabled>
                <option value="">Сначала выберите подкатегорию</option>
            </select>
        </div>
    </div>
</form>
```

### Views

```python
# views.py
from .models import Category, Subcategory, Product

def multi_level_view(request):
    categories = Category.objects.all()
    return render(request, 'forms/multi_level.html', {
        'categories': categories
    })

def get_subcategories(request):
    category_id = request.GET.get('category')
    
    if category_id:
        subcategories = Subcategory.objects.filter(category_id=category_id)
        return render(request, 'forms/subcategory_dropdown.html', {
            'subcategories': subcategories
        })
    else:
        return render(request, 'forms/empty_subcategory.html')

def get_products(request):
    subcategory_id = request.GET.get('subcategory')
    
    if subcategory_id:
        products = Product.objects.filter(subcategory_id=subcategory_id)
        return render(request, 'forms/product_dropdown.html', {
            'products': products
        })
    else:
        return render(request, 'forms/empty_product.html')
```

### Обновленный Template с тремя уровнями

```html
<!-- multi_level_dropdowns_updated.html -->
<form>
    <div class="form-group">
        <label>Категория:</label>
        <select name="category"
                hx-get="{% url 'get_subcategories' %}"
                hx-trigger="change"
                hx-target="#subcategory-select">
            <option value="">Выберите категорию</option>
            {% for category in categories %}
                <option value="{{ category.id }}">{{ category.name }}</option>
            {% endfor %}
        </select>
    </div>
    
    <div class="form-group">
        <label>Подкатегория:</label>
        <div id="subcategory-select">
            <select name="subcategory" 
                    disabled
                    hx-get="{% url 'get_products' %}"
                    hx-trigger="change"
                    hx-target="#product-select">
                <option value="">Сначала выберите категорию</option>
            </select>
        </div>
    </div>
    
    <div class="form-group">
        <label>Продукт:</label>
        <div id="product-select">
            <select name="product" disabled>
                <option value="">Сначала выберите подкатегорию</option>
            </select>
        </div>
    </div>
</form>
```

### Partial Templates для многоуровневых списков

```html
<!-- forms/subcategory_dropdown.html -->
<select name="subcategory" 
        hx-get="{% url 'get_products' %}"
        hx-trigger="change"
        hx-target="#product-select">
    <option value="">Выберите подкатегорию</option>
    {% for subcategory in subcategories %}
        <option value="{{ subcategory.id }}">{{ subcategory.name }}</option>
    {% endfor %}
</select>

<!-- forms/product_dropdown.html -->
<select name="product">
    <option value="">Выберите продукт</option>
    {% for product in products %}
        <option value="{{ product.id }}">{{ product.name }}</option>
    {% endfor %}
</select>

<!-- forms/empty_subcategory.html -->
<select name="subcategory" 
        disabled
        hx-get="{% url 'get_products' %}"
        hx-trigger="change"
        hx-target="#product-select">
    <option value="">Сначала выберите категорию</option>
</select>

<!-- forms/empty_product.html -->
<select name="product" disabled>
    <option value="">Сначала выберите подкатегорию</option>
</select>
```

## Динамические формы с зависимыми полями

### Template

```html
<!-- dynamic_form.html -->
<form method="post">
    {% csrf_token %}
    
    <div class="form-group">
        <label>Тип пользователя:</label>
        <select name="user_type"
                hx-get="{% url 'get_user_fields' %}"
                hx-trigger="change"
                hx-target="#dynamic-fields">
            <option value="">Выберите тип</option>
            <option value="individual">Физическое лицо</option>
            <option value="company">Юридическое лицо</option>
        </select>
    </div>
    
    <div id="dynamic-fields">
        <!-- Динамические поля появятся здесь -->
    </div>
    
    <button type="submit">Сохранить</button>
</form>
```

### View

```python
# views.py
from django import forms

def dynamic_form_view(request):
    if request.method == 'POST':
        # Обработка формы
        pass
    return render(request, 'forms/dynamic_form.html')

def get_user_fields(request):
    user_type = request.GET.get('user_type')
    
    if user_type == 'individual':
        return render(request, 'forms/individual_fields.html')
    elif user_type == 'company':
        return render(request, 'forms/company_fields.html')
    else:
        return HttpResponse('')
```

### Partial Templates для динамических полей

```html
<!-- forms/individual_fields.html -->
<div class="individual-fields">
    <div class="form-group">
        <label>Имя:</label>
        <input type="text" name="first_name" required>
    </div>
    
    <div class="form-group">
        <label>Фамилия:</label>
        <input type="text" name="last_name" required>
    </div>
    
    <div class="form-group">
        <label>Паспорт:</label>
        <input type="text" name="passport" required>
    </div>
</div>

<!-- forms/company_fields.html -->
<div class="company-fields">
    <div class="form-group">
        <label>Название компании:</label>
        <input type="text" name="company_name" required>
    </div>
    
    <div class="form-group">
        <label>ИНН:</label>
        <input type="text" name="inn" required>
    </div>
    
    <div class="form-group">
        <label>КПП:</label>
        <input type="text" name="kpp" required>
    </div>
</div>
```

## Зависимые списки с предварительной загрузкой

### Template с предзагрузкой

```html
<!-- preloaded_dropdowns.html -->
<form>
    <div class="form-group">
        <label>Регион:</label>
        <select name="region"
                hx-get="{% url 'get_cities_by_region' %}"
                hx-trigger="change"
                hx-target="#city-select"
                hx-indicator="#city-loading">
            <option value="">Выберите регион</option>
            {% for region in regions %}
                <option value="{{ region.id }}">{{ region.name }}</option>
            {% endfor %}
        </select>
    </div>
    
    <div class="form-group">
        <label>Город:</label>
        <div id="city-select">
            <select name="city" disabled>
                <option value="">Сначала выберите регион</option>
            </select>
        </div>
        <div id="city-loading" class="htmx-indicator">
            Загрузка городов...
        </div>
    </div>
</form>
```

### View с кэшированием

```python
# views.py
from django.core.cache import cache

def get_cities_by_region(request):
    region_id = request.GET.get('region')
    
    if not region_id:
        return render(request, 'forms/empty_city.html')
    
    # Кэширование для производительности
    cache_key = f'cities_region_{region_id}'
    cities = cache.get(cache_key)
    
    if not cities:
        cities = City.objects.filter(region_id=region_id)
        cache.set(cache_key, list(cities), 300)  # 5 минут
    
    return render(request, 'forms/city_dropdown.html', {
        'cities': cities
    })
```

## Обработка ошибок и валидация

### Template с обработкой ошибок

```html
<!-- dropdowns_with_validation.html -->
<form>
    <div class="form-group">
        <label>Категория:</label>
        <select name="category"
                hx-get="{% url 'get_subcategories' %}"
                hx-trigger="change"
                hx-target="#subcategory-section"
                hx-on::after-request="validateForm()">
            <option value="">Выберите категорию</option>
            {% for category in categories %}
                <option value="{{ category.id }}">{{ category.name }}</option>
            {% endfor %}
        </select>
        <div id="category-error" class="error-message"></div>
    </div>
    
    <div id="subcategory-section">
        {% include 'forms/subcategory_section.html' %}
    </div>
    
    <button type="submit" id="submit-btn" disabled>Отправить</button>
</form>

<script>
function validateForm() {
    const category = document.querySelector('[name="category"]').value;
    const subcategory = document.querySelector('[name="subcategory"]')?.value;
    const submitBtn = document.getElementById('submit-btn');
    
    if (category && subcategory) {
        submitBtn.disabled = false;
    } else {
        submitBtn.disabled = true;
    }
}
</script>
```