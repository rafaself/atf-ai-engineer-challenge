# Fictional source snapshots

These CSV files were copied byte-for-byte from the supplied
`ai-engineer-technical-challenge-2026/data/` directory on 2026-10-31:

- `products.csv` (source: `desafio_tecnico_ai_eng - products.csv`)
- `categories.csv` (source: `desafio_tecnico_ai_eng - categories.csv`)
- `customers.csv` (source: `desafio_tecnico_ai_eng - customers.csv`)
- `orders.csv` (source: `desafio_tecnico_ai_eng - orders.csv`)
- `order_items.csv` (source: `desafio_tecnico_ai_eng - order_items.csv`)
- `promotions.csv` (source: `desafio_tecnico_ai_eng - promotions.csv`)

`store_policies.pdf` was copied byte-for-byte from `políticas_da_loja.pdf` in the
same reference directory on 2026-11-01. Only its filename is translated.

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
records, line endings or encodings are changed. The original policy PDF remains
byte-for-byte identical to the supplied resource.

The operational importer retains customer IDs, minimal order headers and item
references only; contacts, customer names/cities, notes and payment methods never
enter its database or model-facing tool results. Generated databases remain
private and Git-ignored.

From this directory, verify the checked-in snapshot with:

```bash
sha256sum --check SHA256SUMS
```

The manifest covers all six CSV files and `store_policies.pdf`. Each copy matches
its supplied original byte-for-byte. These checks establish source identity,
not live prices or availability.
US-03 ingestion preserves these source files. It converts prices exactly to
integer centavos, validates references/types/statuses/dates/specs, and stores
additional normalized name columns for lookup. Original descriptive fields are
retained. See [catalog import and retrieval](../docs/catalog.md) for the full
snapshot replacement and schema compatibility rules.

## Owner-approved freight clarification

`policies/freight-clarification.json` records the owner-approved Workstream A
decision in GitHub issue #43. Recorded on 2026-11-02, it clarifies the original
PDF's section 5.1 for deliveries within the Região Metropolitana de Campo Grande:
orders below R$ 500,00 have a fixed R$ 35,00 freight fee, and orders at or above
R$ 500,00 receive free freight. This is new business evidence; the original PDF
still leaves equality unspecified and has not been edited. The current policy
freeze records the clarification source hash separately, and the historical
evaluation questions and benchmark captures remain unchanged.
