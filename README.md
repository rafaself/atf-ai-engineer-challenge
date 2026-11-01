# Empório da Música — customer-support agent

A Python prototype for the Artefact AI Engineer challenge. It answers product,
price, availability, promotion and account-order questions in Portuguese using
Pydantic AI tools and the supplied fictional data. SQLite keeps chat history
across restarts. Run one local server process; this is a challenge demonstration.

General policy retrieval (hours, address and returns) remains unfinished. The
assistant states that limitation instead of inventing answers. Existing live
examples predate the latest features; fresh multi-turn evaluation remains US-13.

## Run locally

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Run these commands from the repository root:

```bash
uv sync --project apps/backend --locked
cp .env.example .env
```

Edit `.env`: configure an AWS profile or access keys for Bedrock, and add a private
`DEMO_CUSTOMER_TOKENS_JSON` mapping such as `{"<generated-token>":1}`. Generate a
URL-safe token with:

```bash
uv run --project apps/backend --locked python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Then prepare all supplied data with one command and start the API:

```bash
uv run --env-file .env --project apps/backend --locked python -m emporio_music_backend.prepare
uv run --env-file .env --project apps/backend --locked uvicorn emporio_music_backend.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Preparation imports 65 products, 25 promotions, 50 customers, 20 orders and 22 item
rows. Re-running it refreshes the source snapshots and leaves chat history alone.
It never rewrites supplied CSVs/PDFs. A leftover pre-US-12 generated catalog must
be recreated or replaced with a fresh configured path; no migration system is included.

Open [Swagger UI](http://127.0.0.1:8000/docs), select **Authorize**, and enter a
configured token. Send `{"message":"Quais são as promoções?"}`. Reuse the returned
`session_id` with `{"message":"E o segundo no PIX?","session_id":"<returned-id>"}`.
Omit the ID to start a new chat. Credentials and generated databases stay Git-ignored.
See [API details](docs/api.md) for curl, configuration and errors.

## How it works

FastAPI calls a small chat service, which loads owned history, runs the agent and
saves one complete user/assistant turn. Tools retrieve facts from read-only SQLite
snapshots; the model never builds SQL or chooses the authorized customer.

- **Catalog:** literal name/category lookup, active/stock checks and bounded results.
- **Pricing:** integer-centavo half-up arithmetic; an eligible active promotion
  takes priority, otherwise explicitly requested PIX receives 5%. Discounts never
  stack. Budget filters use final prices, while original prices remain intact.
- **Orders:** trusted demo identity and parameterized ownership checks. Historical
  totals stay unchanged; current catalog prices never reconstruct purchase prices.
- **History:** persisted text pairs, bounded to six turns/24,000 characters by
  default. One service rejects overlapping turns on the same session. Independent
  chats can run concurrently. Failed/cancelled calls save no completed turn.

Bedrock Nova Micro in `us-east-1` is the default model. Pydantic AI provides typed
function calling; straightforward Python/SQL handles the small structured dataset.
The policy PDF will use a separate simple lookup. No vector store is needed here.

Three SQLite files separate replaceable catalog/order snapshots from chat history.
Preparation and the API use the same `.env` paths: `DATABASE_PATH`,
`OPERATIONS_DATABASE_PATH`, and `CONVERSATION_DATABASE_PATH`. Demo customer mapping
is not production authentication. Facts reflect imported snapshots, not live stock
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
and historical decisions. Next priorities are policy retrieval and 3–5 reviewed,
representative live conversations. Frontend, deployment and production authentication
are outside the current demo. The recruiting email determines the submission cutoff.

OpenAI Codex assisted with analysis, implementation, tests, review and GitHub delivery.
Scoped commits and PRs record that workflow; controlled test answers are not claimed
as live model-quality evidence. Preserve source bytes and reference the related issue
in every commit body. See [working agreements](AGENTS.md).
