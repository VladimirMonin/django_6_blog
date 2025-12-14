# Фаза 2.4: Подсветка синтаксиса и диаграммы (Highlight.js + Mermaid)

## Цель

Подключить Highlight.js для подсветки синтаксиса кода и Mermaid.js для рендеринга диаграмм через CDN, настроить темы, инициализацию и стилизацию.

## Контекст

После Phase 2.3 у нас есть чистый HTML с `<code class="language-X">` в базе данных. Теперь добавляем визуальную магию на фронтенде:

- **Highlight.js** — автоматически находит code blocks и раскрашивает их
- **Mermaid.js** — находит блоки с `language-mermaid` и рендерит диаграммы

**Философия:** Подключаем через CDN (без npm/webpack), минимальная настройка, максимальная эффектность для YouTube-контента.

**Документация:**
- Highlight.js: https://highlightjs.org/
- Mermaid.js: https://mermaid.js.org/

## Задачи

### 1. Выбор темы Highlight.js

- [ ] Открыть демо тем: https://highlightjs.org/demo
- [ ] Выбрать тему под дизайн проекта (белый фон, черные элементы, желтые акценты):
  - Рекомендуемые: `github`, `atom-one-light`, `stackoverflow-light`
  - Темная альтернатива: `github-dark`, `atom-one-dark`, `monokai`
- [ ] Запомнить название темы для CDN ссылки
- [ ] Проверить, что тема хорошо смотрится с желтыми акцентами

### 2. Подключение Highlight.js через CDN

- [ ] Открыть `templates/base.html`
- [ ] Найти блок `<head>` с CSS подключениями
- [ ] Добавить CDN ссылку на Highlight.js CSS (после Bootstrap):
  - Формат: `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/THEME_NAME.min.css`
  - Заменить `THEME_NAME` на выбранную тему
- [ ] Найти блок перед закрывающим `</body>` (после Bootstrap JS)
- [ ] Добавить CDN ссылку на Highlight.js JS:
  - `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js`
- [ ] Проверить версию (11.9.0 актуальна на декабрь 2024)

### 3. Инициализация Highlight.js

- [ ] В `templates/base.html` после подключения highlight.min.js
- [ ] Добавить скрипт инициализации в отдельном `<script>` блоке:
  - Вызвать `hljs.highlightAll()` после загрузки DOM
  - Использовать `document.addEventListener('DOMContentLoaded', ...)` или аналог
- [ ] Убедиться, что скрипт выполняется только на страницах с постами (опционально):
  - Можно добавить условие или запускать всегда (безопасно)

### 4. Тестирование Highlight.js

- [ ] Открыть любой пост с code block в браузере
- [ ] Открыть DevTools → Elements
- [ ] Проверить, что `<code>` элемент получил дополнительные классы от Highlight.js:
  - Например: `hljs`, `language-python`, `hljs-keyword`, `hljs-string`
- [ ] Убедиться, что код раскрашен:
  - Ключевые слова (if, def, return) — один цвет
  - Строки — другой цвет
  - Комментарии — третий цвет
- [ ] Проверить производительность:
  - Открыть Network tab, проверить время загрузки highlight.js (~50KB gzip)
  - Проверить Console на ошибки

### 5. Подключение Mermaid.js через CDN

- [ ] Открыть `templates/base.html`
- [ ] После Highlight.js JS добавить CDN ссылку на Mermaid:
  - `https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js`
  - Или использовать конкретную версию: `mermaid@10.9.0`
- [ ] Проверить актуальную версию на https://www.jsdelivr.com/package/npm/mermaid

### 6. Инициализация Mermaid.js

- [ ] В `templates/base.html` добавить скрипт инициализации Mermaid:
  - Вызвать `mermaid.initialize()` с настройками
  - Настроить тему: `theme: 'default'` или `'neutral'`
  - Настроить `startOnLoad: true` для автоматического рендеринга
- [ ] Альтернатива: использовать `mermaid.run()` после DOMContentLoaded
- [ ] Настроить безопасность: `securityLevel: 'loose'` (для админских постов безопасно)

### 7. Настройка Mermaid для работы с Markdown

- [ ] Убедиться, что в Phase 2.3 настроен `pymdownx.superfences`:
  - Расширение должно поддерживать custom fences
  - Блоки с `language-mermaid` должны рендериться как `<code class="language-mermaid">`
