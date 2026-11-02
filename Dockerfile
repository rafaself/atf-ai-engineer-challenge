FROM node:22-bookworm-slim AS frontend-build

WORKDIR /app/apps/frontend
COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci
COPY apps/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend-build

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/
ENV UV_PROJECT_ENVIRONMENT=/app/apps/backend/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./apps/backend/
COPY apps/backend/src/ ./apps/backend/src/
COPY apps/backend/scripts/ ./apps/backend/scripts/
RUN uv sync --project apps/backend --locked --no-dev --extra policy-rag

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/data/benchmark-cache/hf \
    PATH=/app/apps/backend/.venv/bin:$PATH
WORKDIR /app/apps/backend

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /home/app --create-home app

COPY --from=backend-build /app/apps/backend/.venv/ /app/apps/backend/.venv/
COPY --from=backend-build /app/apps/backend/src/ ./src/
COPY --from=backend-build /app/apps/backend/scripts/ ./scripts/
COPY --from=backend-build /app/apps/backend/pyproject.toml /app/apps/backend/uv.lock ./
COPY --from=frontend-build /app/apps/frontend/dist/ /app/apps/frontend/dist/
COPY data/ /app/data/

RUN mkdir -p /app/data/policy-indexes /app/data/benchmark-cache/hf \
    && chown -R app:app /app/data
USER app

RUN python -c "from pathlib import Path; from emporio_music_backend.paths import DATA_DIRECTORY, PROJECT_ROOT; assert PROJECT_ROOT == Path('/app'); assert (DATA_DIRECTORY / 'products.csv').is_file(); probe = DATA_DIRECTORY / '.container-path-smoke'; probe.write_text('ok', encoding='utf-8'); assert probe.read_text(encoding='utf-8') == 'ok'; probe.unlink()"

EXPOSE 8000
CMD ["uvicorn", "emporio_music_backend.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
