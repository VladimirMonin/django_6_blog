# Фаза 2.7: Frontend интерактивность (JS для медиа, копирования, фуллскрин)

## Цель

Добавить интерактивные JS-компоненты для улучшения UX: фуллскрин просмотр изображений, кнопки копирования кода, медиаплееры (Plyr.io), генерация оглавления.

## Контекст

После Phase 2.6 у нас есть:
- ✅ HTML с Bootstrap классами (backend)
- ⏳ Нужна интерактивность (frontend)

**Что добавляем:**
1. **Фуллскрин изображений** — клик на изображение → оверлей на весь экран
2. **Копирование кода** — кнопка "Copy" для code blocks
3. **Медиаплееры** — Plyr.io для `<video>` и `<audio>`
4. **Генерация оглавления** — автоматический TOC из `<h2>` и `<h3>`

**Философия:** Прогрессивное улучшение — сайт работает без JS, но с JS лучше.

**Референс:** `doc/samples/assets/js/` — готовые модули из твоего проекта

**Документация:**
- Plyr.io: https://plyr.io/
- Clipboard API: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API

## Задачи

### 1. Создание структуры static/js/

- [ ] Создать директорию `static/js/` (если еще не существует)
- [ ] Создать файлы:
  - `static/js/fullscreen-images.js`
  - `static/js/code-copy.js`
  - `static/js/media-players.js`
  - `static/js/table-of-contents.js`
  - `static/js/main.js` (инициализация всего)

### 2. Фуллскрин изображений — fullscreen-images.js

- [ ] Создать файл `static/js/fullscreen-images.js`
- [ ] Реализовать логику:
  ```javascript
  function enableFullscreenImages() {
      // Создаем оверлей контейнер
      const overlay = document.createElement('div');
      overlay.className = 'fullscreen-img-container';
      document.body.appendChild(overlay);
      
      // Добавляем обработчики на все изображения
      document.querySelectorAll('.markdown-content img').forEach(img => {
          img.style.cursor = 'pointer';
          img.addEventListener('click', () => showFullscreen(img.src, overlay));
      });
      
      // Закрытие по клику на оверлей
      overlay.addEventListener('click', () => {
          overlay.classList.remove('active');
      });
  }
  
  function showFullscreen(src, overlay) {
      const img = new Image();
      img.src = src;
      
      img.onload = function() {
          const screenRatio = window.innerWidth / window.innerHeight;
          const imageRatio = this.width / this.height;
          
          if (imageRatio > screenRatio) {
              img.style.width = '100vw';
              img.style.height = 'auto';
          } else {
              img.style.width = 'auto';
              img.style.height = '100vh';
          }
      };
      
      overlay.innerHTML = '';
      overlay.appendChild(img);
      overlay.classList.add('active');
  }
  ```
- [ ] Добавить CSS в `static/css/style.css`:
  ```css
  .fullscreen-img-container {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(0, 0, 0, 0.95);
      z-index: 9999;
      display: none;
      justify-content: center;
      align-items: center;
      cursor: pointer;
  }
  
  .fullscreen-img-container.active {
      display: flex;
  }
  
  .fullscreen-img-container img {
      max-width: 100vw;
      max-height: 100vh;
      object-fit: contain;
  }
  ```

**Референс:** `doc/samples/assets/js/media.js:1-39`

### 3. Кнопки копирования кода — code-copy.js

- [ ] Создать файл `static/js/code-copy.js`
- [ ] Реализовать логику:
  ```javascript
  function addCodeCopyButtons() {
      document.querySelectorAll('pre').forEach(preBlock => {
          // Добавляем контейнер класс
          preBlock.classList.add('pre-container');
          
          // Создаем кнопку копирования
          const copyBtn = document.createElement('i');
          copyBtn.className = 'bi bi-clipboard code-copy-btn';
          copyBtn.title = 'Скопировать код';
          
          // Добавляем кнопку в pre
          preBlock.appendChild(copyBtn);
          
          // Обработчик клика
          copyBtn.addEventListener('click', () => {
              const code = preBlock.querySelector('code');
              if (!code) return;
              
              const text = code.innerText;
              navigator.clipboard.writeText(text).then(() => {
                  // Меняем иконку на "скопировано"
                  copyBtn.className = 'bi bi-clipboard-check code-copy-btn';
                  copyBtn.style.color = 'lightgreen';
                  
                  setTimeout(() => {
                      copyBtn.className = 'bi bi-clipboard code-copy-btn';
                      copyBtn.style.color = '';
                  }, 3000);
              });
          });
      });
  }
  ```
