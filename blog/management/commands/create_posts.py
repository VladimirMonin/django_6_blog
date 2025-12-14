"""
Management команда для создания постов из архитектурных документов.

Загружает реальные Markdown документы из doc/architecture/phase_1/
и создает из них посты для тестирования Markdown → HTML конвертации.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from blog.models import Post


class Command(BaseCommand):
    help = "Создает посты из архитектурных документов Phase 1"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Удалить существующие посты перед созданием новых",
        )

    def extract_title_from_markdown(self, content):
        """
        Извлекает заголовок из Markdown файла.

        Ищет первый H1 заголовок (# Заголовок) в начале файла.
        """
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def handle(self, *args, **options):
        # Путь к архитектурным документам относительно BASE_DIR
        docs_dir = Path(settings.BASE_DIR) / "doc" / "architecture" / "phase_1"

        if not docs_dir.exists():
            self.stdout.write(self.style.ERROR(f"❌ Директория не найдена: {docs_dir}"))
            return

        # Удаляем существующие посты если указан флаг --clear
        if options["clear"]:
            existing_count = Post.objects.count()
            if existing_count > 0:
                Post.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"🗑️  Удалено {existing_count} существующих постов."
                    )
                )

        # Получаем список markdown файлов (исключая README.md)
        md_files = sorted([f for f in docs_dir.glob("*.md") if f.name != "README.md"])

        if not md_files:
            self.stdout.write(
                self.style.WARNING("⚠️  Markdown файлы не найдены в директории.")
            )
            return

        created_posts = []
        skipped_posts = []

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n📚 Найдено {len(md_files)} архитектурных документов\n"
            )
        )

        # Создаем посты из документов
        for md_file in md_files:
            try:
                # Читаем содержимое файла
                content = md_file.read_text(encoding="utf-8")

                # Извлекаем заголовок из Markdown
                title = self.extract_title_from_markdown(content)

                if not title:
                    # Fallback: используем имя файла
                    title = md_file.stem.replace("_", " ").title()

                # Генерируем slug из имени файла (без расширения)
                slug = md_file.stem

                # Проверяем, существует ли пост с таким slug
                if Post.objects.filter(slug=slug).exists():
                    skipped_posts.append(f"{title} (slug уже существует)")
                    self.stdout.write(
                        self.style.WARNING(
                            f'⏭️  Пропущен: {title} (slug "{slug}" уже существует)'
                        )
                    )
                    continue

                # Создаем пост
                post = Post.objects.create(
                    title=title, slug=slug, content=content, is_published=True
                )

                created_posts.append(post)

                self.stdout.write(self.style.SUCCESS(f"✓ Создан: {post.title}"))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Ошибка при обработке {md_file.name}: {e}")
                )

        # Итоговая статистика
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS(f"\n✨ Успешно создано постов: {len(created_posts)}")
        )
        if skipped_posts:
            self.stdout.write(
                self.style.WARNING(f"⏭️  Пропущено постов: {len(skipped_posts)}")
            )
        self.stdout.write(f"📊 Всего постов в базе: {Post.objects.count()}\n")
