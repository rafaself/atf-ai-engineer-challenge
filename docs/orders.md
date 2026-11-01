# Authorized order snapshots

US-11 adds read-only account orders to the authenticated local demo. The project
owner confirmed the supplied customer/order data is fictitious and approved its
publication. Original CSVs, provenance and SHA-256 checksums are in [data](../data/README.md).
This is snapshot retrieval, not production authentication or a fulfillment system.

## Required import

For normal setup use the single [README preparation command](../README.md#run-locally).
For a focused operational refresh after catalog setup, the individual importer is:

```bash
uv run --project apps/backend --locked python -m \
  emporio_music_backend.infrastructure.operations_import \
  --customers data/customers.csv \
  --orders data/orders.csv \
  --order-items data/order_items.csv \
  --catalog data/catalog.sqlite3 \
  --database data/operations.sqlite3
```

Expected output: `Imported 50 customers, 20 orders and 22 items`.
`OPERATIONS_DATABASE_PATH` defaults to `data/operations.sqlite3` at runtime; the
importer always requires explicit paths. Keep this database separate from both
`DATABASE_PATH` and `CONVERSATION_DATABASE_PATH`. The HTTP composition rejects
resolved-path and existing hard-link collisions among all three. The importer
rejects destination collisions with any CSV or the catalog, including aliases.
Generated files are Git-ignored and owned operational snapshots have mode 0600.
Do not edit the generated schema or use an unrelated SQLite database.

Each successful import replaces all owned rows in one SQLite transaction, removing
customers, orders, items and copied product references absent from the new snapshot.
Validation completes before destination creation; invalid source data leaves an
existing snapshot unchanged. Write failures roll back the replacement. Foreign or
incompatible schemas are rejected, never migrated or overwritten. A new file can
remain empty after an infrastructure failure; correct the cause and repeat the import.
Stop the demo before manually resetting files. Re-import does not reset conversations.

## Validation and stored projection

Headers must contain exactly the supplied unique columns; every row must match its
header. Operational fields are validated, without inventing email/phone restrictions.
Identifiers and quantities are positive integers within SQLite's signed 64-bit range.
Customer/order IDs and order/product item pairs are unique. All customer, order and
catalog-product references must exist. Dates must be valid `YYYY-MM-DD`; statuses are
`pending`, `confirmed`, `shipped`, `delivered`, or `cancelled`. Totals must be finite,
positive and exactly representable in centavos. Blank tracking and estimated-delivery
fields become unknown values. Known customers without orders and header-only empty
order/item snapshots are valid; the customer registry itself must be nonempty.

| Stored data | Projection |
| --- | --- |
| Customers | Customer ID only |
| Orders | Order/customer IDs, order date, status, supplied total in centavos, optional tracking/estimated delivery |
| Items | Order/product IDs and quantity |
| Product references | Referenced product IDs and names copied from the validated catalog snapshot |

Customer names, contacts/cities, order notes and payment methods are excluded from
the derived database and tool results. Source fingerprints and hash metadata are
not generated. Copied product names remain stable if the catalog changes; an
operational re-import refreshes them. Storage checks require expected columns and
a simple ownership marker, without comparing full SQL definitions.
Historical order totals are preserved even when they differ from current catalog
prices. There are no historical unit prices to infer or totals to recalculate.

## Authorization and tools

Import before configuring demo tokens. `DemoIdentityResolver(mappings, customers)`
requires a CustomerRepository; environment construction takes the same dependency.
It validates **every** configured customer during initialization and rechecks the
matched customer at each resolution. Removing a customer by re-import therefore
invalidates that mapping; update mappings and restart after configuration changes.
Unknown mappings or missing/incompatible initial operational storage produce safe
configuration failures (503). Missing/invalid credentials remain 401; later storage
faults are explicit retrieval failures (500), not successful empty results.

The HTTP agent is composed with `create_store_agent(settings, products, orders)`.
ExecutionContext travels through SDK per-run dependencies, outside model messages.
Cached tools retain only repositories. Repositories open fresh read-only connections,
validate schema, and check the customer within each read transaction. All order,
item and count queries bind customer scope as SQL parameters. Direct repository
access enforces the same ownership; it does not depend on HTTP checks or prompt obedience.

| Tool | Arguments | Result |
| --- | --- | --- |
| `list_my_orders` | `limit=5`, integer 1–20 | Own order ID/date/status/exact total; date descending then ID descending; total matches and truncation |
| `get_my_order` | Positive 64-bit `order_id` | Owned header, optional tracking/estimate, up to 20 product references/quantities sorted by product ID; total item rows and truncation |

Neither tool exposes `customer_id`. Unexpected scope fields and invalid identifiers
fail tool validation. Foreign and nonexistent IDs both return `order: null` and
`Pedido não encontrado na sua conta.` Known customers with no orders receive a
successful empty list. Unknown trusted customers fail authorization even when
calling the repository directly. Results carry `data_basis: imported_snapshot`;
integer-centavo totals also have an exact two-decimal `total_brl` string. `total_items`
counts distinct product rows, not summed quantities. No pagination or order changes
are provided in this story. Current-run truncated lists/items receive deterministic
Portuguese notices, including on output retries; historical returns add no notices.

History preserves conversational references only. The instructions require fresh
retrieval for order facts and ownership. Tracking/estimated delivery never establish
actual receipt, return eligibility, payment confirmation, or live carrier status.
The prompt is not a universal semantic grounding check. Failures propagate through
ChatService without saving a completed turn. Diagnostics allow metadata/counts and
safe error classes only; no identifiers, credentials, contacts, tracking or tool rows.

See [API setup](api.md), [ADR-0005](adr/0005-authorized-operational-snapshots.md) and
[validation evidence](validation.md). Controlled models verify wiring and isolation;
real Portuguese tool choice, follow-ups and adversarial behavior remain opt-in US-13.
Catalog-only factories and smoke/examples are isolated probes, never an HTTP fallback
when operational storage is missing.
