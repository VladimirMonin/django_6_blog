# Медиа-записи, плееры и таймкоды

`Post.content_type` задаёт тип публичной записи:

- `article` — обычная статья;
- `video` — видео с HTML5 video player;
- `audio` — аудио с HTML5 audio player;
- `podcast` — подкаст с audio player и отдельным бейджем.

## Источник основного медиа

Плеер берёт источник в таком порядке:

1. `Post.media_url`, если указан внешний URL;
2. первый прикреплённый `PostMedia` подходящего типа.

Для `video` нужен video-файл. Для `audio` и `podcast` нужен audio-файл.

Если медиа-пост импортирует локальный `![[file.mp4]]` или `![[file.opus]]`, этот файл становится primary media, а standalone embed удаляется из Markdown body, чтобы на detail page был ровно один player.

## Обложки

Обложка задаётся во frontmatter:

```yaml
cover: cover.webp
```

Поддерживаются простые пути, Obsidian embeds и Markdown image syntax. Обложка должна быть изображением внутри `assets_dir`. Первый image `PostMedia` используется как cover в карточках.

Если у video-поста нет cover, карточка показывает проектный video placeholder. Это нормальное состояние и его нужно проверять отдельно от карточек с обложкой.

## Timecodes block

Таймкоды пишутся в Markdown отдельным fenced block:

````markdown
```timecodes
00:00 Вступление
01:23 — Главная мысль
1:02:03 | Ответы на вопросы
```
````

Импорт:

1. удаляет `timecodes` block из Markdown body;
2. парсит строки в `Post.timecodes`;
3. для `video`, `audio`, `podcast` строго валидирует формат до записи в БД;
4. рендерит кнопки таймкодов на detail page.

Поддерживаемые форматы времени:

- `MM:SS Название`;
- `H:MM:SS Название`.

Секунды должны быть `00..59`; минуты в часовом формате — `00..59`. Некорректная строка должна останавливать импорт.

## UI таймкодов

Таймкоды — собственный компонент проекта, а не Bootstrap outline-кнопки. Визуально они должны совпадать с карточной системой блога:

- мягкая карточка панели;
- тёплый yellow accent;
- time-pill для времени;
- hover и active state;
- читаемый label;
- доступный focus-visible state.

Кнопка таймкода должна проматывать ближайший audio/video player к `data-seek-seconds` и выставлять active state.

## Проверки для медиа-слайсов

Минимум для изменений в этой зоне:

```bash
uv run pytest blog/test_content_types_timecodes.py -q
uv run pytest blog/test_obsidian_import.py blog/test_importer_metadata_links.py -q
uv run python manage.py check
git diff --check
```

Для UI-изменений дополнительно:

- browser smoke на video detail;
- browser smoke на podcast/audio detail;
- проверка `currentTime` после клика по таймкоду;
- проверка, что на detail page ровно один `<video>` или `<audio>`;
- WebP-кропы, если пользователь просил визуальное подтверждение.
