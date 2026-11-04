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
    HF_HOME=/opt/emporio-music/hf \
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
COPY data/ /opt/emporio-music/data/

RUN mkdir -p /app/data /opt/emporio-music/hf \
    && chown -R app:app /app/data /opt/emporio-music
USER app

# Prepare all supplied data and pinned local embeddings in the image. A fresh
# runtime volume needs neither manual setup nor a model download.
RUN EMPORIO_MUSIC_DATA_DIR=/opt/emporio-music/data python -m emporio_music.prepare \
    && EMPORIO_MUSIC_DATA_DIR=/opt/emporio-music/data python -m emporio_music.prepare_policy_index --allow-download

EXPOSE 8000
ENTRYPOINT ["python", "-m", "emporio_music.container_start"]
CMD ["uvicorn", "emporio_music_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
