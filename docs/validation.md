# Current guest/demo-selection verification

Issue #33 removes demo bearer mapping, token parsing/digests/comparison, the
resolver and its unused protocols. Guests and selected fictional customers share
the existing bounded SQLite conversation service. Non-null customer selection is
HTTP-validated on every request and kept out of agent input/model tool arguments.
Session mode/customer mismatches fail before model execution. Guest order tools
return a selection-required message without reading customer orders.

Three new guest regressions were observed failing with 401 before implementation:
guest restart/history continuity and both order-tool guards. They pass afterward.
Other new/extended checks were verified after implementation; no failing baseline
is claimed for them. Token/no-guest assertions are replaced because the owner
explicitly superseded those requirements in #33. Order-query scoping, forged tool
arguments, historical evidence, storage failure, cancellation, bounded history,
atomic turns, pricing and diagnostics remain covered. Promotion/PIX integration
now exercises both guest and selected-customer modes.

From the repository root, the README Ruff lint/format, strict mypy (**69 files**),
**249 offline tests**, and source/wheel builds passed. AWS configuration variables
were removed; default tests prohibit live model requests. No live provider or
language-quality acceptance is claimed. All 14 supplied CSV/PDF files retain their
original bytes. No production dependencies or lockfile changes were introduced.

Conversation schema v2 supports null guest owners. Older v1 files are rejected
unchanged; use a fresh configured path and retain prior history files. There is no
migration or automatic reset. ADR-0007 is Accepted after the delivery review.
The pre-merge review found no functional blockers or need for additional
abstractions. The full README checks were rerun: 249 tests, Ruff, strict mypy
(69 files), source/wheel builds and all 14 source byte checks passed. No live
model calls were made; this is Codex review, not independent model-quality acceptance.
Earlier records below describe intermediate implementations and historical auth.

# Earlier naming verification

The approved naming follow-up completes the `chat_service_factory` rename in the
API, dependency overrides and documentation. Names now identify factory roles,
chat-service initialization, database paths, chat requests, request-context reset
tokens, import reports and the catalog snapshot hash. CLI flags and HTTP payloads
are unchanged; there are no compatibility aliases or new dependencies.

The full shared checkout now passes Ruff lint/format, strict mypy (**70 files**),
**237 tests** and source/wheel builds. AWS configuration variables were removed
and live-model requests remained forbidden. The previous API factory import
mismatch is resolved; isolated-copy verification is no longer needed for that
reason. All supplied CSV/PDF bytes remain unchanged. Earlier records below describe
the intermediate work, including the then-incomplete user rename.

# Earlier package verification

The package-cohesion follow-up in issue #32 moves contracts/protocols out of
initializers into defining modules. All callers/tests use explicit imports;
`ChatServicePort` is in `ports.chat`, with `ChatService` in `application.chat`.
The moved definitions have unchanged ASTs. A structural regression failed before
these changes; the boundary probe now imports every core module, checking that
minimal initializers do not hide provider or SQLite dependencies.

The isolated committed copy passed locked sync, Ruff lint/format, strict mypy
(**70 files**), **237 tests**, and source/wheel builds. The built wheel was installed
into the disposable verification environment; all core modules and defining imports
worked outside the source tree without HTTP/AWS/SQLite/Pydantic AI imports.
No live provider call was made. Source files, dependencies and the lockfile remain
unchanged. The existing unrelated API rename is preserved in the working tree;
only this refactor's import declarations are committed from that file. Its old-name
test-import mismatch still prevents claiming a full working-tree pass.

# Initial demo simplification verification

Issue #32 simplifies the existing challenge demo while keeping persistent SQLite
history and customer-scoped tools. The README is now the primary setup guide.
Historical sprint records follow below; their earlier revision/provenance claims
are not the current contract.

The exact committed simplification was verified in an isolated source copy with
`uv sync --project apps/backend --locked`, the README Ruff lint/format commands,
strict mypy, pytest and package build. Results: **236 tests passed**, strict mypy
passed for 58 source/test files, Ruff passed, and source/wheel builds passed.
AWS configuration variables were removed and the live-model guard stayed enabled.

Two regressions were observed failing before their fixes: an extra nullable product
column invalidated exact-DDL checks, and two discounted products repeated the full
snapshot disclaimer twice. New preparation tests verify both data stores, repeat
runs, source/history preservation, no runtime fingerprint metadata, and path collisions.
Other new tests were checked after implementation; no failing baseline is claimed.

The approved single-service/process boundary retires cross-instance stale-revision
coordination. Only that dedicated test and stale-append subcase were removed;
expected-revision parameters/assertions were replaced by saved-history assertions.
Runtime fingerprint checks were removed with their retired metadata. Ownership,
atomic failure/rollback, restart history, bounded context, same-session overlap,
independent chats, cancellation, pricing, tools and safe diagnostics remain tested.

An actual temporary uvicorn server and the new one-command preparation passed
loopback docs/401/422/503 checks using an invalid AWS profile. Preparation loaded
65 products, 25 promotions, 50 customers, 20 orders and 22 item rows. The server
stopped, without a model call or logged token. All 14 original CSV/PDF byte checks
passed. No dependencies or lockfile changed.

An unrelated API naming edit appeared in the shared checkout during validation.
It leaves `test_api.py` importing the old factory name, causing mypy/collection
failure in that working tree. It is preserved and excluded from this PR. The clean
committed copy described above passed independently. No working-tree-wide pass,
hosted CI success, independent review or live Bedrock acceptance is claimed.

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

## US-11 authorized orders validation — 2026-10-31

