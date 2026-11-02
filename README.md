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
They predate the current source-only monetary guard: budget comparisons now say
“seu orçamento” without repeating customer amounts. This guard change is verified
offline only. Failed attempts and model comparisons remain published. These observations
do not establish complete challenge acceptance or guarantee every future answer.

[US-18](docs/examples/us-18/README.md) adds current-run citation enforcement,
explicit mixed order/return tool checks and general grounding principles.
These corrections have offline regression coverage. The first live follow-up passes
three cases; the mixed case still needs revalidation after further corrections.
The backend now appends an order-snapshot notice from current tool metadata instead
of requiring a fixed phrase. An earlier saved Qwen answer replays with that notice
offline; this is not a post-change live run. A local E5 check found that a short
context-dependent follow-up misses section 4.1 alone; adding the previous user
question retrieves it. Policy search now uses that bounded one-turn context when
the combined query is short. This checks retrieval only, not live answer quality.
See the [actual review](docs/examples/us-18/results.md).
The latest approved current-code batch stopped on its first mixed return turn with
HTTP 500 after citation-format retry exhaustion. Both tools succeeded and order
status was preserved, but policy applicability and missing facts were incompletely
addressed. The other five planned turns remain untested; see the
[batch review](docs/examples/us-18/results.md#finding-5-authorized-current-code-grounding-batch).
Sprint completion does not require RAG to outperform Full Context.

## Run locally

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Run these commands from the repository root:

```bash
uv sync --project apps/backend --locked --extra policy-rag
cp .env.example .env
```

Edit `.env` to configure an AWS profile or access keys for Bedrock. Chat needs no
login or demo tokens. Omit `customer_id` for guest mode, or select a fictional
customer to demonstrate order retrieval. This is local demo selection, **not
authentication**; anyone using the demo can select any fictional customer.

Before starting the API, explicitly download E5 if needed and build the local Chroma
index. This command also writes its development comparison report to `/tmp`; generated
weights and the index remain outside Git:

```bash
uv run --project apps/backend --extra policy-rag --locked \
  python -m scripts.policy_benchmark.run --model e5 --index --allow-download \
  --output-dir /tmp/policy-rag-bootstrap
```

Then prepare all supplied data and start the API:

```bash
uv run --env-file .env --project apps/backend --extra policy-rag --locked python -m emporio_music_backend.prepare
uv run --env-file .env --project apps/backend --extra policy-rag --locked uvicorn emporio_music_backend.api.app:create_app --factory --host 127.0.0.1 --port 8000
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
Frontend, deployment and production authentication are outside the current demo. The recruiting email determines the submission cutoff.

OpenAI Codex assisted with analysis, implementation, tests, review and GitHub delivery.
Scoped commits and PRs record that workflow; controlled test answers are not claimed
as live model-quality evidence. Preserve source bytes and reference the related issue
in every commit body. See [working agreements](AGENTS.md).

See [policy corpus, runtime retrieval and evaluation protocol](docs/policy-retrieval.md) for setup, provenance and measured limitations.
