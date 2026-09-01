# Техническая готовность сайта к поиску и нейросетевым ответам

## Назначение и границы

Это исполнимый план улучшения обнаружения и понятности публичного блога для обычного поиска и систем с веб-поиском. Он не обещает индексацию, цитирование, трафик или обучение модели: эти результаты зависят от внешних индексов, их закрытых алгоритмов и времени.

Важно различать три независимых результата:

1. **Поисковая индексация** — поисковик обнаружил и может показать URL.
2. **Цитирование в ответе нейросети** — система с веб-поиском выбрала конкретный фрагмент как источник ответа.
3. **Возможное обучение будущей модели** — публичная страница была получена, прошла неизвестные фильтры и могла попасть в будущий набор данных. Получение страницы ботом не доказывает ни набор данных, ни знание модели, ни рекомендацию автора.

План опирается на принятый исследовательский аудит с 17 официальными источниками. В этой карточке они не запрашивались повторно: сетевые проверки, регистрация домена, вызовы API и изменение поведения сайта не входят в её границы. Перед любым изменением production-политики ботов ссылки и названия ботов нужно перепроверить по официальным страницам.

## Что уже есть и что ещё не готово

Текущая кодовая основа исправна и подходит для первого этапа:

- публичные списки, detail, sitemap и фиды ограничены опубликованными, не soft-deleted постами;
- `robots.txt` разрешает общий обход, закрывает `/admin/` и `/api/`, ссылается на sitemap;
- есть `sitemap.xml`, RSS и Atom; `lastmod` поста берётся из `updated_at`;
- главная, `/about/`, detail и series отдают серверный HTML с одним абсолютным canonical без query; detail также отдаёт RSS/Atom alternate links, Open Graph/Twitter и безопасный JSON-LD `@graph`;
- `/about/` — каноническая страница автора: видимые подписи автора ведут на неё, а detail показывает реальные даты создания и обновления;
- detail уже использует `ETag` и `Last-Modified`, а условный запрос может вернуть `304`.
- `/llms.txt` реализован как компактный UTF-8 `text/plain` v2-указатель: только основные публичные страницы и не более 20 последних опубликованных, не soft-deleted записей с короткими описаниями и ссылками на HTML/Markdown;
- `/post/<slug>.md` реализован из единственного публичного `Post.content`: только published/not-deleted запись, title/description/site author/published/modified/canonical метаданные, UTF-8 `text/markdown`, canonical HTML `Link`, ETag и `Last-Modified`; HTML detail ссылается на Markdown и `/llms.txt`.
- есть локальное fail-open наблюдение `crawler_observation`: после ответа оно
  записывает одну JSON-строку только для заявленных User-Agent кандидатов
  OpenAI, Anthropic, Perplexity, Google, Bing и Brave. Все такие записи имеют
  `verified_identity=false` и не являются подтверждением crawler.

Это подтверждается текущими `blog/views.py`, `blog/discovery.py`, `blog/sitemaps.py`, `blog/feeds.py`, `config/urls.py`, `templates/blog/post_detail.html`, `blog/test_seo.py` и `blog/test_ai_discovery.py`. Это не утверждение о текущем состоянии внешних поисковых индексов.

Первый этап закрыл canonical без query для главной, `/about/`, detail и series; связал автора с `/about/`; вывел реальные даты detail и связный JSON-LD-граф. Нельзя выдумывать профили, регалии, даты или внешние ссылки ради разметки.

## Последовательность работ

### Этап 1. Основная структура и достоверные данные

Цель — сделать каждый индексируемый HTML-URL понятным самостоятельным документом. Google рассматривает AI-функции как часть Search; отдельная «разметка для AI» не заменяет обычную доступность страницы, индексирование и полезный контент.[1][2]

Технические требования:

1. Для главной, `/about/`, detail и series вывести один абсолютный canonical URL без query-параметров. Фильтры и пагинация остаются рабочими SSR URL, но не становятся самостоятельными canonical-копиями.
2. Сделать `/about/` канонической публичной страницей автора только на уже видимых и подтверждаемых фактах. В карточках и detail автор должен быть обычной ссылкой на ту же страницу; `Article.author.url` должен совпадать с ней.
3. Сформировать JSON-LD из Python-структур, а не строками в шаблонах: `WebSite` для главной, `ProfilePage` и `Person` для `/about/`, для публикации — её существующий тип (`Article`, `VideoObject` или `AudioObject`) с `mainEntityOfPage`, `publisher` и `BreadcrumbList`. Разметка обязана соответствовать видимому тексту; она не является гарантией citation.[14][15]
4. Показать реальные `datePublished` и `dateModified` на detail и использовать те же данные в разметке. Не обновлять дату ради видимости: sitemap должен сообщать только фактическое существенное обновление.[13]
5. Добавлять только смысловые внутренние ссылки: существующие related posts и series navigation остаются основой; не строить автоматическую ссылочную сетку и не создавать искусственные страницы.
6. Не ослаблять действующие контракты: публичны только `status=published` и `deleted_at IS NULL`; JSON-LD остаётся script-safe; HTML остаётся полезным без JavaScript; media detail продолжает иметь ровно один основной плеер.

