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
| Missing/invalid configuration or unavailable provider | 503 |
| Conversation deadline/provider timeout | 504 |
| Retrieval, agent execution, or unexpected internal failure | 500 |

If access keys are configured but chat still returns 503, an invalid `AWS_PROFILE`
may be selecting a nonexistent profile. See [troubleshooting](troubleshooting.md)
for safe diagnosis, authentication options, and restart instructions.

Operational responses contain stable generic details rather than exception text,
SQL, provider payloads, credentials, or stack traces. HTTP validation retains
FastAPI's 422 details. This local evaluation server has no authentication and is
bound to loopback; public deployment is outside the sprint.

Offline tests cover HTTP contracts, error mappings, docs/schema, and an actual
service → controlled agent → tool → temporary SQLite round trip. They cannot
establish Bedrock tool selection or generated-answer quality. The live GD20 HTTP
conversation returned 200 with the correct price/stock and clean customer text
after remediation. A placeholder profile still produces a sanitized 503.

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
