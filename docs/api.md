# Local conversational API

The local API uses demo bearer identities, owned SQLite sessions, and bounded
multi-turn history. Run one uvicorn worker on loopback; public deployment and
production authentication remain outside this project slice.

## Demo identity setup

Generate a private URL-safe token locally:

```bash
uv run --project apps/backend --locked python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the resulting token in the ignored local `.env` using a token-to-customer JSON
mapping. Replace the placeholder; do not use it as a credential:

```text
DEMO_CUSTOMER_TOKENS_JSON='{"<generated-token>":1}'
```

Multiple tokens/customers can be configured. Tokens must contain 32–256 ASCII
letters, digits, underscores, or hyphens. IDs must be positive integers, with no
boolean/string coercion or duplicate JSON keys. Missing or invalid configuration
fails closed. The resolver retains token digests, not plaintext tokens, and does
not expose credentials to the application context or model. Every configured ID
must exist in the imported customer registry. Initialization validates all mappings;
each resolution rechecks the matched customer. Removed customers fail safely.
See [operational setup](orders.md) before configuring tokens.

The server reads environment configuration explicitly; it does not load `.env`.
The `uv --env-file` option below loads your local file. Restart after changing
configuration or rotating tokens. Tokens mapped to the same customer share that
customer's session ownership. Never commit tokens or publish their headers.

## Startup and requests

Import the catalog **and operational snapshot** using README instructions, then configure Bedrock as documented
in [agent setup](bedrock.md). Start from the repository root:

```bash
uv run --env-file .env --project apps/backend --locked uvicorn emporio_music_backend.api.app:create_app \
  --factory --host 127.0.0.1 --port 8000
```

In the client terminal set `DEMO_CUSTOMER_TOKEN` to one token in the server mapping
(this variable is a curl helper, not server configuration). Send a first message:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H "Authorization: Bearer $DEMO_CUSTOMER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quais violões disponíveis custam até R$1.000?"}'
```

A successful response has `answer` and a server-generated UUID4 `session_id`.
Copy that identifier to `SESSION_ID` in the client terminal and continue:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H "Authorization: Bearer $DEMO_CUSTOMER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"message\":\"Quanto custa o segundo agora?\",\"session_id\":\"$SESSION_ID\"}"
```

Omitting `session_id` creates a new session for the resolved customer. Explicit
null, malformed, or non-UUID4 values are invalid; an explicit unknown or foreign
ID never creates/reassigns a session. Client `customer_id`, identity, history,
and context fields are forbidden. Body validation errors use generic details
rather than echoing potentially sensitive input. Open `/docs` for OpenAPI and
use its Authorize control with a configured bearer token; docs require no AWS
credentials and do not initialize the provider or conversation database.

Identity resolution precedes session/model access. Provider and storage creation
are lazy after valid input/identity, with serialized factory initialization.
`create_app(service=..., identity_resolver=...)` and `get_service_factory` remain
available for deterministic composition/testing. These interfaces do not permit
an unauthenticated fallback in the running API.

## Configuration and history

| Setting | Default / supported range |
| --- | --- |
| `DATABASE_PATH` | `data/catalog.sqlite3`, imported read-only catalog |
| `OPERATIONS_DATABASE_PATH` | `data/operations.sqlite3`, required imported read-only customers/orders |
| `CONVERSATION_DATABASE_PATH` | `data/conversations.sqlite3`, separate writable storage |
| `CHAT_TIMEOUT_SECONDS` | 60, positive finite deadline |
| `HISTORY_MAX_TURNS` | 6, integer 1–20 |
| `HISTORY_MAX_CHARACTERS` | 24000, integer 1–64000 |
| `PIPELINE_LOGS` | 0; 1 enables metadata diagnostics |

Paths are relative to the server's working directory. The storage parent directory
must exist. Conversation files are created automatically with owner-only access;
owned existing files are reset to mode 0600. The repository rejects a foreign
SQLite schema, and configuration rejects path/alias collisions among catalog,
operations and conversation storage. The operational database must be imported
explicitly; missing/incompatible initial storage or invalid customer mappings fail 503.
Catalog import remains separate and cannot replace the conversation file.

All completed turns remain on disk until reset. The model receives only the newest
contiguous suffix of complete user/assistant pairs fitting both history limits.
The character budget counts saved conversational text, not instructions, the
current message (maximum 4000 characters), output, or token usage. No message is
partially truncated. If the newest saved turn alone exceeds the budget, history
is empty; the assistant must clarify references it cannot resolve. References in
retained answers preserve displayed product/order ordering. Historical prices,
stock and order answers are not current evidence: prompts require fresh tool retrieval. The adapter sends
conversation text without identity/session metadata or old tool returns. Trusted
ExecutionContext travels as per-run SDK dependencies for order tools; output notices
use messages stamped with the current SDK run ID, including corrective retries.

## Failures and completed turns

| Failure | Status |
| --- | --- |
| Missing/invalid bearer identity | 401, `WWW-Authenticate: Bearer` |
| Unknown or foreign session | 404, same safe detail |
| Overlapping turn or stale expected revision | 409, retry after the in-flight turn finishes |
| Invalid request | 422, generic detail without input values |
| Missing/invalid configuration or unavailable provider | 503 |
| Deadline/provider timeout | 504 |
| Retrieval, persistence, agent, or unexpected failure | 500, generic detail |

ChatService validates identity and loads owned history before execution. It rejects
same-session overlap while independent sessions can make model calls concurrently.
A complete user/assistant turn and revision increment commit atomically before
success is returned. Failures/cancellation before commit leave no completed turn.
A failed first call may leave an empty owned session; it is not a completed turn.

SQLite operations are synchronous, short, and use no busy wait. No transaction is
held across a model call. Cancellation is delivered and the deadline checked before
the final non-awaiting commit, preventing delayed worker writes after cancellation.
The final local filesystem commit cannot be asynchronously interrupted and can
briefly block the event loop; this is an intentional single-process demo tradeoff.
Unexpected external SQLite lock contention fails safely as a storage error.
Expected-revision append also rejects stale writes from separate service instances;
this does not claim distributed turn scheduling or multi-worker support.

A committed turn remains saved even if its HTTP response is lost. The client must
recover/reconcile before retrying; no exactly-once delivery or retry deduplication
is implemented. There is no transcript-list API in this story. Storage, model,
and network failures are never disguised as empty retrieval or successful turns.
For AWS profile diagnosis see [agent configuration](bedrock.md).

## Authorized order questions

With a valid imported customer mapping, send `{"message":"Quais são meus pedidos?"}`
and continue with `{"message":"Qual o status do primeiro?","session_id":"<returned-uuid>"}`.
The public shape is unchanged; never supply customer scope/history. Both order
tools derive scope from trusted execution context, and repository SQL independently
enforces it. Lists show up to 5 orders by default (maximum 20); details show up to
20 item rows with truncation metadata/notices. Unknown and foreign order IDs share
the same normal not-found-in-your-account result, rather than disclosing existence.
Known accounts without orders receive an empty result. Current lookup is required
for order facts; data is an imported snapshot, not live tracking or return eligibility.
Storage/tool failures are failures, with no completed turn. See [order contracts](orders.md).

## Direct application calls

Inside trusted application code, compose an agent and conversation repository,
resolve identity independently of model input, and call the same service:

```python
from pathlib import Path
from emporio_music_backend.application import ChatService
from emporio_music_backend.contracts import ChatRequest, ExecutionContext
from emporio_music_backend.infrastructure.conversations import SQLiteConversationRepository

