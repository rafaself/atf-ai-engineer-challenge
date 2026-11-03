# Catalog and pricing reference

Use the [README Getting Started guide](../README.md#getting-started) for normal
Docker setup.
The individual importer below remains available for focused experiments.

US-03 introduced the synchronous ProductRepository port. US-12 extends its
contracts and import with the unchanged promotions source. It uses Python's csv, sqlite3, Decimal, and Unicode modules; no
new dependencies or ORM are required.

## Import and ownership

`infrastructure.catalog_import.import_catalog(products_path, categories_path,
promotions_path, database_path)` accepts explicit Path objects and returns ImportReport with
category/product/promotion counts. Its CLI accepts the three CSV paths and uses
the fixed project catalog destination; relative source paths resolve against the caller's working directory. Success
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
must have user_version 2 and the required catalog tables/columns. SQL definition
text is not compared; harmless additional columns do not invalidate a snapshot.
Unrelated or incomplete storage is rejected without rewriting it. Schema creation is in the same
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

Product results include the imported structured `specs` object, which is the
catalog evidence for instrument characteristics. Free-form product descriptions
remain stored but are not exposed through these tools. An empty `specs` object
means the catalog has no structured details to report; the model must not infer
characteristics from names, categories, brands, prices, or other products.

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

Every catalog tool requires an explicit `payment_method="standard"` or `"pix"`.
There is no implicit payment choice, including for alternatives.
Search budget bounds are capped at R$1,000,000,000 each as a commercial limit,
with at most two decimal places, rather than exposing SQLite's storage ceiling.
`search_available_products` additionally accepts strict `promotions_only=False`;
true selects eligible active promotions, excluding PIX-only discounts. Budget
bounds use payable price for that payment choice. `price_centavos`/`price_brl`
remain the original price; `pricing` contains payment method, final centavo/BRL
price, applied percentage, discount kind (`none`, `promotion`, `pix`) and optional
promotion ID/description. Results identify `computed_quote` price basis and `current_simulated_catalog`
promotion validity. `pricing.explanation` describes the actual applied discount. The model presents the original
price, percentage and final price from those fields; the demo interface explains the simulation once. History
never supplies current pricing evidence. The notice does not validate generated claims.

The supplied four final promotional prices are 32310, 43920, 196718 and 551908
centavos for product IDs 127, 121, 90 and 94. These are snapshot calculations, not
live offers. Their source percentages/original prices remain unchanged in storage.

## Multi-product quotes and comparisons

`calculate_quote` accepts one to ten distinct product IDs, each with a requested
quantity from 1 to 99. It resolves all IDs, prices, active promotions and stock in
one read-only catalog transaction. A missing product, inactive product, zero stock,
or requested quantity above stock prevents a cart total; the tool reports the
specific missing or unavailable item instead of quoting a partial cart. Historical
orders remain separate snapshots and are never repriced.

The tool returns exact centavos and two-decimal BRL display values for line
subtotals, cart totals, shipping, split allocations and installments. `compare` shows
both payment totals; `pix` selects the existing PIX rule; `credit` uses standard
pricing and returns eligible installment plans; `split` requires a requested PIX
allocation. Promotions still take precedence over PIX. The tool does not apply an
additional PIX discount to mixed payment because the policy does not define that
case. Mixed tender is permitted only above R$ 2.000,00; when original and standard
payable totals land on opposite sides of that threshold, the tool reports the
unresolved basis instead of deciding eligibility. A split allocation always sums
to the standard payable merchandise total. Split quotes cannot include shipping
because the manual does not define how freight is assigned between payment methods.

Installment values are allocated in integer centavos and sum exactly to the chosen
total. The calculation follows the specific ranges in policy section 3.1: purchases
below R$ 50,00 have no 1–3 installment option; 4–6 installments require at least
R$ 80,00 each; 7–12 require at least R$ 100,00 each. Section 3 also states a general
R$ 100,00 minimum, so the quote includes that source discrepancy with the result.

Shipping is separate from merchandise totals. For the Campo Grande metropolitan
area, the approved #43 clarification makes freight free at exactly R$ 500,00 and
above, and R$ 35,00 below. Since the manual does not say whether the threshold uses
pre- or post-discount merchandise totals, the tool quotes a charge only when both
bases produce the same result. Supported local shipping is included in
`quoted_total_centavos`; unresolved or unsupported shipping leaves that all-in total
unset. Other-city shipping charges are not estimated because they require CEP,
weight and dimensions; large instruments may require an individual quote.

`compare_products` accepts only identified product IDs and compares original price,
payable price or stock, returning ascending values, minimum/maximum ties and the
numeric difference. For open-ended questions such as the cheapest guitar in a
category, use `search_available_products`, which already orders by payable price.
Both tools read current simulated catalog data. History provides conversational
references only, not prices or inventory.

## Verification

Run the README's locked install, Ruff, strict mypy, pytest, and build commands.
Tests use temporary on-disk databases, synthetic CSVs, and the supplied snapshot.
They exercise failed validation/writes, schema protection, repeat imports, literal
filtering, exact cents, sorting/limits, unavailable products, and command exits.
The expected supplied snapshot has 65 products, nine categories, and 12 available
violões priced at most 100000 centavos. Takamine GD20 costs 219900 centavos with
stock five; active Giannini GF-3D has zero stock and must not be recommended as
available. All values reflect the imported CSV snapshot, not a live inventory.

## Product references and alternatives

Product results expose `product_id`. Initial named lookups use
`find_product_by_name(product_name, payment_method)`; identified follow-ups use
`get_product_details(product_id, payment_method)`. Separate tool schemas prevent
a product code from being silently treated as a name.
Customer answers include product codes so references survive the text-only history.
`find_product_alternatives(product_id, payment_method, limit)` derives the original category,
excludes the original product, and searches available products without invented
price restrictions. Explicit customer budget searches remain available through
`search_available_products`. Tool results are current simulated store records.
