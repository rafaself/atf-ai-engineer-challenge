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

## US-09 session/context validation — 2026-10-31

The US-09 branch adds owned session/message/context contracts and direct execution
of explicitly supplied trusted history. The HTTP API remains stateless. Actual
checks from the repository root passed:

```bash
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests
uv run --directory apps/backend --locked pytest
uv build --project apps/backend
(cd data && sha256sum --check SHA256SUMS)
```

Results: **150 tests passed**, strict mypy passed for 36 source/test files, Ruff
lint/format passed, source/wheel builds passed, both catalog CSV checksums matched.
The full pytest run removed AWS credential/profile/region environment variables;
the autouse model-request guard remained enabled. No live model call was made.
The existing packaging/import-boundary tests passed; a new clean-environment
installation or runtime-only wheel installation was not repeated for this story.

Before adding rule validation, two tests reproduced acceptance of incomplete
history and missing/mismatched identity. After adding the contracts, three
execution tests reproduced the missing context parameter before propagation and
translation were implemented. The later controlled-model/SQLite regression was
added after implementation; no failing baseline is claimed for that check.

Current evidence covers history ordering, immutable independent contexts, safe
ownership rejection at both service and direct adapter entry points, concurrency
isolation without retained state, unchanged HTTP input/output shapes, forbidden
client context fields, and sanitized 401/404/409/500 mappings. Existing catalog,
provider-error, output-validation, deadline, cancellation, and package/import
checks remain in the passing suite. The source CSVs and dependency lockfile are
unchanged.

This does not prove real authentication, session lookup/persistence, restart
recovery, bounded context selection, concurrent persistent writes, or live model
quality. Those remain US-10/US-11/US-13 as documented in ADR-0003. PR delivery is
pending review; no merge or full Sprint 2 acceptance is claimed.

## US-10 persistence validation — 2026-10-31

Actual root-level Ruff lint/format checks, strict mypy, pytest, and `uv build
--project apps/backend` passed. Results: **168 offline tests passed**, strict mypy
passed for 43 files, source/wheel builds passed, and the supplied CSV checksums
matched. The final full pytest run removed AWS access-key/secret/session-token,
profile, and region environment variables; the live-model request guard stayed on.
Dependency declarations, lockfile, and source CSV bytes are unchanged.

The HTTP contract now intentionally requires demo identity, accepts an optional
continuation UUID, and returns a required session ID. Tests were updated from the
superseded stateless service/API assumptions using issue #24's requirements; no
catalog assertions were weakened. A dropped product-name query filter introduced
while removing log fields was caught by existing regressions and restored.

Three regressions were observed failing before their fixes: unauthenticated chat
returned 200, historical tool evidence appended an unrelated truncation notice,
and an existing/copied database retained public-read permissions. Other added
storage/service integration cases were checked after implementation; no test-first
baseline is claimed for them.

Real temporary SQLite and controlled models verify complete-turn atomicity,
rollback/retry, ownership, bounded coherent history, stale-revision conflicts,
independent-session progress, cancellation/timeout without completed turns, new
repository/service/application instances resuming state, catalog re-import safety,
and a retained second-product reference followed by retrieval of a changed price.
Enabled diagnostics omit raw messages, answers, query strings, customer/session
identifiers, tokens, and result rows. These checks prove wiring and data boundaries,
not natural-language understanding or universal model grounding.

An actual uvicorn process on an ephemeral loopback port returned `/docs` 200,
missing identity 401, invalid authenticated input 422, and a generic 503 for a
valid demo token with a deliberately nonexistent AWS profile. The process was
stopped; no live provider call occurred and no token appeared in captured server
output. The setup used temporary conversation storage and synthetic identity.

No new clean-environment/runtime-only wheel installation or live multi-turn
Bedrock evaluation was performed. Existing package/import tests passed; fresh
provider conversations remain US-13. The short synchronous SQLite commit and
commit-before-response loss boundary are documented in ADR-0004 and the API guide.
