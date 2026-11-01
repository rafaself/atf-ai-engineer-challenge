# Empório da Música — AI Engineer Challenge

Python customer-support agent project for the Artefact technical challenge.
This checkout implements **US-01 through US-11**: an installable backend,
development checks, validated values/interfaces, and atomic catalog import with
read-only SQLite retrieval, an isolated Pydantic AI/Bedrock adapter, and typed
product-search tools connected to the catalog repository.
Live Bedrock tool calling and five remediation scenarios have been validated;
see [reviewed captures](docs/examples/README.md) for evidence and limitations.
US-10 adds persistent owned sessions behind `POST /api/chat`, using server-configured
demo bearer identities and a separate writable SQLite database. Complete turns are
committed before responses; bounded text history survives application restarts.
US-11 adds a minimal customer/order snapshot, validated demo-customer mappings,
and read-only order tools scoped by trusted per-run identity. The original
customer/order fixtures are fictional and committed with the owner's confirmation.
See [operational import and authorization](docs/orders.md),
[local API startup](docs/api.md) and [agent setup](docs/bedrock.md).

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python
3.12. The package supports Python 3.12 and later; `apps/backend/.python-version` selects
3.12 for a consistent development baseline. Setup was validated with uv 0.13.4 and
Python 3.12.15.

Run from the repository root:

```bash
uv sync --project apps/backend --locked
uv run --directory apps/backend python -c "import emporio_music_backend"
```

The environment is created at `apps/backend/.venv`. Development tools live in the
`dev` dependency group and are installed by default. Production dependencies are
Pydantic, Pydantic AI with Bedrock support, boto3, FastAPI, and uvicorn. The checked-in `apps/backend/uv.lock` records resolved versions;
use `--locked` when installing an existing checkout.

## Quality checks

Run from the repository root:

```bash
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests
uv run --directory apps/backend --locked pytest
uv build --project apps/backend
```

`--directory apps/backend` deliberately changes the working directory so every tool
uses `apps/backend/pyproject.toml` and resolves `src` and `tests` correctly. `--project`
selects a project without changing the command's working directory.

Contract tests validate chat/catalog values, derived fields, independent typed
fakes, and dependency boundaries without network or database access. Strict mypy
covers source and tests, including those fakes. The packaging smoke test imports
the installed distribution in an isolated Python
subprocess outside the source tree, without AWS configuration or provider imports.
Build outputs are ignored under `apps/backend/dist/`.

To check the wheel with runtime dependencies only (POSIX shell):

```bash
wheel_check_dir=$(mktemp -d)
uv venv --python 3.12 "$wheel_check_dir/.venv"
uv pip install --python "$wheel_check_dir/.venv/bin/python" \
  apps/backend/dist/emporio_music_backend-0.1.0-py3-none-any.whl
(cd "$wheel_check_dir" && .venv/bin/python -I -c \
  "import emporio_music_backend; from importlib.metadata import version; print(version('emporio-music-backend'))")
```

The disposable directory can be removed after verification.

## Repository structure

| Directory | Responsibility |
| --- | --- |
| `apps/backend/` | Installable Python package, tests, and development tooling. |
| `apps/frontend/` | Placeholder for a later sprint; no JavaScript toolchain. |
| `data/` | Unmodified fictional catalog/customer/order CSVs, provenance, and checksums. |
| `docs/` | Architecture decisions, setup guides, and validation evidence. |

## Configuration and data