Минимальные проверки этапа:

- canonical без query для всех четырёх поверхностей;
- JSON-LD round-trip и защита от закрытия `<script>` пользовательским текстом;
- совпадение видимого автора, `author.url` и `/about/`;
- `BreadcrumbList`, реальные даты и отсутствие утечки draft/soft-deleted постов;
- одинаковая публичная `200`-доступность для обычного клиента и запроса с заявленным User-Agent; это не проверка подлинности бота;
- действующие `ETag` и `Last-Modified` дают `304` при условном запросе;
- синхронизация `instructions/SEO.meta.instructions.md` и `doc/seo.md` в той же функциональной карточке.

**Критерий перехода:** целевые тесты, `uv run python manage.py check`, полный `pytest -q` для изменённого среза и `git diff --check` проходят; ручная проверка HTML подтверждает один canonical и согласованную видимую разметку.

**Откат:** вернуть только код, шаблоны, тесты и документацию этого этапа к предыдущему проверенному состоянию. Не менять данные публикаций, robots policy или внешние кабинеты как часть отката.

### Этап 2. Небольшой локальный эксперимент `llms.txt` и Markdown

`llms.txt` v2 — формирующееся соглашение для навигации, а не стандарт поисковой индексации. Google не использует его как специальный сигнал; его наличие не обещает ни появление в ответе, ни доступ для обучения.[2][9][10]

Технические требования:

1. Реализован компактный динамический `/llms.txt`: основные публичные страницы и максимум 20 последних published/not-deleted публикаций с короткими описаниями и HTML/Markdown-ссылками. Он не является копией всего сайта.
2. Markdown-представление каждой публичной публикации берётся из того же сохранённого `Post.content`, что служит источником HTML. Оно соблюдает тот же фильтр published/not-deleted и включает canonical HTML URL, заголовок, site author и даты без отдельной копии контента.
3. HTML detail содержит только стандартизованные связи `rel="alternate" type="text/markdown"` на Markdown и `rel="describedby"` на `/llms.txt`; альтернативный текст вручную не создаётся.
4. Markdown и `/llms.txt` отдают корректные `Content-Type`, `ETag` и `Last-Modified`; они не включают private API, черновики, медиа-файлы, токены, скрытые поля или Obsidian frontmatter.
5. Не создавать `llms-full.txt` с растущим полным корпусом. Такой файл не является требованием спецификации и создаст дублирование, большой ответ и риск расхождения текста.

Метрика эксперимента: в течение восьми недель после запуска считать реальные запросы к `/llms.txt` и Markdown-URL, отдельные уникальные клиентские источники, статусы и переходы на Markdown. Нулевой спрос — допустимый результат, а не причина выдумывать пользу.

**Критерий перехода:** маршрут, заголовки, public-only фильтр, canonical-согласованность и conditional GET покрыты тестами; HTML и Markdown реально берутся из одного поста; `git diff --check` проходит.

**Откат:** убрать новые маршруты и link relations одним срезом. Основной HTML, sitemap, фиды и обычный поиск должны продолжать работать без них.

### Этап 3. Наблюдение за обходом, а не вера в User-Agent

`robots.txt` — договорённость с добросовестным crawler, а не защита данных; специфические группы User-Agent не должны случайно обходить общие запреты.[16] Заявленный User-Agent можно подделать, поэтому решение о WAF или доступе нельзя принимать только по строке заголовка.

Технические требования:

1. Локальный `CrawlerObservationMiddleware` записывает одну JSON-строку после
   ответа только для заявленных User-Agent кандидатов: `provider`, `purpose`,
   `remote_ip`, `method`, path без query, `status`, `elapsed_ms`, `user_agent`
   и неизменный `verified_identity=false`. Он не пишет query string, cookies,
   `Authorization` или body; ошибка классификации/логирования fail-open и не
   меняет HTTP-ответ.
2. Это не identity verification: middleware не выполняет DNS/IP-проверку,
   signature/CDN-WAF validation или allowlist и не называет ни один запрос
   verified crawler. Если такая проверка когда-либо потребуется, сначала нужно
   заново сверить официальную документацию оператора и его опубликованные
   IP-диапазоны; сама проверка остаётся отдельным решением владельца и отдельным
   безопасным срезом.
3. Использовать измеримые знаменатели:
   - crawler coverage = уникальные приоритетные публичные URL, которые посетил подтверждённый поисковый crawler / все приоритетные публичные URL;
   - crawler error rate = `(403 + 429 + 5xx) / все crawler-запросы`;
   - freshness lag = время от существенной публикации или обновления до следующего подтверждённого обхода.
4. Отдельно проверить canonical-поведение фильтров и пагинации, чтобы параметры не создавали crawl trap.
5. Текущую минимальную общую группу `robots.txt` сохранить до отдельного решения владельца. Не добавлять явные `Allow` для search-ботов: при специфических правилах надо повторять все нужные запреты.

