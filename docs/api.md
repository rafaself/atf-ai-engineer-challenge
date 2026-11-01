# Local chat API

Use the [README](../README.md) for the two preparation/run commands. Run one uvicorn
process on loopback. Setup reads the same environment paths as the API and never
opens the conversation database. The application does not load `.env` automatically;
`uv --env-file .env` does. Existing shell variables take precedence.

## Demo identity setup

Generate a private URL-safe token using the README command, then set this in the
ignored `.env` (replace the placeholder):

```text
DEMO_CUSTOMER_TOKENS_JSON='{"<generated-token>":1}'
```

Mapped IDs must exist in imported customers. The resolver checks every configured
mapping initially and rechecks the matched customer on resolution. Tokens use
32–256 ASCII letters/digits/underscores/hyphens; IDs are positive integers. Token
digests are retained, and credentials never enter model messages or execution context.
Restart after changing mappings. This is a demo identity mechanism, not production auth.

## Requests

Set `DEMO_CUSTOMER_TOKEN` in the client terminal to a configured token, then:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/chat \
  -H "Authorization: Bearer $DEMO_CUSTOMER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Quais violões custam até R$1.000?"}'
```

Successful responses contain `answer` and a UUID4 `session_id`. Supply that ID to
continue, or omit it to start a chat. Null/invalid IDs are rejected. Unknown and
foreign IDs never create/reassign a session. Payload fields for customer identity,
history, context and payment are forbidden; payment selection comes from the message
through typed tools. Message length is limited to 4,000 characters.

Try promotions followed by `E o segundo no PIX?`, or an order-list/detail follow-up.
History survives server restarts. Tools retrieve fresh facts for each factual claim;
previous answers are conversational context. Docs/OpenAPI require no provider setup.

## Configuration

| Setting | Default |
| --- | --- |
| `DATABASE_PATH` | `data/catalog.sqlite3` |
| `OPERATIONS_DATABASE_PATH` | `data/operations.sqlite3` |
| `CONVERSATION_DATABASE_PATH` | `data/conversations.sqlite3` |
| `CHAT_TIMEOUT_SECONDS` | 60 seconds |
| `HISTORY_MAX_TURNS` | 6; supported 1–20 |
| `HISTORY_MAX_CHARACTERS` | 24000; supported 1–64000 |
| `PIPELINE_LOGS` | 0; set 1 for metadata diagnostics |

Paths are relative to the working directory and must be separate. Conversation
files are created privately; their parent directory must exist. Preparation refreshes
only source snapshots. A leftover pre-US-12 catalog needs a fresh configured path
or recreation of that generated file. Source files and chat history must remain intact.

## Errors and persistence

| Case | Status |
| --- | --- |
| Missing/invalid identity | 401 |
| Unknown/foreign session | 404 |
| Another turn is active on this session in this service | 409 |
| Invalid request | 422 |
| Missing configuration, invalid mapping or unavailable provider | 503 |
| Deadline/provider timeout | 504 |
| Retrieval, persistence or execution failure | 500 |

Details are sanitized. A valid empty result differs from a retrieval failure. One
service rejects overlapping turns on a session while independent sessions can run
concurrently. A complete user/assistant pair saves atomically before success. There
are no expected revisions or cross-instance guarantees. Run one process/service.
Failed/cancelled executions save no completed turn. Response loss after commit can
still leave a saved turn; automatic retry deduplication is outside the demo.

## Direct application calls

Trusted code calls `ChatService.chat(request, context=ExecutionContext(identity=...))`.
The service loads history itself; externally supplied session metadata/history is
rejected. The lower-level agent can execute explicitly trusted owned history without
saving it. A CustomerIdentity value alone does not authenticate an external caller.

`create_app(service=..., identity_resolver=...)` supports controlled tests. Default
composition retains trusted customer checks for all chats. Stop the server before
manually resetting conversation storage; removing it makes old session IDs inaccessible.
Diagnostics contain counts, timings and safe error classes, not raw messages, answers,
identifiers, credentials or tool rows. See [architecture](architecture.md) and
[provider setup](bedrock.md) for remaining execution limits.
