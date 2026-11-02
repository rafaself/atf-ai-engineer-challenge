# Empório da Música — customer-support agent

A Python prototype for the Artefact AI Engineer challenge. It answers product,
price, availability, promotion and account-order questions in Portuguese using
Pydantic AI tools and the supplied fictional data. SQLite keeps chat history
across restarts. Run one local server process; this is a challenge demonstration.

Store-policy search is now wired into the existing agent through a local E5/Chroma
index. The index and model are prepared explicitly; the assistant reports uncertainty
when retrieved excerpts do not support an answer. US-17 reviewed four paired
Portuguese conversations on 2026-11-01 using RAG and full-policy context. The
review preserved a RAG HTTP 500, missed policy-tool calls, a wrong citation and
unsupported claims; it does not establish that either context strategy is reliable
or that retrieval meets the frozen US-15 targets. See the [paired results](docs/examples/us-17/results.md)
and [captures](docs/examples/us-17/captures.json). Earlier [Sprint 2 closing examples](docs/examples/sprint-2/closure/README.md)
cover budget/context, promotions/PIX and scoped orders at their recorded revision.
Failed attempts and model comparisons remain published; they do not establish complete
challenge acceptance or guarantee future answers.

[US-18](docs/examples/us-18/README.md) now appends a consistent “Fontes consultadas”
list from policy records returned in the current run. It accepts readable generated
references without requiring a citation grammar or corrective model call. The same
simplification removes free-text amount matching and Portuguese intent checks:
legitimate budget quotes and negated return requests previously triggered errors.
Pricing calculations and customer isolation remain enforced by the tools. Tool use,
generated prices and claim support are evaluated through conversations, rather than
inferred from the wording of an answer. Blank/internal-control output still receives
one corrective retry. Snapshot and partial-result notices remain automatic.

