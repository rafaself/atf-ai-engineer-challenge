# Sprint 1 validation evidence

Validated on 2026-10-31 with Python 3.12.15 and uv 0.13.4. US-04–US-08
implementation was delivered in dependency order, with checks and primary-agent
code review before each merge. This is a foundation slice, not full challenge
acceptance. No independent reviewer or hosted CI success is claimed.

## Fresh local environment

A disposable source copy included current tracked/proposed files and excluded
Git metadata, virtual environments, caches, generated databases and local .env.
It used an empty home directory and removed AWS/model/chat configuration variables.
These documented root commands passed:

```bash
uv sync --project backend --locked
uv run --directory backend --locked ruff check .
uv run --directory backend --locked ruff format --check .
uv run --directory backend --locked mypy src tests
uv run --directory backend --locked pytest
uv run --project backend --locked python -m \
  emporio_music_backend.infrastructure.catalog_import \
  --products data/products.csv --categories data/categories.csv \
  --database data/catalog.sqlite3
uv build --project backend
(cd data && sha256sum --check SHA256SUMS)
```

Results: **132 tests passed**, strict mypy passed for 30 source/test files, Ruff
lint/format passed, 9 categories and 65 products imported, source/wheel builds
passed, CSV checksums matched. Locked sync preserved the lockfile SHA-256:
`d205707792491f800ab9c6b42a52f40bf2db910a36908aa403fcec853bced088`.

The built wheel was installed in a second disposable environment with runtime
dependencies only. It imported and constructed the API/OpenAPI schema outside the
source tree while boto3 Session construction was forbidden. Pytest was absent.

Actual uvicorn factory startup on loopback was verified: /docs returned 200,
blank payload returned 422, and a deliberately nonexistent AWS profile produced
a sanitized 503 for a valid message. The temporary server was stopped afterward.
These checks did not invoke a model or prove a live conversation.

## Domain and integration evidence

Existing tests cover validated immutable values, source integrity, atomic
replacement/rollback, incompatible database rejection, read-only retrieval,
normalized literal filters, integer money/overflow and status/availability.
Application/adapter tests cover usage limits, error categories, deadline,
cancellation, statelessness and imports without provider initialization.

Selected HTTP → real ChatService → controlled SDK tool → temporary SQLite tests
verify the supplied snapshot: 12 available violões at or below 100000 centavos,
default 10-result truncation, GD20 at 219900 centavos with stock five, GF-3D excluded
from available-only results but returned with stock zero when explicitly allowed,
and successful empty results for an unmatched name. Those fixture facts are not
embedded in the production prompt. HTTP errors are sanitized and docs/schema match
the actual contracts. Controlled answers do not evaluate natural-language quality.

Review covered dependency direction, request validation before AWS setup,
thread/connection ownership, safe errors, strict tool arguments, exact conversion,
and evidence authenticity/preservation. Findings fixed during the sequence include
Decimal-context rounding, boolean limit coercion, catalog preflight before a paid
capture, and the SDK's deprecated usage accessor. No unresolved code findings remain.

A credential-pattern scan of current tracked/proposed files and locally reachable
Git history found no AWS access-key/secret assignments or private-key markers.
No local environment or generated database is tracked; ignore rules cover these
artifacts. This targeted scan does not establish that arbitrary secrets can never
exist. No credentials were added or used for model access.

## Explicitly deferred acceptance

- Real Bedrock model access/tool calling in us-east-1 (preferred Nova Micro).
- Natural-language tool selection and generated answer grounding/scope handling.
- Live HTTP conversation with the configured model.
- 3–5 reviewed real conversation artifacts in docs/examples/.

The user deferred project AWS profile configuration. These checks remain incomplete;
no mocked output is saved as real evidence. The opt-in probe and live recorder are
ready, but have not been executed against Bedrock. Follow [the capture checklist](examples/README.md)
after access is confirmed. Policy-aware answers/routing and final submission work
are tracked in [follow-up scope](follow-up.md).
