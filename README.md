# Empório da Música — AI Engineer Challenge

Python customer-support agent project for the Artefact technical challenge.
This checkout implements **US-01: Project Foundation** and **US-02: Architecture
and Contracts**: an installable backend, development checks, the supplied catalog
snapshot, validated values, and substitution interfaces. Concrete agent execution,
database import/retrieval, chat orchestration, and HTTP remain later stories.

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
currently limited to Pydantic 2. The checked-in `backend/uv.lock` records resolved versions;
use `--locked` when installing an existing checkout.

## Quality checks

Run from the repository root:

```bash
uv run --directory backend --locked ruff check .
uv run --directory backend --locked ruff format --check .
uv run --directory backend --locked mypy src tests
uv run --directory backend --locked pytest
uv build --project backend
```

`--directory backend` deliberately changes the working directory so every tool
uses `backend/pyproject.toml` and resolves `src` and `tests` correctly. `--project`
selects a project without changing the command's working directory.

Contract tests validate chat/catalog values, derived fields, independent typed
fakes, and dependency boundaries without network or database access. Strict mypy
covers source and tests, including those fakes. The packaging smoke test imports
the installed distribution in an isolated Python
subprocess outside the source tree, without AWS configuration or provider imports.
Build outputs are ignored under `backend/dist/`.

To check the wheel with runtime dependencies only (POSIX shell):

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

The project uses one Python package with `uv_build` and no root uv workspace.
Pydantic 2 supplies frozen models with unknown inputs forbidden. The accepted
[ADR-0001](docs/adr/0001-modular-monolith-and-dependency-boundaries.md) describes
module responsibilities, dependency direction, and tradeoffs.

### Current application contracts

| Contract | Behavior |
| --- | --- |
| `ChatRequest` / `ChatResponse` | Trimmed nonblank `message` / `answer`; message maximum 4,000 characters. |
| `ProductSearchQuery` | Optional `category` / `product_name`, inclusive `min_price_centavos` / `max_price_centavos`, `available_only=True`, limit 10 (maximum 20). |
| `ProductSummary` | Product/category IDs and names, integer-centavo price, stock quantity, status, and derived availability. |
| `ProductSearchResult` | Immutable product tuple, total matches before limiting, and derived truncation. |
| `AgentExecutor.run` | Async single-message execution port returning ChatResponse. |
| `ProductRepository.search` | Synchronous typed catalog search port. |
| `ChatService.chat` | Async application interface only; implementation belongs to US-06. |

Contracts and errors live in `emporio_music_backend.contracts`; ports and the
application entry-point interface live in `ports` and `application`. No provider
or HTTP objects cross these boundaries. Integer fields reject booleans, fractions,
and numeric strings. Negative prices/stock, inverted bounds, blank filters, unknown
statuses, and inconsistent totals are rejected. Availability requires active
status and positive stock; computed availability/truncation are output-only.

The future repository must combine supplied filters, normalize category/name case
and accents, match names by literal substring, and sort by price then product ID.
Unknown categories/names return no matches, never an unrestricted search. Named
lookups may explicitly disable `available_only` to inspect unavailable products.
These are contract semantics; filtering itself is US-03 work. No-match results are
normal data. Operational failures have transport-neutral configuration,
provider-unavailable, timeout, retrieval, and execution error categories; contract
validation retains Pydantic ValidationError.

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
