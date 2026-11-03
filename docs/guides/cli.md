# Interactive Python CLI

The CLI calls the shared package's `ChatService` directly. It does not start an
HTTP server, add a separate conversation database, or load environment files on its
own. Conversation history uses the shared configured data directory;
the repository-root default remains `data/conversations.sqlite3`.

From the repository root, install the CLI package and prepare the existing catalog
and fictional-customer snapshots:

```bash
uv sync --project apps/cli --locked
uv run --project apps/cli --locked python -m emporio_music.prepare
```

With AWS/Bedrock configuration in a local `.env`, start an explicitly opted-in live
conversation:

```bash
uv run --env-file .env --project apps/cli -- emporio-music-chat --live
```

`--live` permits real Bedrock requests, which may incur charges. The command does
not download model weights or prepare the policy index. If AWS settings are already
exported in the shell, omit `--env-file .env`. Keep the file local and out of Git.
To enable policy queries, install the existing optional policy-RAG dependencies and
follow the explicit setup in [policy retrieval](policy-retrieval.md):

```bash
uv sync --project apps/cli --locked --extra policy-rag
```

Choose `g` for guest mode or enter an existing fictional customer ID. Enter
`/new` to start another session and choose an identity again; `/exit`, Ctrl-C or
EOF exits. Customer identity is fixed within each session and is never inferred
from chat text. The CLI does not automatically retry failed messages.
