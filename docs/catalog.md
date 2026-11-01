# Catalog import and SQLite retrieval

US-03 introduced the synchronous ProductRepository port. US-12 extends its
contracts and import with the unchanged promotions source. It uses Python's csv, sqlite3, Decimal, and Unicode modules; no
new dependencies or ORM are required.

## Import and ownership

`infrastructure.catalog_import.import_catalog(products_path, categories_path,
promotions_path, database_path)` accepts explicit Path objects and returns ImportReport with
category/product/promotion counts. The root README command requires all four
paths; relative paths resolve against the caller's working directory. Success
prints counts and exits zero. Failure prints CatalogImportError to stderr and
exits one, without a traceback. Argument errors use argparse's nonzero exit.

All three UTF-8 CSVs (optional BOM) are validated before the database is
opened for writes. Headers may be reordered but must contain exactly the supplied
unique columns. Empty product/category snapshots, malformed rows, duplicate IDs, orphan references,
blank required text, empty normalized names, duplicate normalized categories,
unsupported statuses, invalid ISO dates, and non-object/non-finite JSON are rejected.
Source errors identify the filename, line, field, and reason without echoing
unrelated row values. Original descriptive text, specs, and dates are stored.

Prices must be finite, positive, and exactly representable as centavos. Conversion
does not use floats or silently round. Integer IDs/stock are parsed explicitly;
all persisted integers must fit signed 64-bit SQLite values. The largest allowed
price is R$92,233,720,368,547,758.07. Prices such as 0.2900 are exact; 0.001 is rejected.

The database is a generated, exclusively managed catalog, not a place for user
edits or history. Existing empty databases can be initialized. Existing catalogs
must have user_version 2 and the exact importer-owned categories/products/promotions table
definitions; unrelated tables/views, altered definitions, and other versions are
rejected without migration or modification. Schema creation is in the same
transaction as data replacement. Foreign keys, IDs, required fields, integer
price/stock, and statuses are constrained in the schema.

After validation, one explicit transaction replaces all promotions/products/categories.
Original source files are never written. Owned generated files use private mode 0600.
Identical inputs reproduce the same data; changed records refresh, missing records
disappear, and failed writes roll back, retaining the last committed snapshot.
Connections always close. A failed first database write may leave an empty database
file, but never a partially committed catalog. Validation failures create no database.

## Read-only retrieval

`infrastructure.sqlite_repository.SQLiteProductRepository(database_path)` opens no
connection at construction. Each search opens and closes its own read-only URI
connection and checks schema compatibility. Missing, incompatible, corrupt, or
unreadable databases raise ProductRetrievalError, retaining the underlying cause;
search never creates a database or silently replaces failures with empty results.

Category and name lookup strip surrounding whitespace, casefold, decompose Unicode,
and remove combining marks. Categories match exactly after normalization; product
names match literal substrings. `%`, `_`, quotes, and backslashes have no wildcard
or SQL meaning. Filters combine with AND. Unknown/normalization-empty filters yield
zero matches. Payable prices use inclusive integer-centavo bounds. Arbitrary-size
contract bounds are compared in Python without overflowing SQLite parameters.

Available-only searches require active status and positive stock; explicit
available_only=False includes active/out-of-stock, discontinued, and coming-soon
products. SQL selects products and active offers within one read transaction.
For the small supplied catalog, Python calculates quotes, applies payable-price
bounds, sorts by final price then product ID, counts and limits (default 10, maximum
20). No SQL floating-point arithmetic or premature limit changes budget matches.
Counts and products therefore share the same snapshot during concurrent import. Frozen
ProductSummary values and tuple results derive availability and truncation.

The importer uses the default SQLite journal mode. Tests additionally exercise a
concurrent replacement in WAL mode to prove read consistency; no WAL management,
pooling, retries, environment loader, server, or agent tooling is introduced.

## Promotion and PIX pricing

All 25 supplied promotions are imported, including 21 inactive records. The four
active records are selected using `is_active` only. Campaign names do not establish
dates or calendar validity. No values are repaired or dates/columns fabricated.
IDs/references and descriptions must be valid; integer percentages are 1–100 and
active flags exactly 0/1. Duplicate promotion IDs or multiple active offers for one
product fail validation instead of choosing/rewriting records. Empty promotions are
valid. Version-1 generated catalogs must be regenerated; no migration is included.

A small pure function in `application.pricing` computes a quote for an active,
stocked product: eligible promotion first, otherwise 5% PIX only when explicitly
requested, otherwise original price. Discounts never stack. Unavailable product
details retain original pricing without offering a discount. Original prices remain
positive centavos; final prices may be zero for a valid 100% discount. Half-up
rounding applies to the final price: `(original * (100 - percentage) + 50) // 100`.
No floats, ambient Decimal rounding, historical unit-price reconstruction or order
repricing are involved.

Both product tools accept `payment_method="standard"` (default) or `"pix"`.
`search_available_products` additionally accepts strict `promotions_only=False`;
true selects eligible active promotions, excluding PIX-only discounts. Budget
bounds use payable price for that payment choice. `price_centavos`/`price_brl`
remain the original price; `pricing` contains payment method, final centavo/BRL
price, applied percentage, discount kind (`none`, `promotion`, `pix`) and optional
promotion ID/description. Results identify `computed_snapshot_quote` price basis
and `source_is_active_snapshot` promotion validity. Current-run discounted products
receive Portuguese original/percentage/final-price notices. History never supplies
current pricing evidence. These notices do not validate every generated claim.

The supplied four final promotional prices are 32310, 43920, 196718 and 551908
centavos for product IDs 127, 121, 90 and 94. These are snapshot calculations, not
live offers. Their source percentages/original prices remain unchanged in storage.

## Verification

Run the README's locked install, Ruff, strict mypy, pytest, and build commands.
Tests use temporary on-disk databases, synthetic CSVs, and the supplied snapshot.
They exercise failed validation/writes, schema protection, repeat imports, literal
filtering, exact cents, sorting/limits, unavailable products, and command exits.
The expected supplied snapshot has 65 products, nine categories, and 12 available
violões priced at most 100000 centavos. Takamine GD20 costs 219900 centavos with
stock five; active Giannini GF-3D has zero stock and must not be recommended as
available. All values reflect the imported CSV snapshot, not a live inventory.