Политика training crawler — отдельный выбор владельца: либо сохранить максимальную обнаруживаемость, либо после свежей проверки официальных политик запретить известные training-токены, не блокируя поисковые токены. В частности, `GPTBot` и `OAI-SearchBot`, а также `ClaudeBot` и `Claude-SearchBot` — не один и тот же контроль; `Google-Extended` имеет отдельный компромисс и не заменяет `Googlebot`.[5][6][11][12] `PerplexityBot` также надо оценивать по его собственной официальной политике, а не по чужим спискам.[7]

**Критерий перехода:** источник и поля локального лога документированы,
ошибки имеют знаменатель, а local-only candidate observation не зависит от
одного User-Agent для identity verification и не записывает tokens, query,
cookies, authorization или содержимое публикаций. Полный remote IP не должен
переноситься из access log в долговременный отчёт.

**Откат:** выключить новый логгер или отчёт, сохранив прежние безопасные access logs; не менять robots policy автоматически по единичному запросу.

### Этап 4. Внешние регистрации — позднее и только с владельцем

Google Search Console и Bing Webmaster Tools не входят в реализацию кода. Их выполняют после этапов 1–3 с отдельным разрешением владельца и доступом к домену.

1. В Google Search Console: подтвердить Domain property (предпочтительно DNS TXT), отправить sitemap, проверить четыре приоритетных URL и сохранить исходные показатели Indexing, Search и доступного отчёта Generative AI.[3]
2. В Bing Webmaster Tools: импортировать проверку из Google или подтвердить домен, отправить sitemap, проверить те же URL и сохранить начальные данные AI Performance.[4]
3. Вручную проверить две точные публикации в Brave; это диагностический сигнал, а не доказательство видимости в Claude.
4. У OpenAI, Anthropic и Perplexity нет действия «зарегистрировать домен» в рамках их опубликованных crawler-интерфейсов: здесь контролируются доступ публичных URL и политика их ботов, а реальный трафик подтверждается identity-проверкой.[5][6][7][17]

**IndexNow — отдельный owner gate.** Он требует отдельного ключа, публичного точного key-файла и явного разрешения на live-submit. Реализация возможна только после этого: ключ хранится в env/secret storage, не печатается в ошибках и логах; запросы охватывают публикацию, существенное обновление и удаление, имеют ограниченные повторы и идемпотентность. Протокол уведомляет участвующие поисковые системы об URL, но не гарантирует обход, индексирование или ответ ChatGPT/Claude/Perplexity.[8]

**Проверка и ограничение отката:** подтверждение домена и отправка sitemap — внешние действия, которые нельзя честно «откатить» локальным тестом. При ошибке остановить новые submit, зафиксировать фактический статус в кабинете и не удалять ключ или property без отдельного решения владельца. Нельзя называть эти действия выполненными, пока владелец не увидел их результат в соответствующем кабинете.

## Что не делать

- Не обещать попадание в Google, Bing, ChatGPT, Claude, Perplexity или training dataset.
- Не считать crawler request доказательством citation, referral, обучения или знания модели.
- Не подменять регистрацию Google/Bing локальным тестом или командой без доступа владельца.
- Не создавать `llms-full.txt`, сотни AI-only страниц, фальшивые даты, schema, которая расходится с HTML, или несуществующие профили автора.
- Не использовать `robots.txt` как контроль доступа к черновикам, API или персональным данным.
- Не вызывать IndexNow, не создавать ключ и не менять robots policy без отдельного разрешения владельца.

## Признак завершения всей программы

Программа считается технически готовой не по красивому «AI visibility score», а когда выполнены все применимые локальные стадии, внешние действия отдельно подтверждены владельцем, а отчёт явно показывает: что измерено, какой знаменатель использован, какие URL цитируются или обходятся и что остаётся непроверенным. Отсутствие citations, переходов или признаков обучения остаётся допустимым и честно зафиксированным результатом.

## Источники принятого исследования

1. Google Search Central — [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
2. Google Search Central — [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
3. Google Search Central — [Generative AI performance reports in Search Console](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)
4. Microsoft Bing — [AI Performance in Bing Webmaster Tools](https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview)
5. OpenAI Developers — [OpenAI crawlers and user agents](https://developers.openai.com/api/docs/bots)
6. Anthropic Help Center — [Web crawling and crawler controls](https://support.anthropic.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
7. Perplexity Docs — [Perplexity Crawlers](https://docs.perplexity.ai/docs/resources/perplexity-crawlers)
8. IndexNow — [Protocol documentation](https://www.indexnow.org/documentation)
9. llms.txt — [Proposal](https://llmstxt.org/)
10. llms.txt — [Changes in v2](https://llmstxt.org/changes.html)
11. Google for Developers — [Google common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers)
12. Google for Developers — [Google-Extended](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers#google-extended)
13. Google Search Central — [Build and submit a sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
14. Google Search Central — [Structured data introduction](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data)
15. Google Search Central — [Article structured data](https://developers.google.com/search/docs/appearance/structured-data/article)
16. IETF — [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309)
17. OpenAI Help Center — [Publishers and developers FAQ](https://help.openai.com/en/articles/12627856-publishers-and-developers-faq)
