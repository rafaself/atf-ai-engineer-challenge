FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/apps/frontend
COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS python-build

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/emporio_music/pyproject.toml ./packages/emporio_music/pyproject.toml
COPY packages/emporio_music/src/ ./packages/emporio_music/src/
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src/ ./apps/api/src/
COPY apps/cli/pyproject.toml ./apps/cli/pyproject.toml
RUN uv sync --project apps/api --package emporio-music-api --locked \
    --no-dev --extra policy-rag --no-editable

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    EMPORIO_MUSIC_DATA_DIR=/app/data \
    EMPORIO_MUSIC_FRONTEND_DIR=/app/apps/frontend/dist \
    HF_HOME=/app/data/benchmark-cache/hf \
    PATH=/app/.venv/bin:$PATH
WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /home/app --create-home app

COPY --from=python-build /app/.venv/ /app/.venv/
COPY --from=frontend-build /app/apps/frontend/dist/ /app/apps/frontend/dist/
COPY scripts/ /app/scripts/
COPY data/ /app/data/

RUN mkdir -p /app/data/catalog /app/data/operations /app/data/conversations \
        /app/data/policies/policy-indexes /app/data/policies/policy-benchmark-indexes \
        /app/data/benchmark-cache/hf \
    && chown -R app:app /app/data
USER app

RUN python -c "from pathlib import Path; import emporio_music; from emporio_music.paths import DATA_DIRECTORY; assert DATA_DIRECTORY == Path('/app/data'); assert Path(emporio_music.__file__).resolve().is_relative_to(Path('/app/.venv')); assert (DATA_DIRECTORY / 'catalog' / 'products.csv').is_file(); probe = DATA_DIRECTORY / '.container-path-smoke'; probe.write_text('ok', encoding='utf-8'); assert probe.read_text(encoding='utf-8') == 'ok'; probe.unlink()"

EXPOSE 8000
CMD ["uvicorn", "emporio_music_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
