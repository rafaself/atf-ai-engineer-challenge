# Fictional source snapshots

These files were copied byte-for-byte from the supplied
`ai-engineer-technical-challenge-2026/data/` directory on 2026-10-31:

- `products.csv` (source: `desafio_tecnico_ai_eng - products.csv`)
- `categories.csv` (source: `desafio_tecnico_ai_eng - categories.csv`)
- `customers.csv` (source: `desafio_tecnico_ai_eng - customers.csv`)
- `orders.csv` (source: `desafio_tecnico_ai_eng - orders.csv`)
- `order_items.csv` (source: `desafio_tecnico_ai_eng - order_items.csv`)
- `promotions.csv` (source: `desafio_tecnico_ai_eng - promotions.csv`)

Filenames are translated to English; original encoding, line endings, and contents
are preserved. Git attributes
disable line-ending conversion for these CSVs on checkout. The source
bundle is `Desafio_Técnico_AI_Engineer_2026-20260616T150750Z-3-001.zip`; copies here
for products/categories come from its supplied extracted resource directory.
US-11 copies customer/order/item entries directly from that same original ZIP.
The project owner confirmed on 2026-10-31 that this data is **fictitious** and
approved committing these three original CSVs. Customer names/contact fields and
order notes are fictional source fixtures, not real customer records. No cleaning,
re-encoding, or newline conversion is applied. The snapshot has 50 customers,
20 orders, and 22 order-item rows. US-12 copies all 25 original promotion records
from the same ZIP, with four marked active. Its bytes match both the archive entry
and extracted supplied file. No dates/columns are added and no values, inactive
records, line endings or encodings are changed. Policy PDFs remain in the supplied
resources; general policy retrieval is separate work.

The operational importer retains customer IDs, minimal order headers and item
references only; contacts, customer names/cities, notes and payment methods never
enter its database or model-facing tool results. Generated databases remain
private and Git-ignored.

From this directory, verify the checked-in snapshot with:

```bash
sha256sum --check SHA256SUMS
```

The existing manifest covers the five earlier CSV copies. The new promotions
copy is verified directly against its supplied original; no new checksum
subsystem is introduced. These checks establish source identity, not live prices
or availability.
US-03 ingestion preserves these source files. It converts prices exactly to
integer centavos, validates references/types/statuses/dates/specs, and stores
additional normalized name columns for lookup. Original descriptive fields are
retained. See [catalog import and retrieval](../docs/catalog.md) for the full
snapshot replacement and schema compatibility rules.