- [ ] Добавить CSS в `static/css/style.css`:
  ```css
  .pre-container {
      position: relative;
  }
  
  .code-copy-btn {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      font-size: 1.2rem;
      color: #fff;
      cursor: pointer;
      opacity: 0.7;
      transition: opacity 0.2s;
  }
  
  .code-copy-btn:hover {
      opacity: 1;
  }
  ```

**Референс:** `doc/samples/assets/js/codeCopy.js`

### 4. Медиаплееры Plyr.io — media-players.js

- [ ] Создать файл `static/js/media-players.js`
- [ ] Реализовать логику:
  ```javascript
  function initMediaPlayers() {
      // Проверяем наличие Plyr
      if (typeof Plyr === 'undefined') {
          console.warn('Plyr не загружен');
          return;
      }
      
      // Инициализация для видео
      const videoElements = document.querySelectorAll('.markdown-content video');
      videoElements.forEach(video => {
          new Plyr(video, {
              controls: [
                  'play-large',
                  'play',
                  'progress',
                  'current-time',
                  'duration',
                  'mute',
                  'volume',
                  'settings',
                  'fullscreen'
              ],
              settings: ['quality', 'speed'],
              speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
          });
      });
      
      // Инициализация для аудио
      const audioElements = document.querySelectorAll('.markdown-content audio');
      audioElements.forEach(audio => {
          new Plyr(audio, {
              controls: [
                  'play',
                  'progress',
                  'current-time',
                  'duration',
                  'mute',
                  'volume',
                  'settings'
              ],
              settings: ['speed'],
              speed: { selected: 1, options: [0.5, 0.75, 1, 1.25, 1.5, 2] }
          });
      });
      
      console.log(`Инициализировано ${videoElements.length} видео и ${audioElements.length} аудио плееров`);
  }
  ```
- [ ] Подключить Plyr CDN в `templates/base.html`:
  ```html
  <!-- CSS в <head> -->
  <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
  
  <!-- JS перед </body> -->
  <script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
  ```

**Референс:** `doc/samples/assets/js/media.js:42-104`

### 5. Генерация оглавления — table-of-contents.js

