# **Архитектурный Проект: Технический Блог Следующего Поколения с Гибридным Поиском и Иерархической Структурой (Декабрь 2025\)**

## **1\. Введение: Эволюция RAG и Императивы 2025 Года**

К декабрю 2025 года парадигма построения систем Retrieval-Augmented Generation (RAG) претерпела фундаментальный сдвиг. Эпоха простых "наивных" RAG-систем, полагающихся на примитивное разделение текста (chunking) и простой векторный поиск, завершилась. Индустрия столкнулась с жесткими ограничениями первых поколений: потерей контекста при разбиении кода, неспособностью векторных моделей захватывать точную терминологию (лексический провал) и игнорированием структурной иерархии технической документации.  
Для проектирования технического блога корпоративного уровня требуется архитектура, способная обрабатывать гетерогенный контент — смесь глубокой технической прозы, исполняемого кода, математических формул и структурированных данных. Решение этой задачи требует интеграции лучших в своем классе инструментов: **Chonkie** для интеллектуальной обработки данных, **PostgreSQL 18.1** в качестве надежного фундамента хранения с поддержкой асинхронного ввода-вывода, и **pgvector 0.8.0+** для реализации передовых стратегий гибридного поиска.  
В данном отчете представлен исчерпывающий анализ архитектуры технического блога, который не просто "ищет по словам", а понимает структуру инженерного знания. Мы рассмотрим, как переход на асинхронный I/O в Postgres 18 меняет правила игры для высоконагруженных векторных систем, как использование разреженных векторов (sparsevec) позволяет отказаться от внешних поисковых движков типа Elasticsearch, и почему библиотека Chonkie стала де\-факто стандартом для Python-разработчиков RAG-систем.

### **1.1. Проблема "Потери Середины" и Технический Контекст**

Традиционные подходы к RAG часто страдают от феномена "Lost in the Middle" (потеря контекста в середине), но в техническом блоге эта проблема проявляется иначе. Здесь потеря контекста означает разрыв между определением функции и её использованием, или между архитектурной диаграммой и описывающим её текстом. Плоское векторное пространство не способно отразить вложенность понятий, характерную для инженерных дисциплин (Библиотека $\\rightarrow$ Модуль $\\rightarrow$ Класс $\\rightarrow$ Метод).  
Предлагаемая архитектура решает эту проблему через **Иерархический Гибридный Поиск**, комбинируя семантическую мощь плотных векторов (dense vectors) с точностью разреженных векторов (sparse vectors) и структурной навигацией через ltree.

## ---

**2\. Слой Ингестии: Высокопроизводительная Обработка с Chonkie**

Фундамент любой поисковой системы — качество данных на входе. В 2025 году библиотека **Chonkie** (версия 1.0.4 и выше) вытеснила тяжеловесные фреймворки вроде LangChain и LlamaIndex в задачах предварительной обработки текста благодаря своей специализации, легковесности и производительности.1

### **2.1. Философия Chonkie: "No-Nonsense" Подход**

Chonkie позиционируется как библиотека, которая "просто работает". В отличие от универсальных комбайнов, она фокусируется исключительно на задаче разбиения текста (chunking) и делает это с экстремальной эффективностью.  
**Ключевые преимущества для архитектуры блога:**

1. **Легковесность:** Базовая установка занимает всего \~15-21 МБ против 80-170 МБ у конкурентов. Это критично для развертывания в serverless-окружениях (например, AWS Lambda), где "холодный старт" и размер пакета имеют значение.3  
2. **Скорость:** Благодаря оптимизированным алгоритмам токенизации (на базе Rust) и агрессивному кэшированию, Chonkie демонстрирует 33-кратное ускорение при токен-ориентированном чанкинге по сравнению с аналогами.1  
3. **Модульность:** Библиотека позволяет устанавливать только необходимые компоненты (например, pip install chonkie\[semantic\]), избегая замусоривания среды зависимостями.3

### **2.2. Стратегии Чанкинга для Полиглотичного Контента**

