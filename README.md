# Empório da Música — AI Engineer Challenge

Python customer-support agent project for the Artefact technical challenge.
This checkout implements **US-01: Project Foundation** only: an installable backend
package, development checks, and the supplied catalog snapshot. The agent, database
import, and HTTP API will be implemented in later Sprint 1 stories.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python
3.12. The package supports Python 3.12 and later; `backend/.python-version` selects
3.12 for a consistent development baseline. Setup was validated with uv 0.13.4 and
Python 3.12.15.

Run from the repository root:

```bash
uv sync --project backend --locked
uv run --directory backend python -c "import emporio_music_backend"
```

The environment is created at `backend/.venv`. Development tools live in the
`dev` dependency group and are installed by default. Production dependencies are
currently empty. The checked-in `backend/uv.lock` records the resolved versions;
use `--locked` when installing an existing checkout.

## Quality checks

Run from the repository root:

```bash
uv run --directory backend --locked ruff check .
uv run --directory backend --locked ruff format --check .
uv run --directory backend --locked mypy src
uv run --directory backend --locked pytest
uv build --project backend
```

`--directory backend` deliberately changes the working directory so every tool
uses `backend/pyproject.toml` and resolves `src` and `tests` correctly. `--project`
selects a project without changing the command's working directory.

The packaging smoke test imports the installed distribution in an isolated Python
subprocess outside the source tree, without AWS configuration or provider imports.
Build outputs are ignored under `backend/dist/`.

To check the wheel without development dependencies (POSIX shell):

```bash
wheel_check_dir=$(mktemp -d)
uv venv --python 3.12 "$wheel_check_dir/.venv"
uv pip install --python "$wheel_check_dir/.venv/bin/python" \
  backend/dist/emporio_music_backend-0.1.0-py3-none-any.whl
(cd "$wheel_check_dir" && .venv/bin/python -I -c \
  "import emporio_music_backend; from importlib.metadata import version; print(version('emporio-music-backend'))")
```

The disposable directory can be removed after verification.

## Repository structure

| Directory | Responsibility |
| --- | --- |
| `backend/` | Installable Python package, tests, and development tooling. |
| `frontend/` | Placeholder for a later sprint; no JavaScript toolchain. |
| `data/` | Unmodified product/category CSVs, provenance, and checksums. |
| `docs/` | Placeholder for validated decisions and later interaction examples. |

## Configuration and data

`.env.example` documents future configuration only; no runtime loader exists yet.
The provider preference is Bedrock in `us-east-1`, initially
`amazon.nova-micro-v1:0`, or another validated low-cost feasible model. Model access
and tool calling have **not** been validated in US-01. Future integration will use
the standard AWS credential chain; no credentials are required for setup or tests.

`DATABASE_PATH` is a future path relative to the repository root. No database is
created by the bootstrap. No API startup or agent execution command exists yet.

Only products and categories have been copied. See [data provenance](data/README.md)
for SHA-256 verification. These files are an imported-source snapshot, not a live
inventory service. Ingestion, availability filtering, pricing, and promotions are
not implemented yet. Customer/order datasets remain outside this story.

## Decisions and follow-up

The project starts with one Python package using `uv_build`, no root uv workspace,
and no runtime dependencies. This keeps installation reproducible without adding
application abstractions before US-02. Sprint 1 will build a modular monolith with
typed boundaries, SQLite retrieval, provider configuration, and an API.

Later work must document architecture/retrieval/prompting decisions and include
real example conversations. Policy answers, order access, persistent conversation
history, promotion calculations, frontend delivery, and deployment packaging are
outside the current foundation story.

## Development workflow and coding assistants

Use `type(scope): message` commits with the related issue referenced in the body.
Link each published commit from its issue, open a focused PR, and report checks
that actually ran. Preserve an incremental history and respect the challenge's
submission cutoff; no deadline is assumed here.

OpenAI Codex assisted with challenge/issue analysis, implementation planning,
bootstrap files and tests, validation commands, and GitHub issue/PR updates.
Implementation choices and actual check results remain reviewable in the PR.