`.env.example` documents configuration; export values explicitly, without a dotenv loader.
The API requires `DEMO_CUSTOMER_TOKENS_JSON`, a private token-to-customer mapping;
follow [demo identity setup](docs/api.md#demo-identity-setup). Keep generated tokens
in the ignored local environment. This is a local demonstration of identity and
isolation, not production authentication. Conversation data defaults to
`data/conversations.sqlite3`; catalog and operational re-import never replace it.
Operational data defaults to `data/operations.sqlite3`, independent of the catalog.
The provider preference is Bedrock in `us-east-1`, initially
`amazon.nova-micro-v1:0`, or another validated low-cost feasible model. Model access
and tool calling were live-validated with Nova Micro in us-east-1 on 2026-10-31. The integration uses
the standard AWS credential chain; no credentials are required for setup or tests.

`DATABASE_PATH` documents the catalog path relative to the repository root; pass
that path explicitly to the importer below. The environment example is not loaded
automatically. See [local API startup](docs/api.md) for uvicorn and curl commands.

Products, categories, customers, orders and order items are copied byte-for-byte.
See [data provenance](data/README.md) for fictional origin and SHA-256 verification.
These files are an imported-source snapshot, not a live inventory service. Import and retrieval now implement availability and catalog-price
filtering. Promotion calculations remain deferred; order access is scoped to the
authenticated account.

### Import the catalog

From the repository root, run:

```bash
uv run --project apps/backend --locked python -m \
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
uv run --project apps/backend --locked python -c \
  "from pathlib import Path; from emporio_music_backend.contracts import ProductSearchQuery; from emporio_music_backend.infrastructure.sqlite_repository import SQLiteProductRepository; print(SQLiteProductRepository(Path('data/catalog.sqlite3')).search(ProductSearchQuery(category='violoes', max_price_centavos=100000)).model_dump_json())"
```

The budget search has 12 matches in the supplied snapshot; the default limit is
10, so truncation is reported. Use limit 20 to retrieve all 12.

### Import operational data

After importing the catalog, run from the repository root:

```bash
uv run --project apps/backend --locked python -m \
  emporio_music_backend.infrastructure.operations_import \
  --customers data/customers.csv --orders data/orders.csv \
  --order-items data/order_items.csv --catalog data/catalog.sqlite3 \
  --database data/operations.sqlite3
```

Expected: `Imported 50 customers, 20 orders and 22 items`. This required import
validates references and replaces the minimal operational snapshot atomically.
All configured demo-token customer IDs must exist in this snapshot; the resolver
rechecks the matched customer on every request. Missing/incompatible storage or
invalid mappings fail safely; HTTP has no catalog-only fallback. Generated files
are private and Git-ignored. See [order import, fields and failures](docs/orders.md).

## Decisions and follow-up

The project uses one Python package with `uv_build` and no root uv workspace.
Pydantic 2 supplies frozen models with unknown inputs forbidden. The accepted
[ADR-0001](docs/adr/0001-modular-monolith-and-dependency-boundaries.md) describes
module responsibilities, dependency direction, and tradeoffs.

### Current application contracts

| Contract | Behavior |
| --- | --- |
| `ChatRequest` / `ChatResponse` | Message (maximum 4,000 characters), optional continuation `session_id`; successful answer and required server session ID. Omit the ID to create a session; explicit null/invalid IDs are rejected. |
| `AgentResponse` | Validated answer from the provider adapter; the application supplies the session ID after saving. |
| `ProductSearchQuery` | Optional `category` / `product_name`, inclusive `min_price_centavos` / `max_price_centavos`, `available_only=True`, limit 10 (maximum 20). |
| `ProductSummary` | Product/category IDs and names, integer-centavo price, stock quantity, status, and derived availability. |
| `ProductSearchResult` | Immutable product tuple, total matches before limiting, and derived truncation. |
| `CustomerIdentity` / `ConversationSession` | Trusted customer ID and an owned server-generated UUID4; neither carries credentials. |
| `ConversationMessage` / `ExecutionContext` | Immutable user/assistant text history in complete pairs, with matching trusted identity/session ownership. |
| `CustomerIdentityResolver.resolve` | Resolves server-configured demo bearer tokens to trusted identities; credentials stay outside execution context. |
| `ConversationRepository` | Owned session creation, bounded history loading, and atomic expected-revision append. |
| `HistoryLimits` | Last 6 complete turns within 24,000 characters by default; configurable up to 20 turns / 64,000 characters. |
| `AgentExecutor.run` | Async execution with required keyword-only `context: ExecutionContext`, returning AgentResponse. |
| `ProductRepository.search` | Synchronous typed catalog search port. |
| `CustomerRepository.exists` | Current imported customer existence for trusted identity validation. |
| `OrderRepository.list_orders` / `get_order` | Required trusted identity; scoped SQL, bounded typed results, indistinguishable foreign/unknown order IDs. |
| `OrderSummary` / `OrderDetail` / `OrderListResult` | Exact supplied totals, optional tracking/estimate, bounded product references/quantities and truncation metadata. |
| `ChatService.chat` / `ChatServicePort` | Requires resolved identity in context; loads owned history, executes, and saves a completed turn under the default 60-second deadline. |

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

ChatService accepts only resolved identity in its execution context and loads all
session/history data from its repository. A UUID alone never grants access;
unknown and foreign sessions return the same safe error. The lower-level agent
adapter still accepts explicit owned text history, but does not persist it.
Identity/session metadata stays outside model messages; current tool results
provide minimal scoped facts to the provider. Current-run tool evidence drives
output notices.
See [direct application calls](docs/api.md#direct-application-calls) and
[ADR-0004](docs/adr/0004-persistent-conversation-turns.md) for the implemented
storage, concurrency, timeout, and response-loss boundaries. No new production
dependency is added.

See [architecture and prompting rationale](docs/architecture.md),
[validation evidence](docs/validation.md), [reviewed real examples](docs/examples/README.md),
and [follow-up/submission requirements](docs/follow-up.md).
Policy-aware answers and operational-data-versus-policy routing remain follow-up work.
Five reviewed real conversations and a separate live tool probe are recorded;
passing scenarios do not guarantee every future generated answer. Those live
captures predate persistent sessions; new multi-turn Bedrock evaluation remains
US-13. Policy answers, promotion calculations, frontend delivery,
and deployment packaging remain follow-up work.

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