Технический блог — это сложный мультимодальный документ. Применение единой стратегии разбиения (например, "разбить по 500 символов") приведет к катастрофическим результатам: разрыву Markdown-таблиц, нарушению синтаксиса кода и потере смысла заголовков. Chonkie предлагает набор специализированных чанкеров, которые мы объединяем в единый **Маршрутизируемый Пайплайн (Routing Pipeline)**.

#### **2.2.1. TokenChunker и SentenceChunker: Базовые Примитивы**

Для простых текстовых описаний и метаданных используются TokenChunker и SentenceChunker.

* **TokenChunker:** Разбивает текст на фиксированные окна токенов (например, 512). Идеально подходит для моделей эмбеддинга с жестким контекстным окном. Chonkie поддерживает все основные токенизаторы (OpenAI tiktoken, HuggingFace tokenizers), что позволяет выравнивать границы чанков с "словарем" модели.1  
* **SentenceChunker:** Использует эвристики для определения границ предложений, гарантируя, что мысль не обрывается на полуслове. В Chonkie этот процесс ускорен в 2 раза по сравнению с конкурентами.1

#### **2.2.2. RecursiveChunker: Сохранение Структуры Markdown**

Для основного тела статей мы используем RecursiveChunker. Этот алгоритм работает иерархически: сначала пытается разбить текст по двойным переносам строк (параграфы), затем по одиночным, затем по предложениям.

