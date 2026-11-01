# Retrieval results (US-15, 2026-11-01)

The E5 Base and Titan V2 comparison is complete. No configuration is selected as adequate. Frozen thresholds remain
unchanged; read the accompanying timestamped JSON reports and methodology.

| Model | Split | Strategy | Recall@3 | Recall@5 | MRR@5 | Multi-group coverage@5 | Critical misses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e5 | development | vector | 0.889 | 0.889 | 1.000 | 0.400 | q06, q09 |
| e5 | development | filtered | 0.922 | 0.978 | 1.000 | 0.800 | q09 |
| e5 | validation | vector | 0.875 | 0.875 | 0.875 | 0.333 | q23 |
| e5 | validation | filtered | 0.875 | 0.938 | 0.875 | 0.667 | none |
| titan | development | vector | 0.822 | 0.889 | 0.950 | 0.400 | q09, q17 |
| titan | development | filtered | 0.922 | 0.978 | 0.967 | 0.800 | q09 |
| titan | validation | vector | 0.875 | 0.875 | 0.833 | 0.333 | q23 |
| titan | validation | filtered | 0.875 | 0.938 | 0.854 | 0.667 | none |

Development denominators: 15 answerable cases, 21 evidence groups, 5 multi-group
cases, 1 unsupported case excluded from retrieval metrics. Validation: 8 answerable
cases, 11 evidence groups, 3 multi-group cases, 1 unsupported case excluded.

## Interpretation and bounded next step

Both measured models retrieve a relevant first result reliably, but neither
strategy consistently retrieves every condition needed for multi-section answers.
Broad query-derived metadata filtering improves evidence coverage; it does not
establish safe answerability or replace the operational tools.

For E5, q06 (online returns) misses exclusions in vector-only retrieval; filtering
recovers them. q09 (defect) still misses manufacturer-warranty evidence under the
filtered strategy. On validation, q19 (conflicting WhatsApp numbers) omits company
contact evidence even after filtering. q23's return exclusions are recovered by
filtering. These are missing related conditions, not demonstrated literal-name
failures; lexical fusion is not justified by these observations.

Do not lower the targets or silently select the least-bad configuration. Neither
available configuration passes; review one bounded evidence-expansion change (for example explicit sibling eligibility-condition inclusion),
with its extra context cost. Since validation outcomes have now been examined,
any adjustment based on them is exploratory and needs new untouched validation
questions to support an independent final claim. Keep the original frozen set and
failed rankings; do not rewrite gold labels to make the current runs pass.

This is retrieval evidence only. Unsupported-answer behavior, monetary
applicability and final generation quality remain US-17 work.


## Timing, cost and offline validation

Observed median query-embedding latency: E5 38 ms development / 39 ms validation;
Titan 281 ms development / 274 ms validation. These include embedding work, not
just Chroma lookup; raw reports separate lookup timings for both strategies.
E5 model load was 12.1 seconds and initial document embedding 7.3 seconds under
shared-host memory pressure. Titan indexing time is in the preserved partial run
that built its complete index; the successful development run reused that index.

Completed Titan query runs estimate US$0.00001170 development and US$0.00000726
validation from returned input token counts. These exclude indexing and partial
failed attempts, which remain separately recorded. The total conservative reservation for approved experimentation and setup
probes is below US$0.022, well below the approved US$1 total. Reservations are upper bounds, not billed cost.


Offline validation after implementation: 298 tests passed; Ruff lint/format,
strict mypy across 77 files, package build and diff whitespace checks passed.
Tests use controlled vectors and real temporary Chroma storage; these checks do
not establish provider/model answer quality. The review found no actionable code defects; independent recomputation matched
all per-question and aggregate metrics in the four completed model/split reports.


## Recommendation

No model/strategy meets every frozen adequacy gate. For the next bounded
experiment, prefer **E5 Base with query-derived metadata filtering**: it runs on
the available CPU, has no embedding API cost, and yields comparable filtered
coverage to Titan with much lower measured query latency. This is a provisional
engineering candidate, not a claim that the missing eligibility evidence is safe
to ignore. Review evidence expansion and fresh held-out validation before claiming
that a policy tool is adequate. Do not add a reranker or search framework for the
observed missing related-condition problem.