The README root commands passed: Ruff lint and format checks, strict mypy for
52 source/test files, **208 offline tests**, and `uv build --project apps/backend`
(source distribution and wheel). A final full pytest run removed AWS access-key,
secret, session-token, profile and region variables; the autouse live-model guard
remained enabled. All five `data/SHA256SUMS` entries matched. Each of the three new
fictional CSVs also matched its original ZIP entry byte-for-byte. Existing catalog
CSV bytes, dependency declarations and the uv lockfile remain unchanged.

Two regressions were observed failing before their fixes: configured identity
was accepted without operational storage, and truncated order results produced no
output notice. Other new tests were added after implementation; no failing baseline
is claimed for them. Initial test fixture corrections used source evidence: product
IDs start at 81, and exact money comparisons must allow source totals written
without decimal places. No domain assertions were weakened to obtain a green suite.

Real temporary SQLite tests verify repeatable imports, full replacement/removal,
write rollback, malformed headers/duplicates, positive 64-bit IDs/quantities, exact
centavo totals, supported dates/statuses and all references. They cover optional
tracking/estimates, known customers with no orders, consistent empty snapshots,
minimal stored projections, source hashes, logical catalog-reference fingerprints,
and copied product references surviving later catalog removal/renaming. Scoped
reads enforce customer ownership directly, independently of transport/model behavior;
foreign and unknown orders are indistinguishable. Read failures remain errors.

Authenticated HTTP → ChatService → controlled SDK → order tools → SQLite checks
cover list/detail follow-ups across application reconstruction and refreshed snapshots,
concurrent customers sharing a cached executor, invalid/forged tool arguments,
forged payload/message scope, missing/unknown identities, foreign sessions/orders,
empty accounts, removed configured customers after re-import, path collisions, and
storage failures without completed turns. Tool schemas expose no customer scope;
trusted identity/session metadata stays outside model messages. Diagnostics exclude
credentials, contacts, identifiers, tracking payloads and result rows. Existing
catalog/session, timeout, cancellation, output and import-boundary regressions pass.

The documented catalog and operational importer CLIs were run against temporary
paths: 9 categories/65 products, then 50 customers/20 orders/22 items. An actual
uvicorn factory on an ephemeral loopback port returned docs 200, missing identity
401, invalid authenticated input 422 and safe 503 with a deliberately nonexistent
AWS profile. The temporary server was stopped and its captured output contained
no synthetic token. No provider invocation occurred.

The final diff was reviewed locally for SQL ownership, source/derived projections,
atomic import, per-run dependency/state isolation, error propagation and docs.
No independent review, new clean-environment/runtime-only wheel install or live
Bedrock evaluation is claimed. Controlled models prove wiring/data boundaries,
not natural-language interpretation, adversarial prompt resistance, Portuguese
answer quality or universal semantic grounding. Real multi-turn evaluation remains
explicitly opted in under US-13; US-12 promotions stay deferred.

## US-12 promotions validation

The user scheduled the previously deferred story with an explicit immutable-source
requirement. All 13 previously present CSV/PDF files matched their before/after
checksums, including the original resource directory. The new `data/promotions.csv`
copy matches both the original ZIP entry and extracted supplied file byte-for-byte.
The existing five-entry checksum manifest remains unchanged and passes. No source
values, records, columns, dates, encoding or line endings were rewritten. Invalid
input tests create independent temporary CSV fixtures. No new hashing subsystem,
production dependency or database path was introduced.

Actual root-level README Ruff lint/format, strict mypy (56 source/test files),
pytest (**234 tests**), and `uv build --project apps/backend` passed. The final
suite removed AWS access-key/secret/session-token, profile and region environment
variables; the live-model request guard remained enabled. Source distribution and
wheel builds passed. Dependency declarations and lockfile remain unchanged.

Two regressions failed before implementation: the supplied active Kalani offer
had no separate final-price quote, and discounted results had no current-run price
disclosure. Other added cases were verified after implementation; no failing
baseline is claimed for those. One controlled-model fixture initially used only
the brand Ohana, which correctly returned multiple matches. It was corrected to
preserve and query the displayed full product name; production matching rules
and the expected promotional price were not weakened.

Real SQLite tests verify all 25 source promotion records, four active offers,
source prices, exact half-up ties and large integer arithmetic, promotion-first
PIX exclusion, unavailable statuses/stock, payable-price boundaries/order, bounded
counts, invalid references/flags/percentages, conflicts, atomic rollback, replacement
and empty offers. Existing catalog snapshot consistency and customer-order/session
regressions pass. Controlled HTTP tests exercise promotional ordering, product
follow-ups, PIX, application reconstruction, refreshed snapshots, concurrent payment
choices, historical order totals, safe diagnostics and failed turns without commits.

The updated importer CLI actually loaded 9 categories, 65 products and 25 promotions
into temporary catalog storage, followed by 50 customers/20 orders/22 items into
separate operations storage. An actual temporary uvicorn process returned docs 200,
missing identity 401, invalid authenticated input 422 and sanitized 503 with a
purposefully nonexistent AWS profile. The process stopped, and its captured output
contained no synthetic token. No provider invocation occurred.

Catalog schema version 2 intentionally requires regeneration of disposable old
catalogs; no source edits or migration layer are involved. The final diff was
reviewed locally for source immutability, atomic import, price/availability rules,
strict tool inputs and evidence boundaries. No independent review, fresh runtime-only
wheel installation or live pricing/language evaluation is claimed. Original live
captures are preserved and predate this feature. Real promotion/PIX and multi-turn
Bedrock evaluation remains explicitly opted in under US-13.