* **Специфика Markdown:** Для технического блога критически важно настроить этот чанкер на распознавание заголовков (\#, \#\#, \#\#\#). Chonkie позволяет задать пользовательские правила разделения, гарантируя, что чанк никогда не "перепрыгнет" через заголовок раздела. Это сохраняет локальный контекст: вектор, полученный из раздела "Настройка PostgreSQL", не будет загрязнен текстом из соседнего раздела "Настройка Nginx".5

#### **2.2.3. CodeChunker: Синтаксически-Ориентированное Разбиение**

Самым важным компонентом для технического блога является **CodeChunker**. Традиционные сплиттеры рассматривают код как текст, часто разрезая функции посередине. Это делает полученный чанк бесполезным для LLM, так как теряется сигнатура функции или закрывающие скобки.

* **Механизм работы:** CodeChunker в Chonkie использует парсинг абстрактного синтаксического дерева (AST) (через интеграцию с tree-sitter или аналогичными механизмами). Он понимает структуру более 100 языков программирования.  
* **Результат:** Разбиение происходит по логическим блокам — классам, функциям, методам. Если функция слишком велика, она разбивается по вложенным блокам (циклам, условиям), но с сохранением контекста (например, добавлением комментариев с именем родительской функции).7  
* **Автоопределение языка:** Версия 1.0.4+ поддерживает режим language="auto", что упрощает пайплайн ингестии.8

#### **2.2.4. SemanticChunker и LateChunker: Продвинутые Методики**

Для сложных аналитических статей, где границы темы не всегда совпадают с абзацами, мы применяем семантические стратегии.

* **SemanticChunker:** Анализирует косинусное сходство между соседними предложениями. Если сходство падает ниже порога (threshold), создается новый чанк. Это позволяет группировать предложения по смыслу, а не по форматированию. Chonkie использует "running mean pooling" для ускорения этого процесса.4  
* **LateChunker:** Реализует передовой метод "позднего чанкинга" (Late Chunking), предложенный Jina AI. Вместо того чтобы сначала разбивать текст, а потом векторизовать куски (теряя глобальный контекст), этот метод прогоняет через модель весь документ (используя long-context модели), получает эмбеддинги для каждого токена, и только потом агрегирует их в чанки. Это обеспечивает феноменальное качество поиска, так как каждый чанк "знает" о содержании всего документа.7 В нашей архитектуре это используется для "золотого фонда" статей — фундаментальных руководств, где качество поиска приоритетнее скорости индексации.

#### **2.2.5. SDPMChunker и SlumberChunker (Agentic)**

Chonkie также предлагает экспериментальные, но мощные методы:

* **SDPMChunker (Semantic Double-Pass Merge):** Двухпроходный алгоритм, который сначала разбивает, а потом склеивает семантически близкие чанки, сглаживая шум.1  
* **SlumberChunker (Agentic):** Использует LLM (через интерфейс Genie) для принятия решений о границах разбиения. Хотя это медленно и дорого, для критически важных документов это дает качество, сравнимое с ручной разметкой экспертом.7

### **2.3. Архитектура Пайплайна Ингестии (Chonkie Pipeline)**

Мы организуем процесс обработки данных как направленный ациклический граф (DAG) операций, используя API Pipeline в Chonkie.  
**Этапы Пайплайна:**

1. **Fetcher (Загрузчик):** Компонент FileFetcher или UrlFetcher забирает исходные Markdown-файлы из git-репозитория блога.  
2. **Chef (Препроцессор):** MarkdownChef очищает текст, удаляет лишние метаданные (frontmatter), извлекает таблицы для отдельной обработки (TableChunker) и нормализует ссылки на изображения.7  
3. **Router (Маршрутизатор):**  
   * Блоки кода $\\rightarrow$ CodeChunker.  
   * Таблицы $\\rightarrow$ TableChunker (разбивает по строкам, сохраняя заголовки колонок в каждом чанке).11  
   * Текст $\\rightarrow$ RecursiveChunker или SemanticChunker (в зависимости от типа статьи).  
4. **Refinery (Обогащение):**  
   * OverlapRefinery: Добавляет перекрытие (overlap) между чанками (например, 50 токенов), чтобы исключить потерю информации на границах.8  
   * EmbeddingsRefinery: Немедленно вызывает модель эмбеддинга (например, model2vec для скорости или OpenAI для качества) и обогащает объект чанка вектором. Это позволяет сохранять в БД уже готовый к поиску объект.2  
5. **Handshake (Сохранение):** Финальный этап — PgvectorHandshake. Этот компонент абстрагирует логику подключения к БД и вставки данных, используя COPY для массовой загрузки, что критично при первичной индексации большого архива.2

## ---

**3\. Фундамент Данных: PostgreSQL 18.1**

Выбор **PostgreSQL 18.1** (актуальная версия на декабрь 2025 года) обусловлен не просто привычкой, а радикальными архитектурными изменениями, которые превращают эту реляционную СУБД в высокопроизводительный векторный движок.

### **3.1. Асинхронный Ввод-Вывод (Asynchronous I/O)**

Самым значимым нововведением версии 18 является полнофункциональная подсистема асинхронного I/O (AIO).13  
Проблема синхронного I/O в векторном поиске:  
Векторный поиск по индексу HNSW (Hierarchical Navigable Small World) порождает паттерн доступа к памяти, напоминающий "случайные блуждания" (random walks). В предыдущих версиях Postgres, если нужная страница индекса отсутствовала в shared\_buffers, процесс backend блокировался в ожидании чтения с диска. При миллионах векторов индекс не помещается в RAM, и система упиралась в IOPS диска, простаивая CPU.  
Революция AIO в Postgres 18:  
С включенным параметром io\_method \= 'io\_uring' (на Linux ядрах 5.10+), Postgres 18 может отправлять запросы на чтение страниц превентивно. Пока CPU обрабатывает дистанцию до текущего узла графа, контроллер диска уже извлекает соседние узлы.

* **Результат:** Ускорение "холодного" векторного поиска в 2-3 раза.  
* **Мониторинг:** Новое представление pg\_aios позволяет в реальном времени видеть очередь асинхронных запросов, что дает DBA инструменты для тонкой настройки.13

### **3.2. UUIDv7: Локальность Данных и Индексация**

PostgreSQL 18 внедрил нативную поддержку **UUIDv7** — идентификаторов, содержащих временную метку.13  
Почему это важно для блога?  
В RAG-системах часто требуется фильтрация по времени ("найти статьи за последний месяц"). Использование UUIDv7 в качестве первичного ключа (chunk\_id) означает, что данные в B-Tree индексе и в куче (heap) физически упорядочены по времени создания. Это обеспечивает локальность данных (data locality): статьи, написанные в одно время, лежат на диске рядом. Это снижает количество "грязных" страниц при записи и уменьшает I/O при чтении диапазонов времени, что идеально синергирует с новым AIO движком.

### **3.3. Виртуальные Генерируемые Колонки**

В версии 18 генерируемые колонки (Generated Columns) стали виртуальными по умолчанию.13 Это позволяет нам хранить JSON-метаданные в одной колонке metadata (тип jsonb) и создавать виртуальные типизированные колонки (например, author\_id, category) для индексации, не дублируя физические данные на диске. Это экономит место, что важно при хранении миллионов векторов.

### **3.4. Оптимизация Запросов и Обслуживания**

* **B-tree Skip Scan:** Позволяет эффективно искать уникальные значения в индексах (например, список всех тегов в блоге) без полного сканирования, что ускоряет построение фасетных фильтров в поиске.13  
* **Улучшенный pg\_stat\_io:** Детализированная статистика ввода-вывода позволяет точно отследить, какую нагрузку создает именно векторный поиск, отделяя его от обычных транзакций.14

## ---

**4\. Векторный Движок: pgvector 0.8.0+**

Расширение **pgvector** к концу 2025 года (версия 0.8.1) достигло зрелости, позволяющей конкурировать с специализированными векторными БД (Pinecone, Qdrant). Ключевыми нововведениями стали поддержка разреженных векторов, итеративное сканирование и квантование.

### **4.1. Революция Разреженных Векторов (sparsevec)**

Главная слабость плотных векторов (dense vectors) — неспособность находить точные совпадения (exact match) для специфических терминов (коды ошибок, ID транзакций, редкие аббревиатуры). Раньше для этого использовали Full Text Search (tsvector), но он ограничен лемматизацией и не учитывает семантический вес слов.  
**pgvector 0.8.0 вводит тип sparsevec**.15

* **Суть:** Это вектор огромной размерности (например, 30,000 — размер словаря), в котором 99% значений — нули. Хранятся только ненулевые индексы и их веса.  
* **Применение:** Это позволяет реализовать алгоритмы **Learned Sparse Retrieval** (например, **SPLADE**). В отличие от BM25, SPLADE "расширяет" запрос. Если пользователь ищет "Postgres", модель SPLADE добавит в разреженный вектор слова "SQL", "Database", "Relational" с определенными весами, даже если их нет в запросе.  
* **Хранение:** sparsevec эффективно сжат. Он поддерживает до 1000 ненулевых элементов, чего более чем достаточно для чанка текста.17

### **4.2. Итеративное Сканирование Индекса (Iterative Index Scans)**

Это решение одной из самых болезненных проблем векторного поиска в SQL — проблемы **пост-фильтрации**.18  
Сценарий провала:  
Пользователь ищет "конфигурация памяти" с фильтром category \= 'Frontend'. Индекс HNSW находит топ-100 ближайших векторов. Но так как запрос про "память", 99 из них оказываются из категории Backend или Kernel. После применения фильтра WHERE category \= 'Frontend' в результате остается 0 или 1 запись.  
Решение в pgvector 0.8:  
Итеративное сканирование позволяет индексу HNSW "общаться" с планировщиком запросов. Если фильтр отбрасывает найденные кандидаты, сканирование графа автоматически продолжается (resume), пока не будет набрано нужное количество (LIMIT) валидных записей.

* **Настройка:** Параметр hnsw.iterative\_scan можно установить в relaxed\_order (быстрее, допускает небольшое нарушение порядка сортировки) или strict\_order (строгое соблюдение дистанции). Для блога relaxed\_order является предпочтительным.21

### **4.3. Квантование и Тип halfvec**

Для оптимизации памяти (RAM) используется тип halfvec (16-битные числа с плавающей точкой).15 Это уменьшает размер индекса в 2 раза с минимальной потерей точности (recall). Для векторов размерности 1536 (OpenAI) или 1024 (Cohere) это существенная экономия. pgvector также поддерживает бинарное квантование (bit), но для точности технического поиска halfvec является оптимальным компромиссом.

### **4.4. Индексация HNSW: Тонкая Настройка**

Для гибридного поиска мы создаем два индекса:

1. **Dense Index:** HNSW на колонке dense\_vector (косинусное расстояние). Параметры: m=16, ef\_construction=64 (дефолт) или выше для лучшего качества.15  
2. **Sparse Index:** HNSW на колонке sparse\_vector (L2 distance или Inner Product). Да, pgvector позволяет строить граф HNSW даже для разреженных векторов, что делает поиск по ключевым словам молниеносным.16

## ---

**5\. Архитектурный Паттерн: Иерархический Гибридный Поиск**

Мы объединяем вышеописанные технологии в единую схему **Parent-Child Document Retrieval** с поддержкой иерархии через ltree.

### **5.1. Схема "Родитель-Ребенок" (Parent-Child)**

Технический контекст требует окружения. Найденный сниппет кода (Child Chunk) часто бесполезен без объяснения, которое находится в начале раздела (Parent Chunk).  
**Реализация:**

* **Ингестия:** Chonkie разбивает статью на крупные блоки (Parents) и мелкие блоки (Children).  
* **Векторизация:** Эмбеддинги строятся только для Children (для максимальной точности поиска).  
* **Связь:** В БД каждый Child ссылается на parent\_id.  
* **Поиск:** Векторный поиск находит Child, но возвращает контент Parent. Это дает LLM полный контекст для генерации ответа.12

### **5.2. Управление Иерархией с ltree**

Технический блог имеет структуру таксономии: Backend.Database.Postgres.Index. Расширение ltree позволяет эффективно моделировать эту структуру.  
**SQL Схема:**

| Таблица | Описание |
| :---- | :---- |
| **documents** | Хранит метаданные статьи. Первичный ключ doc\_id (UUIDv7). Колонка path типа ltree хранит путь в таксономии. |
| **chunks** | Хранит сами фрагменты. chunk\_id (UUIDv7). Ссылается на doc\_id и parent\_chunk\_id. Содержит векторы. |

**Пример DDL:**

SQL

CREATE TABLE chunks (  
    chunk\_id uuid DEFAULT uuid\_generate\_v7() PRIMARY KEY,  
    doc\_id uuid REFERENCES documents(doc\_id) ON DELETE CASCADE,  
    parent\_id uuid REFERENCES chunks(chunk\_id),  
    content text,  
    dense\_vec halfvec(768),       \-- Плотный вектор (Model2Vec/OpenAI)  
    sparse\_vec sparsevec(10000),  \-- Разреженный вектор (SPLADE)  
    metadata jsonb  
);

CREATE INDEX ON chunks USING gist (path); \-- Для быстрого поиска по иерархии  
CREATE INDEX ON chunks USING hnsw (dense\_vec vector\_cosine\_ops);  
CREATE INDEX ON chunks USING hnsw (sparse\_vec sparsevec\_ip\_ops);

Использование индекса GIST для ltree позволяет выполнять запросы вида "Найти все чанки в разделе Database и его подразделах" (WHERE path \<@ 'Backend.Database') с высокой скоростью, отсекая ненужные ветви поиска до начала сканирования векторов.23

### **5.3. Алгоритм Гибридного Поиска: Reciprocal Rank Fusion (RRF)**

Для объединения результатов плотного (семантического) и разреженного (лексического) поиска мы используем алгоритм RRF. Он не требует сложной калибровки весов, так как работает с рангами, а не с абсолютными значениями скоров.24  
**SQL-запрос Гибридного Поиска (PostgreSQL 18.1):**

SQL

WITH semantic AS (  
    SELECT chunk\_id,   
           RANK() OVER (ORDER BY dense\_vec \<=\> $1) as rank  
    FROM chunks  
    WHERE path \<@ $2 \-- Фильтр по иерархии ltree  
    LIMIT 60  
),  
lexical AS (  
    SELECT chunk\_id,   
           RANK() OVER (ORDER BY sparse\_vec \<\#\> $3) as rank  
    FROM chunks  
    WHERE path \<@ $2  
    LIMIT 60  
)  
SELECT   
    COALESCE(s.chunk\_id, l.chunk\_id) as id,  
    (  
        COALESCE(1.0 / (60 \+ s.rank), 0.0) \+   
        COALESCE(1.0 / (60 \+ l.rank), 0.0)  
    ) as rrf\_score  
FROM semantic s  
FULL OUTER JOIN lexical l ON s.chunk\_id \= l.chunk\_id  
ORDER BY rrf\_score DESC  
LIMIT 10;

Этот запрос использует Common Table Expressions (CTE) для независимого поиска, а затем объединяет их. Благодаря оптимизатору Postgres 18 и AIO, оба подзапроса могут выполняться параллельно.25

## ---

**6\. Эксплуатация и Развертывание**

### **6.1. Настройка Инфраструктуры**

Для продакшн-окружения рекомендуется использовать Docker-контейнер на базе официального образа pgvector/pgvector:pg17 (или pg18, когда выйдет официальный образ).

* **Память:** shared\_buffers следует установить в 25-40% от RAM. Критически важен параметр maintenance\_work\_mem — его увеличение ускоряет построение индексов HNSW.17  
* **Параллелизм:** Увеличить max\_parallel\_maintenance\_workers для ускорения создания индексов при деплое.17

### **6.2. Мониторинг и Observability**

Использование представления pg\_stat\_io в Postgres 18 обязательно для отслеживания эффективности кэша. Если мы видим высокий процент evictions в контексте векторных индексов, необходимо увеличить RAM или перейти на halfvec.  
Chonkie предоставляет встроенные средства логирования и колбэки для мониторинга процесса чанкинга, что позволяет выявлять "проблемные" статьи, которые парсятся некорректно (например, из\-за сломанной разметки Markdown).7

### **6.3. Будущее: Агентские RAG и Cross-Encoders**

В качестве шага "Day 2" архитектура предусматривает добавление этапа **Reranking** (переранжирования). После получения топ-10 результатов из RRF, легкая модель Cross-Encoder (например, через Chonkie Refinery или внешний сервис) может переоценить релевантность, прочитав полный текст пар "запрос-документ". Это повышает точность (precision) на 15-30% ценой небольшой задержки.25

## ---

**7\. Заключение**

Предложенная архитектура "Chonkie \+ Postgres 18.1 \+ pgvector" является "золотым стандартом" для построения систем поиска по техническим знаниям на конец 2025 года. Она устраняет фундаментальные недостатки предыдущих поколений RAG, предоставляя:

1. **Понимание кода:** Благодаря CodeChunker и AST-парсингу.  
2. **Структурную целостность:** Через RecursiveChunker и ltree иерархию.  
3. **Гибридную точность:** Комбинацией sparsevec (SPLADE) и плотных векторов через RRF.  
4. **Высокую производительность:** За счет AIO в Postgres 18 и оптимизаций Chonkie.

Это решение позволяет создать технический блог, который не просто хранит статьи, а служит интеллектуальным ассистентом для инженеров, мгновенно находящим точные ответы в гигабайтах документации.

### **Сводная Таблица Технологического Стека**

| Компонент | Технология | Версия | Функция в архитектуре |
| :---- | :---- | :---- | :---- |
| **Ingestion** | **Chonkie** | v1.0.4+ | Полиглотичный чанкинг (Текст/Код), Pipeline-оркестрация, создание Sparse/Dense векторов. |
| **СУБД** | **PostgreSQL** | v18.1 | Хранение, AIO движок, UUIDv7, JSONB метаданные. |
| **Vector Ext** | **pgvector** | v0.8.1+ | Индексация HNSW, разреженные векторы (sparsevec), halfvec, итеративный поиск. |
| **Иерархия** | **ltree** | Native | Таксономическая фильтрация и Scoped Search. |
| **Fusion** | **SQL RRF** | \- | Математическое объединение рангов семантического и лексического поиска. |

Данный отчет служит готовым техническим заданием (Blueprint) для реализации системы.

#### **Источники**

1. Introducing Chonkie: The Lightweight RAG Chunking Library | Deeplearning.fr, дата последнего обращения: декабря 16, 2025, [https://deeplearning.fr/introducing-chonkie-the-lightweight-rag-chunking-library/](https://deeplearning.fr/introducing-chonkie-the-lightweight-rag-chunking-library/)  
2. CHONK docs with Chonkie — The lightweight ingestion library for fast, efficient and robust RAG pipelines \- GitHub, дата последнего обращения: декабря 16, 2025, [https://github.com/chonkie-inc/chonkie](https://github.com/chonkie-inc/chonkie)  
3. chonkie \- PyPI, дата последнего обращения: декабря 16, 2025, [https://pypi.org/project/chonkie/0.5.1/](https://pypi.org/project/chonkie/0.5.1/)  
4. Launch HN: Chonkie (YC X25) – Open-Source Library for Advanced Chunking \- Hacker News, дата последнего обращения: декабря 16, 2025, [https://news.ycombinator.com/item?id=44225930](https://news.ycombinator.com/item?id=44225930)  
5. Fix Broken Context in RAG with Tensorlake \+ Chonkie, дата последнего обращения: декабря 16, 2025, [https://www.tensorlake.ai/blog/tensorlake-chonkie-rag](https://www.tensorlake.ai/blog/tensorlake-chonkie-rag)  
6. Reintroducing Chonkie \- The no-nonsense Chunking library : r/Rag \- Reddit, дата последнего обращения: декабря 16, 2025, [https://www.reddit.com/r/Rag/comments/1jzigjb/reintroducing\_chonkie\_the\_nononsense\_chunking/](https://www.reddit.com/r/Rag/comments/1jzigjb/reintroducing_chonkie_the_nononsense_chunking/)  
7. Open Source \- Chonkie Documentation, дата последнего обращения: декабря 16, 2025, [https://docs.chonkie.ai/common/open-source](https://docs.chonkie.ai/common/open-source)  
8. Changelog \- Chonkie Documentation, дата последнего обращения: декабря 16, 2025, [https://docs.chonkie.ai/oss/changelog](https://docs.chonkie.ai/oss/changelog)  
9. Easy Late-Chunking With Chonkie | Towards AI, дата последнего обращения: декабря 16, 2025, [https://towardsai.net/p/machine-learning/easy-late-chunking-with-chonkie](https://towardsai.net/p/machine-learning/easy-late-chunking-with-chonkie)  
10. A Comparative Analysis of Data Pre-processing Frameworks for Retrieval-Augmented Generation: Chonkie, Docling, and Unstructured \- Thinkdeeply, дата последнего обращения: декабря 16, 2025, [https://www.thinkdeeply.ai/post/a-comparative-analysis-of-data-pre-processing-frameworks-for-retrieval-augmented-generation-chonkie](https://www.thinkdeeply.ai/post/a-comparative-analysis-of-data-pre-processing-frameworks-for-retrieval-augmented-generation-chonkie)  
11. Table Chunker \- Chonkie Documentation, дата последнего обращения: декабря 16, 2025, [https://docs.chonkie.ai/oss/chunkers/table-chunker](https://docs.chonkie.ai/oss/chunkers/table-chunker)  
12. The Beauty of Parent-Child Chunking. Graph RAG Was Too Slow for Production, So This Parent-Child RAG System was useful \- Reddit, дата последнего обращения: декабря 16, 2025, [https://www.reddit.com/r/Rag/comments/1mtcvs7/the\_beauty\_of\_parentchild\_chunking\_graph\_rag\_was/](https://www.reddit.com/r/Rag/comments/1mtcvs7/the_beauty_of_parentchild_chunking_graph_rag_was/)  
13. PostgreSQL 18 New Features: What's New and Why It Matters \- Neon, дата последнего обращения: декабря 16, 2025, [https://neon.com/postgresql/postgresql-18-new-features](https://neon.com/postgresql/postgresql-18-new-features)  
14. PostgreSQL 18 Released\!, дата последнего обращения: декабря 16, 2025, [https://www.postgresql.org/about/news/postgresql-18-released-3142/](https://www.postgresql.org/about/news/postgresql-18-released-3142/)  
15. Getting started with pgvector \- Nile Documentation, дата последнего обращения: декабря 16, 2025, [https://www.thenile.dev/docs/ai-embeddings/vectors/pg\_vector](https://www.thenile.dev/docs/ai-embeddings/vectors/pg_vector)  
16. pgvector/pgvector: Open-source vector similarity search for Postgres \- GitHub, дата последнего обращения: декабря 16, 2025, [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector)  
17. The pgvector extension \- Neon Docs, дата последнего обращения: декабря 16, 2025, [https://neon.com/docs/extensions/pgvector](https://neon.com/docs/extensions/pgvector)  
18. PostgreSQL as a Vector Database: A Complete Guide \- Airbyte, дата последнего обращения: декабря 16, 2025, [https://airbyte.com/data-engineering-resources/postgresql-as-a-vector-database](https://airbyte.com/data-engineering-resources/postgresql-as-a-vector-database)  
19. pgvector 0.8.0 Released\! \- PostgreSQL, дата последнего обращения: декабря 16, 2025, [https://www.postgresql.org/about/news/pgvector-080-released-2952/](https://www.postgresql.org/about/news/pgvector-080-released-2952/)  
20. Announcing: pgvector 0.8.0 released and available on Nile, дата последнего обращения: декабря 16, 2025, [https://www.thenile.dev/blog/pgvector-080](https://www.thenile.dev/blog/pgvector-080)  
21. Supercharging vector search performance and relevance with pgvector 0.8.0 on Amazon Aurora PostgreSQL | AWS Database Blog, дата последнего обращения: декабря 16, 2025, [https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/](https://aws.amazon.com/blogs/database/supercharging-vector-search-performance-and-relevance-with-pgvector-0-8-0-on-amazon-aurora-postgresql/)  
22. Parent-Child Chunking in LangChain for Advanced RAG | by Seahorse | Medium, дата последнего обращения: декабря 16, 2025, [https://medium.com/@seahorse.technologies.sl/parent-child-chunking-in-langchain-for-advanced-rag-e7c37171995a](https://medium.com/@seahorse.technologies.sl/parent-child-chunking-in-langchain-for-advanced-rag-e7c37171995a)  
23. Documentation: 18: F.22. ltree — hierarchical tree-like data type \- PostgreSQL, дата последнего обращения: декабря 16, 2025, [https://www.postgresql.org/docs/current/ltree.html](https://www.postgresql.org/docs/current/ltree.html)  
24. Hybrid Search in PostgreSQL: The Missing Manual \- ParadeDB, дата последнего обращения: декабря 16, 2025, [https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)  
25. RAG Series \- Hybrid Search with Re-ranking \- dbi services, дата последнего обращения: декабря 16, 2025, [https://www.dbi-services.com/blog/rag-series-hybrid-search-with-re-ranking/](https://www.dbi-services.com/blog/rag-series-hybrid-search-with-re-ranking/)  
26. Hybrid Search \- Re-ranking and Blending Searches · SingleStore Self-Managed Documentation, дата последнего обращения: декабря 16, 2025, [https://docs.singlestore.com/db/v9.0/developer-resources/functional-extensions/hybrid-search-re-ranking-and-blending-searches/](https://docs.singlestore.com/db/v9.0/developer-resources/functional-extensions/hybrid-search-re-ranking-and-blending-searches/)  
27. The Ultimate Guide to using PGVector | by Intuitive Deep Learning | Medium, дата последнего обращения: декабря 16, 2025, [https://medium.com/@intuitivedl/the-ultimate-guide-to-using-pgvector-76239864bbfb](https://medium.com/@intuitivedl/the-ultimate-guide-to-using-pgvector-76239864bbfb)