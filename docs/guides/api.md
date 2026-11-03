# Local chat API

Use the [README Getting Started guide](../../README.md#getting-started) for the
recommended Docker setup and preparation/startup sequence. Run one uvicorn process
on loopback for local API development. Setup uses the same fixed storage paths as
the API and never opens the conversation database. The application does not load
`.env` automatically; `uv --env-file .env` does. Existing shell variables take
precedence.

## Local API setup

For local development, install Python 3.12+ and `uv`, then run these commands from
the repository root. Edit `.env` for the desired Bedrock model and host credentials
before starting the API; a host AWS profile or SSO session can use the normal
credential chain here.

```bash
uv sync --project apps/api --locked --extra policy-rag
test -f .env || cp .env.example .env
uv run --env-file .env --project apps/api --extra policy-rag --locked python -m emporio_music.prepare
uv run --project apps/api --extra policy-rag --locked python -m emporio_music.prepare_policy_index --allow-download
uv run --env-file .env --project apps/api --extra policy-rag --locked uvicorn emporio_music_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Policy indexing remains explicit in this path too. To develop the React client
against this API, follow the [frontend guide](../../apps/frontend/README.md).

## Guest and fictional-customer requests

No credentials are required. Guest catalog/promotion chat:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quais violões custam até R$1.000?"}'
```

Select an existing fictional customer for orders:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Meus pedidos","customer_id":1}'
```

This is **local fictional demo selection, not authentication**. Anyone using the
demo can select any imported customer. Bind to loopback; do not deploy this selector
as a public service with real data. Guest order tools return a selection-required
message without reading orders. Customer IDs are strict positive 64-bit integers,
validated against the current registry on each selected request. Unknown IDs fail
explicitly. Omitted or null `customer_id` means guest; no ID is inferred from chat text.

Success contains `answer` and a UUID4 `session_id`. Repeat that ID and the same
customer selection to continue, for example:

```json
{"message":"Detalhe o primeiro pedido","customer_id":1,"session_id":"<returned-id>"}
```

Omit `session_id` or send null to start another chat. Invalid non-null IDs are
rejected. Guest/customer switching and customer changes require a new session;
unknown or differently scoped session IDs return the same 404 without model execution.
Guest sessions are distinguished only by their IDs: anyone with a guest session ID
can resume it. There is no identity protection for individual demo users.

The React client uses `POST /api/chat/stream` with the same request fields. It
returns `text/event-stream` events named `delta`, `done`, and `error`. A `delta`
contains provisional text. `done` contains the authoritative `answer` and
`session_id` and is sent only after the complete answer is validated and the user /
assistant pair has been committed. `error` contains a sanitized message. Errors
before streaming starts use the normal HTTP status and JSON body. If the client
disconnects before the commit, cancellation closes the provider stream and the
turn is not saved. A connection lost after commit but before `done` may leave a
saved turn, so the client reports unknown completion and does not retry. The
existing `POST /api/chat` JSON contract remains available.

Nested identity, history, context and payment fields remain forbidden; payment
selection comes from conversational text through typed tools. Message length is
limited to 4,000 characters. `customer_id` is HTTP-only: the boundary removes it from
ChatRequest and passes the validated selection through ExecutionContext. It never
becomes a model-generated tool argument or shared mutable customer state.

History survives restarts. Try promotions followed by `E o segundo no PIX?`.
Tools retrieve fresh facts; previous answers are context, not evidence.
Docs/OpenAPI require no provider setup.

## Configuration

| Setting | Default |
| --- | --- |
| `CHAT_TIMEOUT_SECONDS` | 60 seconds |
| `HISTORY_MAX_TURNS` | 6; supported 1–20 |
| `HISTORY_MAX_CHARACTERS` | 24000; supported 1–64000 |
| `PIPELINE_LOGS` | 0; set 1 for metadata diagnostics |

`EMPORIO_MUSIC_DATA_DIR` explicitly selects the source-data and persistent runtime
directory. It defaults to `data` relative to the process working directory; the
documented commands run from the repository root. Compose sets `/app/data` on the
persistent volume. The API's React build path is `EMPORIO_MUSIC_FRONTEND_DIR`,
defaulting to `apps/frontend/dist` from the repository root.
Conversation files are private; preparation refreshes only source snapshots. Before
using this version with a v1 conversation database, stop the server and move that
file aside, preserving it. Startup then creates a fresh database at the fixed path.
There is no automatic reset or migration. Source CSV/PDF files remain unchanged.

## Errors and persistence

| Case | Status |
| --- | --- |
| Unknown/foreign session | 404 |
| Another turn is active on this session in this service | 409 |
| Invalid request or unknown selected customer | 422 |
| Missing configuration or unavailable provider | 503 |
| Deadline/provider timeout | 504 |
| Retrieval, persistence or execution failure | 500 |

Details are sanitized. A valid empty result differs from a retrieval failure. One
service rejects overlapping turns on a session while independent sessions can run
concurrently. A complete user/assistant pair saves atomically before success. There
are no expected revisions or cross-instance guarantees. Run one process/service.
Failed/cancelled executions save no completed turn. Streaming failures after the
response starts use sanitized in-band `error` events. Response loss after commit
can still leave a saved turn; automatic retry deduplication is outside the demo.

## Direct application calls

Trusted code imports the defining modules:

```python
from emporio_music.application.chat import ChatService
from emporio_music.domain.chat import ChatRequest
from emporio_music.domain.conversations import ExecutionContext
from emporio_music.ports.chat import ChatServicePort
```

It calls `ChatService.chat(request, context=ExecutionContext())` for guests or
supplies a validated CustomerIdentity as `ExecutionContext(identity=...)` for a
selected customer. Direct callers own registry validation at their application
boundary; order repositories independently recheck customer existence.
The service loads history itself; externally supplied session metadata/history is
rejected. The lower-level agent can execute explicitly trusted owned history without
saving it. A CustomerIdentity value alone does not authenticate an external caller.

`create_app(chat_service=...)` supports controlled tests. HTTP selection always
validates non-null IDs against the operational registry. Stop the server before
manually resetting conversation storage; removing it makes old session IDs inaccessible.
Diagnostics contain counts, timings and safe error classes, not raw messages, answers,
identifiers, credentials or tool rows. See [architecture](../architecture.md) and
[provider setup](bedrock.md) for remaining execution limits.