- [ ] Проверить конфигурацию Markdown в `blog/models.py`:
  - Добавить поддержку Mermaid в `superfences` (если еще не добавлено)
- [ ] Альтернатива: использовать `<div class="mermaid">` вместо `<code>`

### 8. Создание тестового поста с Mermaid диаграммой

- [ ] Открыть админку и создать новый пост
- [ ] Добавить Markdown с Mermaid диаграммой:
  - Простой пример: graph TD, flowchart, sequence diagram
  - Например: блок-схема процесса или UML диаграмма
- [ ] Сохранить пост
- [ ] Открыть пост на сайте
- [ ] Убедиться, что диаграмма отрисовалась корректно

### 9. Стилизация code blocks в style.css

- [ ] Открыть `static/css/style.css`
- [ ] Добавить стили для code blocks:
  - `.post-content pre` — обертка для блока кода
  - `.post-content code` — сам код
  - Настроить `border-radius`, `padding`, `background-color`
  - Добавить `overflow-x: auto` для горизонтального скролла
  - Настроить `font-family` (monospace)
- [ ] Добавить стили для inline кода:
  - `.post-content code:not(pre code)` — inline код
  - Легкий фон, padding, border-radius
- [ ] Добавить стили для Mermaid диаграмм:
  - `.post-content .mermaid` — обертка диаграммы
  - Центрирование, margin, возможно рамка

### 10. Настройка темной/светлой темы (опционально)

- [ ] Если планируется переключатель темы:
  - Добавить CSS переменные для цветов code blocks
  - Настроить `prefers-color-scheme` media query
  - Динамически менять тему Highlight.js через JS
- [ ] Если тема одна (светлая):
  - Убедиться, что выбранная тема Highlight.js сочетается с белым фоном
  - Проверить контраст текста (WCAG AA стандарт)

### 11. Добавление copy-button для code blocks (опционально)

- [ ] Создать файл `static/js/copy-code.js` (если нужен кастомный JS)
- [ ] Добавить кнопку "Копировать" в каждый code block:
  - Через JS добавить `<button>` внутри `<pre>`
  - Стилизовать кнопку (position: absolute, top-right)
  - Обработчик клика: `navigator.clipboard.writeText(code)`
- [ ] Альтернатива: использовать готовый плагин для Highlight.js
- [ ] Добавить иконку (Bootstrap Icons уже подключены)
- [ ] Добавить feedback: кнопка меняется на "Скопировано!" на 2 секунды

### 12. Оптимизация производительности

- [ ] Проверить размер загружаемых библиотек:
  - Highlight.js: ~50KB gzipped
  - Mermaid: ~150KB gzipped (тяжелее, но для диаграмм оправдано)
- [ ] Рассмотреть lazy loading:
  - Загружать Mermaid только если на странице есть диаграммы
  - Использовать `defer` атрибут для JS
- [ ] Проверить время инициализации в DevTools Performance

### 13. Тестирование на разных устройствах

- [ ] Открыть пост с кодом на десктопе:
  - Проверить отображение code blocks
  - Проверить горизонтальный скролл для длинных строк
- [ ] Открыть на планшете (через DevTools Responsive mode):
  - Убедиться, что code blocks не ломают layout
  - Проверить читаемость кода
- [ ] Открыть на мобильном:
  - Проверить, что код читаемый (может нужно уменьшить font-size)
  - Проверить скролл
- [ ] Проверить Mermaid диаграммы на всех размерах экрана

### 14. Проверка совместимости с HTMX

- [ ] Открыть список постов с HTMX подгрузкой
- [ ] Загрузить еще посты через "Загрузить еще" (HTMX)
- [ ] Убедиться, что Highlight.js подсвечивает новые code blocks:
  - Может потребоваться вызов `hljs.highlightAll()` после HTMX обновления
  - Использовать HTMX event: `htmx:afterSwap`
- [ ] Проверить Mermaid диаграммы в HTMX подгруженном контенте:
  - Вызвать `mermaid.run()` для новых элементов

## Результат

Полностью работающая система подсветки синтаксиса и диаграмм:

- Highlight.js подсвечивает code blocks автоматически
- Mermaid.js рендерит диаграммы из Markdown
- Красивые стили для code blocks (border-radius, padding, цвета)
- Copy-button для удобного копирования (опционально)
- Адаптивный дизайн (работает на мобильных)
- Совместимость с HTMX подгрузкой

