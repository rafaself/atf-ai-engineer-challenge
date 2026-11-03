# Empório da Música — customer-support agent

This is a fictional demo: catalog and order tools simulate current store-system
requests using local data. No external fulfillment or carrier service is contacted.
The interface discloses this once; answers report the simulated system results
directly. An estimated delivery date still does not establish actual receipt.

Evaluator path: follow the Docker quick start below, open the chat and `/docs`,
then inspect [four representative Portuguese conversations](docs/examples/submission.md).
These are historical real-model captures with explicit revision limits. Current
offline checks verify application behavior, not current generated-answer quality.

A local Python customer-support agent for the Artefact AI Engineer challenge.
React chat, FastAPI and a standalone Python CLI share the reusable
`emporio-music` package, Bedrock agent and persistent SQLite history. It answers product, price,
availability, promotion, order and policy questions in Portuguese using the
supplied fictional data.

The demo uses typed catalog/order tools and local E5/Chroma policy retrieval.
Model weights and indexes require explicit preparation. It has no authentication:
keep it on loopback and use fictional customer data. The frontend selects customer
1; the API and CLI also support guests and other fictional customers.

The [recorded conversations](docs/examples/submission.md) include successes and
failures from earlier revisions. Generated prices, tool choices and policy claims
still require review; a source footer records consulted material without certifying
an answer. [Sprint 3 closure](docs/sprint-3.md) and the
[US-18 report](docs/examples/us-18/README.md) explain the remaining grounding and
retrieval limits, including failed mixed order/return cases. Controlled replays
and offline tests do not establish current real-model quality. New paid Bedrock
evaluations require separate explicit approval.

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
cached and builds the local Chroma index. Run it once for a new data volume. It
intentionally fails if an index already exists. To rebuild after an intentional policy
source change, run this explicit command:

```bash
docker compose run --rm app \
  python -m scripts.policy_benchmark.run --model e5 --index --rebuild \
  --allow-download --output-dir /tmp/policy-rag-bootstrap
```

Image build and normal startup do not download weights, prepare SQLite snapshots,
rebuild the index, or call a model provider.
`make prepare-data` imports 65 products, 25 promotions, 50 customers, 20 orders and
22 item rows from the supplied files; it never rewrites the CSV or PDF inputs.

