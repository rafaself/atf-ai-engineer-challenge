# Interactive Python CLI

The CLI calls the shared package's `ChatService` directly. It does not start an HTTP server, add a separate conversation database, or load environment files on its own. Conversation history uses the shared configured data directory; the repository-root default is `data/conversations/conversations.sqlite3`.

From the repository root, install the CLI package and prepare the existing catalog and fictional-customer snapshots:

```bash
uv sync --project apps/cli --locked
uv run --project apps/cli --locked python -m emporio_music.prepare
```

With AWS/Bedrock configuration in a local `.env`, start an explicitly opted-in live conversation:

```bash
uv run --env-file .env --project apps/cli -- emporio-music-chat --live
```

`--live` permits real Bedrock requests, which may incur charges. The command does not download model weights or prepare the policy index. If AWS settings are already exported in the shell, omit `--env-file .env`. Keep the file local and out of Git. To enable policy queries, install the existing optional policy-RAG dependencies and follow the explicit setup in [policy retrieval](policy-retrieval.md):

```bash
uv sync --project apps/cli --locked --extra policy-rag
```

The CLI uses the same fixed fictional customer ID `1` as the HTTP and React demo.
It checks that customer against the current operational snapshot for each turn and
does not prompt for identity. Customer `1` owns order `4`, whose imported tracking
code `BRQM7890123BR` can be used in the demo. `/new` starts another session under
the same identity; `/exit`, Ctrl-C or EOF exits. Identity is never inferred from
chat text, and the CLI does not automatically retry failed messages. This is demo
context, not authentication.
