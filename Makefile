.PHONY: build prepare-data prepare-policy up down check check-backend check-frontend

build:
	docker compose build app

prepare-data:
	docker compose run --rm app python -m emporio_music_backend.prepare

prepare-policy:
	docker compose run --rm app python -m scripts.policy_benchmark.run --model e5 --index --allow-download --output-dir /tmp/policy-rag-bootstrap

up:
	docker compose up --detach app

down:
	docker compose down

check: check-backend check-frontend

check-backend:
	uv sync --project apps/backend --locked --group dev --extra policy-rag
	uv run --directory apps/backend --locked --extra policy-rag ruff check .
	uv run --directory apps/backend --locked --extra policy-rag ruff check ../cli/src ../cli/tests
	uv run --directory apps/backend --locked --extra policy-rag ruff format --check .
	uv run --directory apps/backend --locked --extra policy-rag ruff format --check ../cli/src ../cli/tests
	uv run --directory apps/backend --locked --extra policy-rag mypy src tests scripts
	uv run --directory apps/backend --locked --extra policy-rag mypy ../cli/src ../cli/tests
	uv run --directory apps/backend --locked --extra policy-rag pytest
	PYTHONPATH=../cli/src uv run --directory apps/backend --locked --extra policy-rag pytest ../cli/tests
	uv build --project apps/cli

check-frontend:
	npm --prefix apps/frontend ci
	npm --prefix apps/frontend run lint
	npm --prefix apps/frontend run typecheck
	npm --prefix apps/frontend run build