## Следующий шаг

Phase 3: Расширенные возможности блога (категории, теги, комментарии)

## Возможные проблемы и решения

### Проблема 1: Highlight.js не раскрашивает код

**Причина:** Неправильная инициализация или CSS не загрузился.

**Решение:**

- Открыть DevTools Console, проверить ошибки JS
- Убедиться, что `hljs.highlightAll()` вызывается после DOMContentLoaded
- Проверить Network tab: CSS и JS загрузились (200 OK)
- Проверить, что code blocks имеют класс `language-X`

### Проблема 2: Mermaid диаграммы не рендерятся

**Причина:** Неправильная инициализация или формат блока.

**Решение:**

- Проверить Console на ошибки Mermaid
- Убедиться, что `mermaid.initialize()` вызывается
- Проверить HTML: блок должен быть `<code class="language-mermaid">` или `<div class="mermaid">`
- Проверить синтаксис диаграммы (возможна ошибка в Markdown)
- Попробовать простой пример: `graph TD; A-->B;`

### Проблема 3: Код ломает layout на мобильных

**Причина:** Длинные строки кода без горизонтального скролла.

**Решение:**

- Добавить в CSS: `pre { overflow-x: auto; }`
- Добавить `word-wrap: break-word;` для очень длинных слов (осторожно, может сломать код)
- Уменьшить `font-size` для мобильных через media query

### Проблема 4: HTMX подгруженный код не подсвечивается

**Причина:** Highlight.js запускается только при первой загрузке страницы.

**Решение:**

- Добавить обработчик HTMX события:
  - `htmx:afterSwap` — после вставки нового контента
  - Вызвать `hljs.highlightAll()` повторно
- Для Mermaid: вызвать `mermaid.run()` с селектором новых элементов

### Проблема 5: Copy-button не работает на HTTPS

**Причина:** `navigator.clipboard` требует HTTPS или localhost.

**Решение:**

- Для локальной разработки: использовать `localhost` вместо `127.0.0.1`
- Для production: обязательно HTTPS
- Альтернатива: использовать старый метод `document.execCommand('copy')`

## Проверочный чеклист

После завершения фазы убедитесь:

- [ ] Highlight.js подключен через CDN и работает
- [ ] Code blocks раскрашены корректно
- [ ] Mermaid.js рендерит диаграммы
- [ ] Стили code blocks соответствуют дизайну проекта
- [ ] Адаптивный дизайн работает на мобильных
- [ ] HTMX совместим с подсветкой (если используется)
- [ ] Console без ошибок JS
- [ ] Производительность приемлема (проверить DevTools)

## Дополнительная информация

### Языки поддерживаемые Highlight.js

Highlight.js поддерживает 190+ языков из коробки:

- **Популярные:** Python, JavaScript, TypeScript, Java, C++, C#, Ruby, PHP, Go
- **Web:** HTML, CSS, SCSS, SQL
- **Markup:** Markdown, YAML, JSON, XML
- **Shell:** Bash, PowerShell, Dockerfile
- **Специализированные:** Rust, Swift, Kotlin, Dart

Автоопределение языка работает хорошо, но лучше явно указывать через ` ```python `.

### Типы Mermaid диаграмм

Mermaid поддерживает множество типов диаграмм:

- **Flowchart** — блок-схемы (graph TD, graph LR)
- **Sequence** — диаграммы последовательности (sequenceDiagram)
- **Class** — UML диаграммы классов (classDiagram)
- **State** — диаграммы состояний (stateDiagram)
- **ER** — диаграммы сущность-связь (erDiagram)
- **Gantt** — диаграммы Ганта (gantt)
- **Pie** — круговые диаграммы (pie)
- **Git** — Git графы (gitGraph)

Отлично подходит для технической документации!

### Темы Highlight.js

Рекомендуемые светлые темы под дизайн проекта:

- **github** — классическая GitHub светлая (нейтральная, отличная читаемость)
- **stackoverflow-light** — светлая Stack Overflow (чистая, минималистичная)
- **atom-one-light** — светлая Atom (мягкие цвета)

Если захочешь темную:

- **github-dark** — классическая GitHub темная
- **atom-one-dark** — темная Atom (популярная в VSCode)
- **monokai** — классическая Monokai (контрастная)

Смена темы: просто замени `THEME_NAME` в CDN ссылке!
