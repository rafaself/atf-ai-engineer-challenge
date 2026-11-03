# ADR-0005: Authorized operational snapshots

> Identity update: [ADR-0007](0007-simplified-demo-identity.md), accepted in #33,
> replaces tokens and mandatory customer identity with local fictional selection
> and guest sessions. Context separation and customer-scoped reads remain.

Historical decision record. [Issue #32](https://github.com/rafaself/atf-ai-engineer-challenge/issues/32)
simplifies persistence and import infrastructure. Expected revisions, cross-instance
coordination, exact DDL checks and runtime source fingerprints described below are
retired where applicable. See the current [architecture](../architecture.md).

Status: Accepted (offline import, authorization and HTTP integration evidence)

Related issue: [US-11 #25](https://github.com/rafaself/atf-ai-engineer-challenge/issues/25)

## Context

US-10 supplies trusted demo identities and owned persistent history. US-11 needs
customer-order facts without letting text, tools or cached agents select a different
customer. The original order data has historical totals but no item unit prices.
Customer CSV contacts and free-text notes are unnecessary for these operations.
The owner confirmed the data is fictional and approved committing the original bytes.

## Decision

Use a separate owned SQLite operational snapshot, populated by an explicit
validated importer. Store customer IDs, minimal order headers, quantities, and
referenced product IDs/names copied from a validated catalog transaction. Exclude
customer names/contacts/cities, notes and payment methods. Preserve historical
totals exactly; do not reconcile against current prices. Keep source CSV hashes and
a deterministic hash of the copied product-reference projection. Validate first,
then replace all owned rows atomically with rollback. Reject foreign schemas and
path collisions; create/private-reset owned files to 0600. No migrations or ORM.

Retain the approved server token mapping. Inject CustomerRepository into its
resolver, validate every mapping initially, and recheck the matched customer on
each resolution. Initial storage/configuration faults fail 503, invalid credentials
401, and runtime operational faults 500. A removed mapped customer fails configuration
rather than silently remaining authorized. A known customer without orders is valid.

Pass ExecutionContext as Pydantic AI per-run dependencies. Share product tools with
the full store composition; cached order tools retain repositories, never identity.
No customer argument is present in model-visible order schemas. Independently require
trusted scope in repository reads, validate identifiers, and parameterize ownership
on order/item/count SQL in one fresh read transaction. Unknown customers fail
authorization. Unknown and foreign orders share the same optional typed result and
safe tool response, without revealing existence in another account.

Bound order lists to 5 by default/20 maximum, date descending then ID descending.
Bound details to 20 item rows sorted by product ID, with explicit counts/truncation.
Append current-run Portuguese truncation notices from returned evidence. Send no
identity/session metadata or historical tool evidence as messages. History preserves
references, while instructions require fresh retrieval for order status/ownership.
Keep diagnostics metadata-only. HTTP composition requires all three independent
storage paths; isolated catalog probes are not a fallback for missing operations.

## Consequences

Atomic re-import removes absent records and refreshes future reads without mutating
conversations. Copied product references survive later catalog removal/renaming;
only an operational re-import updates them. A resolver check and subsequent order
read can see different committed snapshots; the repository rechecks customer and
ownership so removal between these steps fails closed. No database transaction spans
model execution. Old conversation answers may remain stale and are not evidence.

The local single-process demo adds no production dependencies. Owner-scoped SQL
protects record access independently of model wording. This does not establish
production authentication, live fulfillment, payment confirmation, return eligibility,
or universally grounded answers. Original fictional contacts remain in the approved
source fixture, not operational/model projections. The existing session deadline,
cancellation and commit-before-response limitations remain ADR-0004's contract.
Real provider/tool-selection evaluations remain explicitly opted in under US-13.

Real temporary SQLite tests cover replacement/removal, rollback, exact totals,
references, optional fields, minimal projections, bounded sorting and direct isolation.
Controlled HTTP tests cover session follow-ups across reconstruction/refreshed imports,
concurrent customers, forged scope, removed token mappings, empty accounts, failure
turn integrity and safe diagnostics. Two regressions were observed failing before
fixes: identity without required operational storage and missing order notices.
Other new tests were checked after implementation; they are not claimed as failing
baselines. See [operational guide](../guides/orders.md) and [actual checks](../validation.md).
