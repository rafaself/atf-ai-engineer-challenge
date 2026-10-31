# Local conversational API

Import the catalog using the README command, configure a project AWS profile as
[documented for Bedrock](bedrock.md), and run from the repository root:

```bash
uv run --project apps/backend --locked uvicorn emporio_music_backend.api.app:create_app \
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

Operational responses contain stable generic details rather than exception text,
SQL, provider payloads, credentials, or stack traces. HTTP validation retains
FastAPI's 422 details. This local evaluation server has no authentication and is
bound to loopback; public deployment is outside the sprint.

Offline tests cover HTTP contracts, error mappings, docs/schema, and an actual
service → controlled agent → tool → temporary SQLite round trip. They cannot
establish Bedrock tool selection or generated-answer quality. The live curl
conversation remains deferred until the user confirms an AWS profile; a
placeholder profile returns a sanitized 503 rather than a fabricated answer.
