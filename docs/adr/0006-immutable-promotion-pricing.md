# ADR-0006: Immutable promotion sources and exact pricing

Historical decision record. [Issue #32](https://github.com/rafaself/atf-ai-engineer-challenge/issues/32)
simplifies persistence and import infrastructure. Expected revisions, cross-instance
coordination, exact DDL checks and runtime source fingerprints described below are
retired where applicable. See the current [architecture](../architecture.md).

Status: Accepted (offline import, arithmetic and HTTP integration evidence)

Related issue: [US-12 #26](https://github.com/rafaself/atf-ai-engineer-challenge/issues/26)

## Context

The user scheduled the previously deferred promotion story and requires every
supplied CSV/PDF to remain unchanged. The promotions source has 25 records, four
active, and no dates. Catalog prices and historical order totals must be preserved.
The challenge needs a simple implementation, not another database or rules engine.

## Decision

Copy promotions byte-for-byte and require that source in the existing catalog
import. Validate before an atomic replacement of all three catalog datasets.
Store inactive records too; validation reports errors and never repairs sources.
Use schema version 2 and explicitly regenerate disposable version-1 catalogs,
without migrations or compatibility fallbacks. Operational/conversation stores stay
independent. Reject duplicate active offers per product rather than choosing one.

Use only the supplied active flag for snapshot validity. Do not infer dates from
campaign labels. For available products, an eligible promotion takes priority;
otherwise explicitly requested PIX uses 5%, otherwise retain original price.
Unavailable products receive no discount offer. Integer arithmetic rounds the final
price half-up; discounts never stack. A single pure application function owns this
rule, keeping stored prices/promotion values and historical orders unchanged.

Extend product queries/tools with standard/PIX selection and a promotion-only
search filter. Preserve original price fields and add a typed quote containing the
final price, applied percentage and discount source. Read one consistent snapshot,
then calculate/filter/sort/count/limit in Python: the supplied catalog has 65 rows,
so no SQL arithmetic, paging infrastructure or generalized pricing engine is needed.
Append factual price disclosures using current-run tool results, without replaying
historical evidence. Diagnostics remain metadata-only.

## Consequences

Import setup gains one required path and old generated catalogs must be recreated.
Payable-price filtering intentionally includes products whose original price exceeds
a budget but whose eligible final price fits. Python integers avoid SQL overflow
and floating-point/Decimal-context rounding. All source values and files remain
unchanged; invalid tests use independent temporary fixtures. No production dependencies,
new storage path, calendar subsystem, checkout, policy RAG or order mutation is added.

Real SQLite and controlled HTTP tests verify exact totals, atomic replacement,
source preservation, availability, PIX non-stacking, budget boundaries and refreshed
follow-ups. Two failing regressions were observed before implementation. Other new
tests were checked after implementation. Controlled answers prove wiring, not live
Portuguese interpretation or semantic grounding; explicitly opted-in evaluation
remains US-13. See [catalog behavior](../guides/catalog.md) and [validation](../validation.md).
