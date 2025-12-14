"""
Команда для регенерации слагов постов с использованием транслитерации.

Использование:
    python manage.py regenerate_slugs
"""

from django.core.management.base import BaseCommand
from transliterate import slugify
from blog.models import Post


class Command(BaseCommand):
    """
    Management-команда для регенерации слагов у всех постов.

    Использует транслитерацию для корректной обработки кириллицы.
    """

    help = "Регенерирует слаги у всех постов с использованием транслитерации кириллицы"

    def add_arguments(self, parser):
        """
        Добавляет аргументы командной строки.
        """
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать изменения без их применения",
        )

    def handle(self, *args, **options):
        """
        Основная логика команды.
        """
        dry_run = options["dry_run"]

        posts = Post.objects.all()
        updated_count = 0
        skipped_count = 0

        self.stdout.write(self.style.SUCCESS(f"Найдено постов: {posts.count()}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Режим dry-run: изменения не будут сохранены")
            )

        for post in posts:
            new_slug = slugify(post.title)

            if post.slug != new_slug:
                self.stdout.write(f'Пост #{post.id}: "{post.title}"')
                self.stdout.write(f"  Старый слаг: {post.slug}")
                self.stdout.write(self.style.SUCCESS(f"  Новый слаг:  {new_slug}"))

                if not dry_run:
                    # Проверяем уникальность нового слага
                    if Post.objects.filter(slug=new_slug).exclude(pk=post.pk).exists():
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ⚠ Слаг "{new_slug}" уже существует! Пропускаем...'
                            )
                        )
                        skipped_count += 1
                        continue

                    post.slug = new_slug
                    post.save(update_fields=["slug"])
                    updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f"Пост #{post.id}: слаг не изменился")
                )
                skipped_count += 1

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run завершен. Запустите без --dry-run для применения изменений."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Обновлено слагов: {updated_count}")
            )
            self.stdout.write(self.style.WARNING(f"○ Пропущено: {skipped_count}"))
