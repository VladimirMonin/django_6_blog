.PHONY: setup migrate run test check lint

setup:
	uv sync --frozen

migrate:
	uv run python manage.py migrate

run:
	uv run python manage.py runserver

test:
	uv run pytest -q

check:
	uv run python manage.py check

lint:
	uv run python manage.py check