- [ ] Создать файл `static/js/table-of-contents.js`
- [ ] Реализовать логику:
  ```javascript
  function generateTableOfContents() {
      const tocContainer = document.getElementById('table-of-contents');
      if (!tocContainer) return;
      
      const headings = document.querySelectorAll('.markdown-content h2, .markdown-content h3');
      if (headings.length === 0) return;
      
      const tocList = document.createElement('ul');
      tocList.className = 'list-unstyled';
      
      headings.forEach((heading, index) => {
          // Добавляем ID к заголовку (если нет)
          if (!heading.id) {
              heading.id = `heading-${index}`;
          }
          
          const tocItem = document.createElement('li');
          tocItem.className = heading.tagName === 'H2' ? 'mb-2' : 'ms-3 mb-1';
          
          const tocLink = document.createElement('a');
          tocLink.href = `#${heading.id}`;
          tocLink.textContent = heading.textContent;
          tocLink.className = 'text-decoration-none';
          
          tocItem.appendChild(tocLink);
          tocList.appendChild(tocItem);
      });
      
      tocContainer.appendChild(tocList);
  }
  ```
- [ ] Добавить контейнер в `templates/blog/post_detail.html`:
  ```django
  <div class="col-lg-3 d-none d-lg-block">
      <nav id="table-of-contents" class="sticky-top pt-4">
          <h5>Содержание</h5>
      </nav>
  </div>
  ```

**Референс:** `doc/samples/assets/js/menu.js` (генерация TOC)

### 6. Главный файл main.js — инициализация

- [ ] Создать файл `static/js/main.js`
- [ ] Реализовать инициализацию:
  ```javascript
  document.addEventListener('DOMContentLoaded', function() {
      console.log('Инициализация frontend модулей');
      
      // Проверяем наличие markdown контента
      const markdownContent = document.querySelector('.markdown-content');
      if (!markdownContent) {
          console.log('Markdown контент не найден на странице');
          return;
      }
      
      // Инициализируем модули
      enableFullscreenImages();
      addCodeCopyButtons();
      initMediaPlayers();
      generateTableOfContents();
      
      console.log('Frontend модули инициализированы');
  });
  ```

**Референс:** `doc/samples/assets/js/main.js:1-24`

### 7. Подключение скриптов в base.html

- [ ] Открыть `templates/base.html`
- [ ] Добавить перед закрывающим `</body>`:
  ```django
  <!-- Статические JS модули -->
  <script src="{% static 'js/fullscreen-images.js' %}"></script>
  <script src="{% static 'js/code-copy.js' %}"></script>
  <script src="{% static 'js/media-players.js' %}"></script>
  <script src="{% static 'js/table-of-contents.js' %}"></script>
  <script src="{% static 'js/main.js' %}"></script>
  ```
- [ ] Убедиться, что `{% load static %}` в начале файла

### 8. Тестирование фуллскрин изображений

- [ ] Открыть пост с изображениями
- [ ] Кликнуть на изображение
- [ ] Проверить:
  - ✅ Оверлей появляется на весь экран
  - ✅ Изображение центрировано и масштабировано корректно
  - ✅ Клик на оверлей закрывает его
  - ✅ Курсор меняется на pointer при наведении на изображение
- [ ] Проверить на мобильном (адаптивность)

### 9. Тестирование кнопок копирования

- [ ] Открыть пост с code blocks
- [ ] Проверить:
  - ✅ Кнопка "Copy" отображается в правом верхнем углу
  - ✅ Клик копирует код в буфер обмена
  - ✅ Иконка меняется на "скопировано" (зеленая галочка)
  - ✅ Через 3 секунды иконка возвращается
- [ ] Проверить вставку из буфера (Ctrl+V)

### 10. Тестирование медиаплееров

- [ ] Создать тестовый пост с `<video>` и `<audio>`:
  ```markdown
  <video src="/static/video/test.mp4"></video>
  <audio src="/static/audio/test.mp3"></audio>
  ```
- [ ] Открыть пост на сайте
- [ ] Проверить:
  - ✅ Plyr UI отображается
  - ✅ Кнопки воспроизведения, паузы, громкости работают
  - ✅ Слайдер прогресса функционален
  - ✅ Настройки скорости доступны (0.5x - 2x)
  - ✅ Фуллскрин работает для видео
- [ ] Проверить на мобильном

### 11. Тестирование генерации оглавления

- [ ] Открыть архитектурный пост (много заголовков)
- [ ] Проверить:
  - ✅ Оглавление генерируется автоматически
  - ✅ H2 заголовки выровнены влево
  - ✅ H3 заголовки имеют отступ
  - ✅ Клик на пункт оглавления скроллит к заголовку
  - ✅ Оглавление sticky (прилипает при скролле)
- [ ] Проверить на планшете/десктопе (на мобильном скрыто)

## Результаты

✅ **Что получим:**
- Фуллскрин просмотр изображений с адаптивным масштабированием
- Кнопки копирования кода с визуальным фидбеком
- Plyr.io плееры для видео и аудио
- Автоматическое оглавление из H2/H3 заголовков
- Модульная JS архитектура (легко расширять)

## Проблемы и решения

### Проблема: Clipboard API не работает на HTTP
**Решение:** Работает только на HTTPS или localhost. В продакшн использовать HTTPS.

### Проблема: Plyr не инициализируется
**Решение:** Проверить, что CDN загружен и `typeof Plyr !== 'undefined'`

### Проблема: Оглавление не появляется
**Решение:** Проверить наличие `#table-of-contents` в шаблоне

## Чеклист готовности к Phase 2.8

- [ ] Все 5 JS файлов созданы
- [ ] CSS стили для фуллскрин и кнопок добавлены
- [ ] Plyr CDN подключен
- [ ] Скрипты подключены в `base.html`
- [ ] Фуллскрин изображений работает
- [ ] Копирование кода работает
- [ ] Медиаплееры инициализируются
- [ ] Оглавление генерируется

**Следующая фаза:** 2.8 — Финальная полировка и документация
