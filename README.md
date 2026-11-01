# Empório da Música — customer-support agent

A Python prototype for the Artefact AI Engineer challenge. It answers product,
price, availability, promotion and account-order questions in Portuguese using
Pydantic AI tools and the supplied fictional data. SQLite keeps chat history
across restarts. Run one local server process; this is a challenge demonstration.

General policy retrieval (hours, address and returns) belongs to the later retrieval
sprint and remains unfinished. The assistant states that limitation instead of
inventing answers. [Sprint 2 closing examples](docs/examples/sprint-2/closure/README.md)
cover budget/context, promotions/PIX and scoped orders on the final application
code. Failed attempts and model comparisons remain published. These observations
do not establish complete challenge acceptance or guarantee every future answer.

## Run locally

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Run these commands from the repository root:

```bash
uv sync --project apps/backend --locked
cp .env.example .env
```

Edit `.env` to configure an AWS profile or access keys for Bedrock. Chat needs no
login or demo tokens. Omit `customer_id` for guest mode, or select a fictional
customer to demonstrate order retrieval. This is local demo selection, **not
authentication**; anyone using the demo can select any fictional customer.

Then prepare all supplied data with one command and start the API:

```bash
uv run --env-file .env --project apps/backend --locked python -m emporio_music_backend.prepare
uv run --env-file .env --project apps/backend --locked uvicorn emporio_music_backend.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Preparation imports 65 products, 25 promotions, 50 customers, 20 orders and 22 item
rows. Re-running it refreshes the source snapshots and leaves chat history alone.
It never rewrites supplied CSVs/PDFs. A leftover pre-US-12 generated catalog must
be moved aside before preparing a fresh catalog; no migration system is included.

Open [Swagger UI](http://127.0.0.1:8000/docs) and send
`{"message":"Quais são as promoções?"}` as a guest. Reuse the returned `session_id`
with `{"message":"E o segundo no PIX?","session_id":"<returned-id>"}`.
For orders, start a new chat with `{"message":"Meus pedidos","customer_id":1}`;
repeat the same customer selection on each follow-up. Omit `session_id` when
switching customer or mode. Generated databases and AWS credentials stay Git-ignored.
If upgrading from token-based sessions, stop the server and move the old
`data/conversations.sqlite3` aside before starting. Keep that history file; old
schemas are rejected without migration or deletion.
See [API details](docs/api.md) for curl, configuration and errors.

## How it works

FastAPI calls a small chat service, which loads owned history, runs the agent and
saves one complete user/assistant turn. Tools retrieve facts from read-only SQLite
snapshots; the model never builds SQL or chooses the selected customer.

- **Catalog:** literal name/category lookup, active/stock checks and bounded results.
- **Pricing:** integer-centavo half-up arithmetic; an eligible active promotion
  takes priority, otherwise explicitly requested PIX receives 5%. Discounts never
  stack. Budget filters use final prices, while original prices remain intact.
- **Orders:** validated fictional customer selection and parameterized scope checks. Historical
  totals stay unchanged; current catalog prices never reconstruct purchase prices.
- **History:** persisted text pairs, bounded to six turns/24,000 characters by
  default. One service rejects overlapping turns on the same session. Independent
  chats can run concurrently. Failed/cancelled calls save no completed turn.

Bedrock Qwen 3 (`qwen.qwen3-32b-v1:0`) in `us-east-1` is the default model,
selected after the bounded comparison reproduced invalid PIX answers with Nova
Micro/Lite and Qwen passed the final conversations. Pydantic AI provides typed
function calling; straightforward Python/SQL handles the small structured dataset.
Existing `.env` files should set `BEDROCK_MODEL_ID=qwen.qwen3-32b-v1:0` to use this selection.
The policy PDF will use a separate simple lookup. No vector store is needed here.

Three SQLite files separate replaceable catalog/order snapshots from chat history.
The small `paths.py` module derives `PROJECT_ROOT` from its source location and
defines all storage under `PROJECT_ROOT / "data"`: `catalog.sqlite3`,
`operations.sqlite3` and `conversations.sqlite3`. Paths are fixed, independent of
the launch directory; no storage-path environment variables or CLI overrides are needed.
Guests cannot retrieve orders. Session IDs let guests resume a chat; they do not distinguish individual
guests. Keep the demo on loopback with fictional data; it has no authentication. Facts reflect imported snapshots, not live stock
or carrier status. Only `is_active` establishes promotion validity; the source has
no dates. The demo has no cross-process turn coordination or retry deduplication.

## Development checks

From the repository root:

```bash
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests
uv run --directory apps/backend --locked pytest
uv build --project apps/backend
```

Default tests use temporary SQLite and controlled models; real model requests are
forbidden. Paid Bedrock probes require explicit opt-in. See [validation](docs/validation.md),
[real examples](docs/examples/README.md) and [provider setup](docs/bedrock.md).

## Documentation and remaining work

Contracts and protocols are grouped by responsibility. Import definitions directly
(for example, `contracts.chat.ChatRequest`, `ports.chat.ChatServicePort` and
`application.chat.ChatService`); package initializers hold no implementation.

Start here; use the [documentation index](docs/README.md) for implementation details
and historical decisions. Three representative live conversations are reviewed;
next comes policy retrieval and its evaluation in the later retrieval sprint.
Frontend, deployment and production authentication are outside the current demo. The recruiting email determines the submission cutoff.

OpenAI Codex assisted with analysis, implementation, tests, review and GitHub delivery.
Scoped commits and PRs record that workflow; controlled test answers are not claimed
as live model-quality evidence. Preserve source bytes and reference the related issue
in every commit body. See [working agreements](AGENTS.md).