Open the chat at [http://127.0.0.1:8000](http://127.0.0.1:8000) or the API docs at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). The UI, static assets and
existing API share one FastAPI process and origin. The port is published on loopback
only. The Compose data volume persists SQLite files, the Chroma index and the
Hugging Face cache across container restarts; `make down` keeps that volume.

For checks, install Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and Node.js 20.19+ or 22.12+ with npm, then run `make check`. The Docker build also
checks that the installed shared package reads its configured `/app/data` source
directory and can write runtime state there.

For Docker chat, put temporary credentials from your approved AWS credential source
in the Git-ignored `.env`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and
`AWS_SESSION_TOKEN`, along with `AWS_DEFAULT_REGION`. Remove `AWS_PROFILE` from
`.env`; Compose passes these values to the container, but does not mount the host's
`~/.aws` directory, so a host profile or SSO login is unavailable there. Keep the
credentials temporary and narrowly scoped. The UI and docs can start without AWS
credentials, but the agent cannot answer. `.env` and local AWS files are excluded
from the Docker build context and image. The policy-RAG runtime includes CPU PyTorch
and uses additional disk for model weights, cache and index data.

The named volume is initialized from `/app/data` in the image when first created.
Rebuilding the image does not refresh source files already in an existing volume.
To intentionally update the source data while keeping saved chat history, start the
app, copy the source files from the updated checkout into its existing volume, then
refresh the SQLite snapshots:

```bash
make up
docker compose cp data/categories.csv app:/app/data/categories.csv
docker compose cp data/products.csv app:/app/data/products.csv
docker compose cp data/promotions.csv app:/app/data/promotions.csv
docker compose cp data/customers.csv app:/app/data/customers.csv
docker compose cp data/orders.csv app:/app/data/orders.csv
docker compose cp data/order_items.csv app:/app/data/order_items.csv
docker compose cp data/store_policies.pdf app:/app/data/store_policies.pdf
docker compose cp data/policies/. app:/app/data/policies/
docker compose stop app
make prepare-data
# If policy sources changed, run the explicit --rebuild command above here.
make up
```

`make prepare-data` replaces only the catalog and operations snapshots; it preserves
the conversation database. These steps leave the persistent volume in place. Do not
run `docker compose down --volumes` when you need to retain conversations or other
persistent runtime data.

If catalog/order requests fail because SQLite snapshots are missing, run
`make prepare-data`. Policy retrieval requires both the E5 cache and index; missing
resources are service errors, not “no policy found.”

Use `make down` to stop the app without deleting its data. Removing the named volume
requires an explicit `docker compose down --volumes`.

If Docker starts but the published port times out on Linux, check host bridge
networking. The [validation report](docs/sprint-4-validation.md#clean-docker-setup-and-runtime)
records the observed limitation and a tested loopback-only host-network workaround.
It also distinguishes controlled interface checks from historical model evidence.

## Run without Docker for development

Install Python 3.12+ and `uv`, then from the repository root run:

```bash
uv sync --project apps/api --locked --extra policy-rag
test -f .env || cp .env.example .env
uv run --env-file .env --project apps/api --extra policy-rag --locked python -m emporio_music.prepare
uv run --env-file .env --project apps/api --extra policy-rag --locked uvicorn emporio_music_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

The frontend can run separately with the commands in
[`apps/frontend/README.md`](apps/frontend/README.md). Vite proxies `/api` to the
local FastAPI server. The frontend uses fictional customer ID `1`; this is demo
context, not authentication or customer selection. For guest API requests, omit
`customer_id`; for orders, repeat the same fictional customer ID on every follow-up.
See [API details](docs/api.md) for request examples and errors.

For direct terminal conversations without the HTTP server, prepare and run the
standalone Python CLI using [these commands](docs/cli.md). Its `--live` flag is
required before it constructs the Bedrock-backed agent.

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

GPT-6 Luna (`us.openai.gpt-6-luna`) through Bedrock Runtime's US cross-Region
profile in `us-east-1` is the runtime default. The owner selected it after the
full v7 benchmark: Luna scored 11 Pass / 1 Partial / 0 Fail with lower cost and
median latency than GPT-6.1 Sol, whose perfect 12/0/0 result cost about 20.5 times
more in this sample. See the [reviewed comparison](docs/examples/model-comparison/full-qwen-luna-sol-2026-11-03.md).
Pydantic AI provides typed function calling; straightforward Python/SQL handles
the small structured dataset. Set `BEDROCK_MODEL_ID` to override the default.
Policy retrieval uses embedded ChromaDB and locally cached multilingual E5; SQLite
remains the operational/history store. The optional `policy-rag` extra provides the
runtime libraries. Startup and default tests do not download weights, build indexes,
or call an embedding provider. See [policy retrieval setup and limitations](docs/policy-retrieval.md).

Three SQLite files separate replaceable catalog/order snapshots from chat history.
`EMPORIO_MUSIC_DATA_DIR` selects the source-data and persistent runtime directory.
Its default is `data` relative to the process working directory; the documented
local commands run from the repository root, preserving
`data/catalog.sqlite3`, `data/operations.sqlite3` and
`data/conversations.sqlite3`. Compose sets `/app/data` on its persistent volume.
The API uses `EMPORIO_MUSIC_FRONTEND_DIR` for built React assets and defaults to
`apps/frontend/dist` from the repository root.
Guests cannot retrieve orders. Session IDs let guests resume a chat; they do not
distinguish individual guests. Keep the demo on loopback with fictional data; it
has no authentication. Each tool read is authoritative within the simulation; local data does not imply
an external carrier request. Only `is_active` establishes promotion validity; the source has
no dates. The demo has no cross-process turn coordination or retry deduplication.

## Development checks

From the repository root:

```bash
make check-python
uv build --project packages/emporio_music
uv build --project apps/api
uv build --project apps/cli
```

Default tests use temporary SQLite and controlled models; real model requests are
forbidden. Paid Bedrock probes require explicit opt-in. See [validation](docs/validation.md),
[real examples](docs/examples/README.md) and [provider setup](docs/bedrock.md).

## Documentation and remaining work

Domain contracts and ports are grouped by responsibility. Import definitions directly
(for example, `domain.chat.ChatRequest`, `ports.chat.ChatServicePort` and
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
