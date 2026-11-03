# US-23 validation evidence

> Archived Sprint 4 validation record. Paths and commands below describe the
> repository layout at that time. For the current modular-monolith layout and
> commands, see the [README](../README.md) and [architecture](architecture.md).

Candidate base: `790feb1` (`integration/sprint-4`), validated on 2026-11-02.
The US-23 changes add the backend typing marker and reconcile submission docs.
This report records actual checks and their limits. In particular, the default
Docker bridge path failed host access; the documented Linux workaround passed.

## Quality checks

From the repository root, `make check` passed after adding the missing backend
`py.typed` marker. Initially CLI mypy failed with 17 `import-untyped` errors:
the standalone consumer could not see the installed backend as a typed package.
No type errors were suppressed and no tests were removed.

- Backend Ruff lint/format and strict mypy passed (91 source files).
- Backend pytest: 321 passed.
- CLI Ruff lint/format and strict mypy passed (3 source files).
- CLI pytest: 6 passed, including persistent guest/customer sessions, isolation,
  sanitized failures without resubmission, clean exit and provider-free help/import.
- Frontend npm install, lint, typecheck and production build passed.
- `npm ci` reported 10 moderate advisories. `npm audit` could not reach
  `registry.npmjs.org`, so affected packages could not be verified. No
  dependencies or lockfiles were changed for this validation story.
- `uv build --project apps/backend` and the CLI build in `make check` produced
  source distributions and wheels. The backend wheel contains `py.typed`.
- `sha256sum -c SHA256SUMS` from `data/` passed all seven supplied source checksums.

Tests use controlled agents and temporary storage. They prove application wiring,
session persistence across application instances, customer isolation and error
contracts; they do not prove autonomous real-model reasoning.

The initial sandbox run could not acquire the uv cache lock because its cache
directory was read-only. The same command completed with the required access.
Docker daemon access likewise required explicit sandbox elevation.

## Clean Docker setup and runtime

Built with `docker build -t emporio-da-musica:us23 /tmp/us23-clean` from a
`git archive 790feb1` export plus the new typing marker. The build context had no
credentials or generated databases/index/cache. Only `.env.example` was copied
as the runtime `.env`; its values were not real credentials. A network-disabled
fresh-image inspection confirmed absent SQLite/index/cache files and local
`.env`/`.aws` paths (empty runtime directories are expected).

An isolated Compose project, `us23-validation`, used the unchanged `compose.yaml`
plus a temporary image-tag override and `AWS_EC2_METADATA_DISABLED=true`. Existing
application volumes and local chat history were not used.

Executed preparation commands inside the isolated project:

```bash
docker compose run --rm app python -m emporio_music_backend.prepare
docker compose run --rm app python -m scripts.policy_benchmark.run --model e5 --index --allow-download --output-dir /tmp/policy-rag-bootstrap
```

The first imported 65 products, 25 promotions, 50 customers, 20 orders and 22 items.
The second downloaded pinned E5 weights, built Chroma and completed its existing
local development retrieval checks. It made no Bedrock calls. Image build and
normal startup performed neither initialization step.

The benchmark-runner command above is historical evidence from before runtime
index preparation was separated from evaluation. On the current checkout, it
builds under `data/policy-benchmark-indexes`; prepare the runtime collection with
`make prepare-policy` instead.

Normal Compose startup completed. Inside the container `/`, `/docs` and
`/openapi.json` returned 200. However, on this machine, host traffic to the
published loopback port timed out despite the running Docker proxy and correct
bridge route. This is an unresolved host/Docker bridge-ingress limitation; the
normal published-port path was **not** verified from the browser.

A temporary Linux host-network override made the same image accessible at
`127.0.0.1:8000`. Production startup returned the React page; the browser rendered
the chat and suggestions. This workaround preserves the single application
process and binds only to loopback. On Linux with Compose 2.24.4+ it can be
reproduced from the repository root after normal preparation:

```bash
cat > /tmp/emporio-host.yaml <<'YAML'
services:
  app:
    network_mode: host
    ports: !reset []
    command: [uvicorn, 'emporio_music_backend.api.app:create_app', --factory, --host, 127.0.0.1, --port, '8000']
YAML
docker compose -f compose.yaml -f /tmp/emporio-host.yaml up -d --no-build app
# Stop using the same configuration; the data volume remains.
docker compose -f compose.yaml -f /tmp/emporio-host.yaml down
```

This workaround was used for the remaining host/browser checks. It does not
establish that the default bridge works on this machine. No firewall, network
policy or production Compose configuration was changed.

## Controlled end-to-end checks

A disposable, uncommitted agent was injected through the existing
`create_app(chat_service=...)` seam. It returned an explicitly labelled controlled
answer with the history-derived turn number, or raised a known application error.
It used the real `ChatService`, SQLite history, API customer validation, HTTP
client and built React assets. It never constructed a Bedrock agent.

- UI/assets, `/docs` and `/openapi.json`: 200; unknown API routes retain 404.
- HTTP: two successful turns reused the same session; another selected customer
  and guest access both returned 404. Empty input and unknown customer returned
  422. A controlled provider failure returned a sanitized 503. New chat returned
  a different session at turn one.
- Browser: sent Markdown user text, displayed the controlled Markdown answer,
  continued at turn two, displayed the 503 message and used the new-conversation
  button to return to the welcome state and then start at turn one.
- Container teardown/recreation retained 58 runtime files totalling
  3,404,345,637 bytes. SHA-256 manifests matched for SQLite, Chroma and downloaded
  model-cache files. The earlier HTTP session resumed at turn three; its failed
  turn was not persisted. The isolated volume remains available after shutdown.
- After recreation, real local `LocalPolicySearch` ran with `HF_HUB_OFFLINE=1`
  against the persisted index/cache. This validates local retrieval, not generated
  policy answers. Allow roughly 3.4 GB of runtime data in addition to the image;
  preparation also needs download bandwidth and CPU memory for E5.

The first production-chat POST probe was rejected by automatic approval review
because it could incur Bedrock charges. It was not executed. The controlled
checks above were the safe alternative; no current production model response is
claimed. One temporary retrieval probe initially used a model-style serializer
on the dictionary result; correcting that diagnostic call required no app change.

## Standalone CLI setup

From the clean source export, `uv sync --project apps/cli` and
`uv run --project apps/cli -- emporio-music-chat --help` passed. The help lists
`--live` without constructing a provider. A direct injected-agent interactive run
covered guest selection, two turns, `/new`, customer 1 and `/exit` using temporary
history and the imported source snapshots. This was controlled execution without
HTTP, additional CLI dependencies or live model calls.

## Conversation evidence

[Four actual Portuguese conversations](examples/submission.md) cover catalog,
pricing, promotions, contextual follow-ups, scoped orders, policies and scope
redirection. These are historical captures with explicit model/date/revision
limits. Failed attempts and mixed-policy failures remain linked. No new Bedrock
calls were authorized or performed during these checks. The temporary validation
containers were stopped; the isolated `us23-validation_app-data` volume was retained.