# agent implements AgentExecutor; identity came from a trusted resolver.
service = ChatService(agent, SQLiteConversationRepository(Path("data/conversations.sqlite3")))
context = ExecutionContext(identity=identity)
first = await service.chat(ChatRequest(message="Procuro um violão"), context=context)
second = await service.chat(
    ChatRequest(message="Até R$1.000", session_id=first.session_id), context=context
)
```

ChatService requires identity-only context and loads history itself; supplied
session metadata/history is rejected. The lower-level AgentExecutor can still
execute owned history explicitly and returns AgentResponse, without saving turns.
Only ChatService returns ChatResponse with the durable session ID. Constructing a
CustomerIdentity value alone is not authentication of an external caller.

## Local reset

Stop the server and any other process using the conversation file. Confirm the
configured conversation path, then remove that file (and any SQLite journal
sidecars after processes have stopped). On the next valid request, the repository
creates empty storage. All previous session IDs become inaccessible. Keep catalog
and source CSV files intact. No automatic expiration, deletion endpoint, or schema
migration framework is included; do not remove a live database.

## Metadata diagnostics and evidence

Set `PIPELINE_LOGS=1` explicitly before startup to emit JSON on stderr with a fresh
request correlation ID. Supported events include HTTP status/timing, provider
setup, request/token counts, tool names/result counts, output-retry reasons,
truncation totals, and safe error classes/hints. Per-event allowlists exclude raw
messages, answers, history, query text, customer/session identifiers, credentials,
source paths, and tool rows. Unknown events carry no arbitrary fields. Third-party
SDK debug logging is not enabled. Omit the flag or set 0 to disable diagnostics.

Offline tests exercise real temporary SQLite, restart through new application
instances, referential product follow-ups, catalog re-import, changed prices,
isolation, cancellation/conflicts, rollback, and log privacy. Actual loopback
startup checks cover docs/401/422/503 without model calls. These do not establish
live Bedrock interpretation/answer quality; new multi-turn live evidence remains
explicitly opted in under US-13. Sprint 1's saved live captures are historical.
