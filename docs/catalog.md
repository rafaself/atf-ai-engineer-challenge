# Catalog import and SQLite retrieval

US-03 implements the synchronous ProductRepository port without changing the
US-02 contracts. It uses Python's csv, sqlite3, Decimal, and Unicode modules; no
new dependencies or ORM are required.

## Import and ownership

`infrastructure.catalog_import.import_catalog(products_path, categories_path,
database_path)` accepts explicit Path objects and returns ImportReport with
category/product counts. The module command in the root README requires all three
paths; relative paths resolve against the caller's working directory. Success
prints counts and exits zero. Failure prints CatalogImportError to stderr and
exits one, without a traceback. Argument errors use argparse's nonzero exit.

Both complete UTF-8 CSVs (optional BOM) are validated before the database is
opened for writes. Headers may be reordered but must contain exactly the supplied
unique columns. Empty snapshots, malformed rows, duplicate IDs, orphan references,
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
must have user_version 1 and the exact importer-owned categories/products table
definitions; unrelated tables/views, altered definitions, and other versions are
rejected without migration or modification. Schema creation is in the same
transaction as data replacement. Foreign keys, IDs, required fields, integer
price/stock, and statuses are constrained in the schema.

After validation, one explicit transaction replaces all products/categories.
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
zero matches. Prices use inclusive integer-centavo bounds. Arbitrary-size contract
bounds are handled without overflowing SQLite parameters.

Available-only searches require active status and positive stock; explicit
available_only=False includes active/out-of-stock, discontinued, and coming-soon
products. Results sort by price ascending then product ID, using the requested
limit (default 10, maximum 20). Total count before limiting and rows are read in
the same transaction, so a concurrent import cannot mix snapshots. Frozen
ProductSummary values and tuple results derive availability and truncation.

The importer uses the default SQLite journal mode. Tests additionally exercise a
concurrent replacement in WAL mode to prove read consistency; no WAL management,
pooling, retries, environment loader, server, or agent tooling is introduced.

## Verification

Run the README's locked install, Ruff, strict mypy, pytest, and build commands.
Tests use temporary on-disk databases, synthetic CSVs, and the supplied snapshot.
They exercise failed validation/writes, schema protection, repeat imports, literal
filtering, exact cents, sorting/limits, unavailable products, and command exits.
The expected supplied snapshot has 65 products, nine categories, and 12 available
violões priced at most 100000 centavos. Takamine GD20 costs 219900 centavos with
stock five; active Giannini GF-3D has zero stock and must not be recommended as
available. All values reflect the imported CSV snapshot, not a live inventory.