The last approved live batch stopped on its first mixed return turn with HTTP 500
at the earlier revision because of citation-format retry exhaustion. Replaying its
saved candidate through the current HTTP path now returns 200 with source metadata,
without changing the generated text. This is a controlled regression, not a new live
Qwen result; its policy-scope omissions remain documented in the [batch review](docs/examples/us-18/results.md#finding-5-authorized-current-code-grounding-batch).
The other five live turns remain untested. A bounded local E5 check also supports
adding the previous user question to short contextual follow-ups; broader retrieval
optimization is deferred. Sprint completion does not require RAG to outperform Full Context.

Sprint 3 closure scope, evidence and deferred work are recorded in [the sprint closeout](docs/sprint-3.md).

## Run the complete demo with Docker

Install Docker Engine or Docker Desktop with Compose, and GNU Make. From the
repository root, configure Bedrock credentials for runtime use, then run:

```bash
test -f .env || cp .env.example .env
# Edit .env with your local Bedrock configuration.
make build
make prepare-data
make prepare-policy
make up
```

`make prepare-policy` explicitly downloads the pinned CPU E5 model if it is not
cached and builds the local Chroma index. Run it during first-time setup or when
intentionally rebuilding that index. Image build and normal startup do not download
weights, prepare SQLite snapshots, rebuild the index, or call a model provider.
`make prepare-data` imports 65 products, 25 promotions, 50 customers, 20 orders and
22 item rows from the supplied files; it never rewrites the CSV or PDF inputs.

Open the chat at [http://127.0.0.1:8000](http://127.0.0.1:8000) or the API docs at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The UI, static assets and
existing API share one FastAPI process and origin. The port is published on loopback
only. The Compose data volume persists SQLite files, the Chroma index and the
Hugging Face cache across container restarts; `make down` keeps that volume.

For checks, install Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Node.js 20.19+ or 22.12+ with npm, then run `make check`. The Docker build also
performs a packaging smoke check for the source-relative data path, an input CSV
and write access to runtime data.

If catalog/order requests fail because SQLite snapshots are missing, run
`make prepare-data`. Policy retrieval requires both the E5 cache and index from
`make prepare-policy`; missing resources are service errors, not “no policy found.”
Chat requests require valid Bedrock credentials in `.env`; the UI and docs can start
without them, but the agent cannot answer. The `.env` file and local AWS files are
excluded from the Docker build context and image. The policy-RAG runtime includes
CPU PyTorch and uses additional disk for model weights, cache and index data.

Use `make down` to stop the app without deleting its data. Removing the named volume
requires an explicit `docker compose down --volumes`.

## Run without Docker for development

Install Python 3.12+ and `uv`, then from the repository root run:

```bash
uv sync --project apps/backend --locked --extra policy-rag
test -f .env || cp .env.example .env
uv run --env-file .env --project apps/backend --extra policy-rag --locked python -m emporio_music_backend.prepare
uv run --env-file .env --project apps/backend --extra policy-rag --locked uvicorn emporio_music_backend.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

The frontend can run separately with the commands in
[`apps/frontend/README.md`](apps/frontend/README.md). Vite proxies `/api` to the
local FastAPI server. The frontend uses fictional customer ID `1`; this is demo
context, not authentication or customer selection. For guest API requests, omit
`customer_id`; for orders, repeat the same fictional customer ID on every follow-up.
See [API details](docs/api.md) for request examples and errors.

## How it works

FastAPI calls a small chat service, which loads owned history, runs the agent and
saves one complete user/assistant turn. Tools retrieve facts from read-only SQLite
snapshots; the model never builds SQL or chooses the selected customer.

- **Catalog:** literal name/category lookup, active/stock checks and bounded results.
- **Pricing:** integer-centavo half-up arithmetic; an eligible active promotion
  takes priority, otherwise explicitly requested PIX receives 5%. Discounts never
  stack. Budget filters use final prices, while original prices remain intact.
- **Orders:** validated fictional customer selection and parameterized scope checks.
  Historical totals stay unchanged; current catalog prices never reconstruct purchase prices.
- **Policies:** the existing agent retrieves three E5 ranking seeds plus direct
  related conditions, capped at eight excerpts. Answers include section/page citations;
  missing or stale local search resources fail as service errors instead of policy no-matches.
- **History:** persisted text pairs, bounded to six turns/24,000 characters by
  default. One service rejects overlapping turns on the same session. Independent
  chats can run concurrently. Failed/cancelled calls save no completed turn.

Bedrock Qwen 3 (`qwen.qwen3-32b-v1:0`) in `us-east-1` is the default model,
selected after the bounded comparison reproduced invalid PIX answers with Nova
Micro/Lite and Qwen passed the final conversations. Pydantic AI provides typed
function calling; straightforward Python/SQL handles the small structured dataset.
Existing `.env` files should set `BEDROCK_MODEL_ID=qwen.qwen3-32b-v1:0` to use this selection.
Policy retrieval uses embedded ChromaDB and locally cached multilingual E5; SQLite
remains the operational/history store. The optional `policy-rag` extra provides the
runtime libraries. Startup and default tests do not download weights, build indexes,
or call an embedding provider. See [policy retrieval setup and limitations](docs/policy-retrieval.md).

Three SQLite files separate replaceable catalog/order snapshots from chat history.
The small `paths.py` module derives `PROJECT_ROOT` from its source location and
defines all storage under `PROJECT_ROOT / "data"`: `catalog.sqlite3`,
`operations.sqlite3` and `conversations.sqlite3`. Paths are fixed, independent of
the launch directory; no storage-path environment variables or CLI overrides are needed.
Guests cannot retrieve orders. Session IDs let guests resume a chat; they do not
distinguish individual guests. Keep the demo on loopback with fictional data; it
has no authentication. Facts reflect imported snapshots, not live stock or carrier
status. Only `is_active` establishes promotion validity; the source has
no dates. The demo has no cross-process turn coordination or retry deduplication.

## Development checks

From the repository root:

```bash
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests scripts
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
and historical decisions. Three Sprint 2 conversations and four US-17 paired
policy scenarios are descriptive evidence, not a guarantee of future answers. See
the [US-17 results](docs/examples/us-17/results.md) for grounding, uncertainty,
tool-selection and full-context findings.
The [React frontend](apps/frontend/README.md) uses the existing chat API with a
fixed fictional customer and session context. The Docker package remains limited
to local loopback use; public deployment is out of scope. The recruiting email
determines the submission cutoff.

OpenAI Codex assisted with analysis, implementation, tests, review and GitHub delivery.
Scoped commits and PRs record that workflow; controlled test answers are not claimed
as live model-quality evidence. Preserve source bytes and reference the related issue
in every commit body. See [working agreements](AGENTS.md).

See [policy corpus, runtime retrieval and evaluation protocol](docs/policy-retrieval.md) for setup, provenance and measured limitations.
