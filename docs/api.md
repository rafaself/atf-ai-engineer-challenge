# Local conversational API

Import the catalog using the README command, configure a project AWS profile as
[documented for Bedrock](bedrock.md), and run from the repository root:

```bash
uv run --env-file .env --project apps/backend --locked uvicorn emporio_music_backend.api.app:create_app \
  --factory --host 127.0.0.1 --port 8000
```

Then, in another terminal:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Qual o preço e estoque do Takamine GD20?"}'
```

A successful response contains only `{"answer":"..."}`. The supplied snapshot
lists GD20 at R$ 2.199,00 with five in stock. This is catalog snapshot evidence,
not a live inventory guarantee. Each request is independent; there is no history.

Open http://127.0.0.1:8000/docs for examples and interactive OpenAPI documentation.
Documentation and validation work without AWS credentials. A valid chat lazily
constructs the configured Bedrock client, repository and ChatService; AWS setup is
offloaded from the event loop. The factory can accept a ChatServicePort directly,
and tests can override get_service_factory through FastAPI dependency_overrides.
SQLite connections are short-lived and owned by each repository operation.

Export DATABASE_PATH to override data/catalog.sqlite3 (relative to the server's
working directory). CHAT_TIMEOUT_SECONDS defaults to 60 for the complete agent
conversation; individual provider request limits are described in bedrock.md.
Environment values are read on first valid chat and the service is then reused;
restart the process after changing configuration. No .env loader is installed.

| Failure | HTTP status |
| --- | --- |
| Invalid message/payload | 422 |
| Missing/invalid trusted identity for session/customer operations | 401 |
| Unknown or inaccessible conversation session | 404 |
| Concurrent conversation turn conflict | 409 |
| Missing/invalid configuration or unavailable provider | 503 |
| Conversation deadline/provider timeout | 504 |
| Conversation persistence, retrieval, agent execution, or unexpected failure | 500 |

If access keys are configured but chat still returns 503, an invalid `AWS_PROFILE`
may be selecting a nonexistent profile. See [agent configuration](bedrock.md)
for safe diagnosis, authentication options, and restart instructions.

Operational responses contain stable generic details rather than exception text,
SQL, provider payloads, credentials, or stack traces. HTTP validation retains
FastAPI's 422 details. This local evaluation server has no authentication and is
bound to loopback; public deployment is outside the sprint.

The 401/404/409 mappings prepare the application error boundary for US-10. They
do not mean this endpoint implements sessions or authentication today. Each HTTP
request supplies a new empty ExecutionContext internally. Client-supplied
session_id, customer_id, identity, history, and context fields are rejected with
422; no caller-provided history or customer selection reaches the agent.

Offline tests cover HTTP contracts, error mappings, docs/schema, and an actual
service → controlled agent → tool → temporary SQLite round trip. They cannot
establish Bedrock tool selection or generated-answer quality. The live GD20 HTTP
conversation returned 200 with the correct price/stock and clean customer text
after remediation. A placeholder profile still produces a sanitized 503.

## Direct application calls (US-09)

Trusted non-HTTP consumers can invoke an existing ChatService instance with
explicit application-owned history:

```python
from emporio_music_backend.contracts import (
    ChatRequest,
    ConversationMessage,
    ConversationSession,
    CustomerIdentity,
    ExecutionContext,
)

# Inside an async function, after resolving identity at a trusted boundary.
# This ID is illustrative: constructing CustomerIdentity does not authenticate it.
identity = CustomerIdentity(customer_id=1)
session = ConversationSession(owner=identity)  # server-generated UUID4
context = ExecutionContext(
    identity=identity,
    session=session,
    history=(
        ConversationMessage(role="user", content="Estou procurando um violão."),
        ConversationMessage(role="assistant", content="Qual seu orçamento?"),
    ),
)
response = await service.chat(ChatRequest(message="Até R$1.000"), context=context)
```

Here service is an explicitly composed ChatService with an AgentExecutor; creation
is separate from this snippet. Both chat(request, *, context) and
run(request, *, context) require the keyword argument. For a stateless call, pass
ExecutionContext(). The service and adapter revalidate supplied contexts before
model execution. Nonempty history requires a session with matching trusted identity,
and complete alternating user/assistant pairs. System/tool roles are not accepted.
Only text history reaches the provider, without identity/session metadata or old
tool returns. The cached executor retains no session history between calls.

These calls neither save turns nor check session existence in a database. Trusted
callers must supply authentic session metadata and history; the UUID alone is not
proof of ownership. Context size/retention limits and restart persistence are US-10.
Historical answers provide conversational references, not current prices or stock:
tools must retrieve mutable facts again. Controlled-model tests verify this wiring,
not natural-language correctness or a prompt-injection guarantee.

### Session and identity handoff to US-10

The approved local demo uses `Authorization: Bearer <demo-token>`, resolved through
a server-side token-to-customer mapping implementing CustomerIdentityResolver.
The adapter/configuration parser is not implemented in US-09; no token environment
variable is supported yet. Tokens must never enter public chat fields, context
values, model messages, diagnostics, or committed examples.

US-10 will create an owned session when session_id is omitted, return its identifier,
and load persisted history only after identity resolution and ownership checks.
An explicit malformed ID is invalid input; an unknown/foreign ID must yield the
same sanitized 404 without creating or switching sessions. Missing/invalid identity
yields 401; identity changes cannot reassign an existing session. Same-session
overlap yields 409, and failed persistence yields a generic 500. Catalog-only
stateless HTTP access remains the current implemented behavior until that story.

## Temporary terminal pipeline logs

Enable project diagnostics explicitly when starting the local server:

```bash
PIPELINE_LOGS=1 uv run --env-file .env --project apps/backend --locked \
  uvicorn emporio_music_backend.api.app:create_app \
  --factory --host 127.0.0.1 --port 8000 --log-level info
```

Each line is JSON on stderr. Valid chat requests receive a generated request_id
shared across worker-thread events. Follow http.request → composition/provider
(on first construction) → chat.started → agent.started → tool.called →
catalog.search/result → tool.result → output.accepted → agent.completed →
http.response. Direct answers omit tool/database events; output.rejected marks a
corrective retry. Agent completion includes model-request count and input/output
tokens; HTTP completion includes elapsed milliseconds. Tool results include
returned products, total matches and truncation. CSV imports also emit start/count
summaries when PIPELINE_LOGS=1. This traces application stages, not SDK wire traffic.

For a 503, http.failure/provider.failure show cause class names and a safe AWS
error code/hint when available, such as ProfileNotFound. Raw SDK exception bodies,
AWS configuration values and rejected internal model text are not dumped. Payload
validation failures still appear in uvicorn's normal access logs as 422.

This is temporary, local diagnostics. It includes chat messages, validated final
answers, query filters and catalog rows. Active AWS access-key/secret/session-token
values are redacted if echoed in text; this is not general personal-data redaction.
Do not share raw logs containing customer or other sensitive input. Only the
project logger is enabled; boto3/botocore debug logging is not enabled. Set
PIPELINE_LOGS=0 or omit it to disable these logs; restart the server after changing
its environment. No telemetry service or new dependency is required.
