# Empório da Música — AI Engineer Challenge

Python customer-support agent project for the Artefact technical challenge.
This checkout implements **US-01 through US-08 (implementation; live acceptance deferred)**: an installable backend,
development checks, validated values/interfaces, and atomic catalog import with
read-only SQLite retrieval, an isolated Pydantic AI/Bedrock adapter, and a typed
product-search tool connected to the catalog repository.
Live Bedrock evidence is deferred until the user confirms a project AWS profile.
ChatService orchestrates stateless conversations behind `POST /api/chat`. See
[local API startup](docs/api.md) and [agent setup](docs/bedrock.md).

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
Pydantic, Pydantic AI with Bedrock support, boto3, FastAPI, and uvicorn. The checked-in `backend/uv.lock` records resolved versions;
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
| `docs/` | Architecture decisions, setup guides, and validation evidence. |

## Configuration and data

`.env.example` documents configuration; export values explicitly, without a dotenv loader.
The provider preference is Bedrock in `us-east-1`, initially
`amazon.nova-micro-v1:0`, or another validated low-cost feasible model. Model access
and tool calling have **not** been live-validated. The integration uses
the standard AWS credential chain; no credentials are required for setup or tests.

`DATABASE_PATH` documents the catalog path relative to the repository root; pass
that path explicitly to the importer below. The environment example is not loaded
automatically. See [local API startup](docs/api.md) for uvicorn and curl commands.

Only products and categories have been copied. See [data provenance](data/README.md)
for SHA-256 verification. These files are an imported-source snapshot, not a live
inventory service. Import and retrieval now implement availability and catalog-price
filtering. Promotion calculations and customer/order access remain outside scope.

### Import the catalog

From the repository root, run:

```bash
uv run --project backend --locked python -m \
  emporio_music_backend.infrastructure.catalog_import \
  --products data/products.csv \
  --categories data/categories.csv \
  --database data/catalog.sqlite3
```

Expected output: `Imported 9 categories and 65 products`. Every successful import
replaces the entire catalog atomically, refreshing changed rows and removing absent
products/categories. Validation failures leave an existing snapshot untouched and
do not create a database. Empty snapshots are rejected. Generated databases remain
ignored by Git. See [catalog behavior](docs/catalog.md) for validation, ownership,
schema compatibility, failure behavior, and the repository interface.

For a local retrieval example (no server or AWS calls):

```bash
uv run --project backend --locked python -c \
  "from pathlib import Path; from emporio_music_backend.contracts import ProductSearchQuery; from emporio_music_backend.infrastructure.sqlite_repository import SQLiteProductRepository; print(SQLiteProductRepository(Path('data/catalog.sqlite3')).search(ProductSearchQuery(category='violoes', max_price_centavos=100000)).model_dump_json())"
```

The budget search has 12 matches in the supplied snapshot; the default limit is
10, so truncation is reported. Use limit 20 to retrieve all 12.

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
| `ChatService.chat` / `ChatServicePort` | Concrete async orchestration and its structural interface; one 60-second default end-to-end deadline. |

Contracts and errors live in `emporio_music_backend.contracts`; ports and the
application entry-point interface live in `ports` and `application`. No provider
or HTTP objects cross these boundaries. Integer fields reject booleans, fractions,
and numeric strings. Negative prices/stock, inverted bounds, blank filters, unknown
statuses, and inconsistent totals are rejected. Availability requires active
status and positive stock; computed availability/truncation are output-only.

The repository combines supplied filters, normalizes category/name case
and accents, matches names by literal substring, and sorts by price then product ID.
Unknown categories/names return no matches, never an unrestricted search. Named
lookups may explicitly disable `available_only` to inspect unavailable products.
These semantics are implemented by SQLiteProductRepository. No-match results are
normal data. Operational failures have transport-neutral configuration,
provider-unavailable, timeout, retrieval, and execution error categories; contract
validation retains Pydantic ValidationError.

See [architecture and prompting rationale](docs/architecture.md),
[validation evidence](docs/validation.md), [pending real examples](docs/examples/README.md),
and [follow-up/submission requirements](docs/follow-up.md).
Policy-aware answers and operational-data-versus-policy routing remain follow-up work;
3–5 real conversations and live Bedrock validation are outstanding. Policy answers, order access, persistent conversation
history, promotion calculations, frontend delivery, and deployment packaging are
outside the current foundation story.

## Development workflow and coding assistants

Use `type(scope): message` commits with the related issue referenced in the body.
Link each published commit from its issue, open a focused PR, and report checks
that actually ran. Preserve an incremental history and respect the challenge's
submission cutoff; no deadline is assumed here.

OpenAI Codex assisted with challenge/issue analysis, implementation planning,
bootstrap files and tests, validation commands, and GitHub issue/PR updates.
Codex used the implement-work-item workflow for scoped delivery and domain-testing
guidance for risk-based tests. Tests, review findings/fixes, conventional issue-linked
commits, and sequential PR merges are recorded in GitHub; model reasoning/quality
has not been validated using controlled-test answers.
Implementation choices and actual check results remain reviewable in the PRs.
