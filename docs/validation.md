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
uv sync --project apps/backend --locked
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests
uv run --directory apps/backend --locked pytest
uv run --project apps/backend --locked python -m \
  emporio_music_backend.infrastructure.catalog_import \
  --products data/products.csv --categories data/categories.csv \
  --database data/catalog.sqlite3
uv build --project apps/backend
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

## Subsequent live acceptance and remediation

The initial live-access deferral was resolved after key activation. The fresh-code
Bedrock probe and GD20 HTTP conversation passed. Original live scenarios exposed
truncation, availability-selection and output-markup defects; their captures remain
unchanged in examples/live/.

The remediation uses two tools with fixed availability semantics, a deterministic
per-run truncation notice, and one bounded corrective output retry. Five new live
captures in examples/live-recheck/ passed review against actual tool data. The
HTTP GD20 request returned 200 with correct price/stock and no control markup.

Current checks: 133 offline tests, strict mypy (32 files), Ruff lint/format passed.
Regression tests first reproduced raw-markup acceptance and absent truncation
disclosure before production changes. Existing integration assertions were updated
for the approved tool split; catalog semantics and public HTTP contracts remain.
The original 132-test fresh-environment results above are historical, before later
risk-based consolidation and the current regressions. See the live validation report
for failed baseline, remediation evidence and remaining scope boundaries.

Policy-aware answers/routing and final public-submission/cutoff checks remain
follow-up work; no live capture guarantees correctness for every future request.
