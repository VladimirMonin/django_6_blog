# Пример 7: Modal (Модальное окно)

## Template

```html
<!-- modal_trigger.html -->
<button hx-get="{% url 'modal_content' %}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
    Открыть модальное окно
</button>

<!-- Контейнер для модального окна -->
<div id="modal-container"></div>
```

## View

```python
# views.py
def modal_content(request):
    return render(request, 'modal/content.html')

def modal_action(request):
    if request.method == 'POST':
        # Обработка действия
        return HttpResponse('<script>window.location.reload()</script>')
    return HttpResponse('')
```

## Modal Template

```html
<!-- modal/content.html -->
<div class="modal-overlay" id="modal-overlay">
    <div class="modal">
        <div class="modal-header">
            <h3>Модальное окно</h3>
            <button onclick="closeModal()">×</button>
        </div>
        
        <div class="modal-body">
            <p>Содержимое модального окна</p>
            
            <form hx-post="{% url 'modal_action' %}"
                  hx-target="#modal-result">
                {% csrf_token %}
                <input type="text" name="data" placeholder="Введите данные">
                <button type="submit">Сохранить</button>
            </form>
            
            <div id="modal-result"></div>
        </div>
        
        <div class="modal-footer">
            <button onclick="closeModal()">Закрыть</button>
        </div>
    </div>
</div>

<style>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal {
    background: white;
    padding: 20px;
    border-radius: 8px;
    max-width: 500px;
    width: 90%;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
</style>

<script>
function closeModal() {
    document.getElementById('modal-container').innerHTML = '';
}

// Закрытие по клику вне модального окна
document.addEventListener('click', function(event) {
    const modalContainer = document.getElementById('modal-container');
    if (event.target === modalContainer) {
        closeModal();
    }
});
</script>
```

## Альтернативный подход с HTMX

```html
<!-- Альтернатива с hx-on -->
<button hx-get="/modal/" 
        hx-target="body" 
        hx-swap="beforeend">
    Открыть модальное окно
</button>

<!-- Модальное окно будет добавлено в конец body -->
```

```python
# View для альтернативного подхода
def modal_view(request):
    return render(request, 'modal/full_modal.html')
```

```html
<!-- modal/full_modal.html -->
<div class="modal-overlay" 
     hx-on:click="this.remove()"
     style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
    
    <div class="modal" 
         hx-on:click="event.stopPropagation()"
         style="background: white; padding: 20px; border-radius: 8px; max-width: 500px; width: 90%;">
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h3>Модальное окно</h3>
            <button hx-on:click="this.closest('.modal-overlay').remove()">×</button>
        </div>
        
        <div>
            <p>Содержимое модального окна</p>
            
            <form hx-post="/modal-action/" 
                  hx-target="#modal-result">
                {% csrf_token %}
                <input type="text" name="data" placeholder="Введите данные">
                <button type="submit">Сохранить</button>
            </form>
            
            <div id="modal-result"></div>
        </div>
    </div>
</div>
```