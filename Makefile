.PHONY: build prepare-data prepare-policy rebuild-policy up down check \
	check-python check-frontend

build:
	docker compose build app

prepare-data:
	docker compose run --rm app python -m emporio_music.prepare

prepare-policy:
	docker compose run --rm app python -m emporio_music.prepare_policy_index --allow-download

rebuild-policy:
	docker compose run --rm app python -m emporio_music.prepare_policy_index --allow-download --rebuild

up:
	docker compose up --detach app

down:
	docker compose down

check: check-python check-frontend

check-python:
	uv sync --project apps/api --package emporio-music-api --locked --group dev --extra policy-rag
	uv run --project apps/api --package emporio-music-api --locked ruff check packages/emporio_music/src apps/api/src apps/cli/src scripts tests conftest.py
	uv run --project apps/api --package emporio-music-api --locked ruff format --check packages/emporio_music/src apps/api/src apps/cli/src scripts tests conftest.py
	MYPYPATH=apps/cli/src uv run --project apps/api --package emporio-music-api --locked mypy packages/emporio_music/src apps/api/src apps/cli/src apps/cli/tests scripts tests conftest.py
	uv run --project apps/api --package emporio-music-api --locked pytest tests
	uv sync --project apps/cli --package emporio-music-cli --locked --group dev --extra policy-rag
	uv run --project apps/cli --package emporio-music-cli --locked pytest apps/cli/tests
	uv build --project packages/emporio_music
	uv build --project apps/api
	uv build --project apps/cli

check-frontend:
	npm --prefix apps/frontend ci
	npm --prefix apps/frontend test
	npm --prefix apps/frontend run lint
	npm --prefix apps/frontend run typecheck
	npm --prefix apps/frontend run build
