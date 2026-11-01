# Evidence-expansion experiment results

The bounded change improves evidence completeness but is not yet an adequate
policy-answering solution. Full-manual context also makes unsupported inferences;
it is not automatically the safer answer baseline.

Original US-15 reports, questions and thresholds are unchanged. The original 25
questions are exploratory for this new strategy. Expansion recovers every required
group for all 23 answerable original questions. The fresh set contains 11
answerable questions and one unsupported question. Expanded context is complete
for 10/11 answerable cases and 7/8 multi-section cases. The fresh phone-contact
question n06 misses sections 1.2 and 7 because none of its top-three seeds belongs
to the contact relation group. No rule was changed after seeing this failure.
These context-completeness figures are NOT Recall@5: context expansion can include
up to eight records (observed maximum seven on the old set, six on the fresh set).

## Paired generation: expanded versus full manual

All 24 Qwen3 32B calls completed without provider errors, blank answers, truncation,
internal-markup flags or unsupported R$ numeric values. Same model, temperature,
instructions, output cap and frozen questions in both arms; no operational tools,
history or live customer facts. Full context contains all 29 reviewed corpus
records; this compares policy content, not native PDF vision/layout processing.

| Measure, 12 questions per arm | Expanded E5 | Whole manual |
| --- | ---: | ---: |
| Input tokens | 9096 | 46134 |
| Output tokens | 1050 | 993 |
| Median generation latency (seconds) | 0.804 | 0.924 |
| Estimated USD at conservative rates | 0.002659 | 0.010021 |
| Provisional strict rubric passes | 7 | 6 |

Expanded context saves approximately 80% of input tokens. One generation sample
per question/arm on a shared host does not establish statistically reliable latency
or quality superiority. Retrieval latency is additional for the expanded arm;
context_experiment retrieves first and does not include that time in generation
latency. Refer to US-15's embedding/index measurements for that component.

## Answer failures matter more than a small score difference

- n01: the expanded answer moves the start of legal warranty to after 30 days;
  full context assumes eligibility from purchase date and invents a store remedy.
- n02: both arms categorically reject withdrawal for a final-sale item, silently
  reconciling the source's online-withdrawal and exchange-exclusion tension.
- n06: expanded context safely abstains but lacks needed contact evidence. Full
  context contains both contacts yet chooses their roles without flagging conflict.
- n11: both infer the exact-threshold freight outcome; expansion additionally
  assigns the fixed fee. All mentioned amounts exist in source, demonstrating that
  numeric membership does not validate applicability.
- n12: whole-manual context asserts there is no loan service; the document merely
  lacks that policy. Expanded context correctly describes absent evidence.

See answer-review.json for every question/arm and qualifications, and the raw
report for exact answers, usage and contexts. Review was performed by Codex against
source and frozen rubrics, not an independent human; scores are provisional.
The n04 rubric mentions general/tier payment conditions, but at eight installments
both minima agree, so a correct answer is not penalized for omitting a nonexistent
conflict. The rubric file itself was not edited after outputs were seen.

## Recommendation

Retain E5 plus bounded condition expansion as the lower-context candidate, but do
not declare it adequate or start production integration on a claim of success.
Full context supplies missing evidence but does not eliminate eligibility,
contradiction or absent-evidence errors. The next bounded US-16 design should make
unknown eligibility and source contradictions explicit in the policy tool/result
contract and require conditional answers; it should not add another retrieval
framework or reranker. Review the fresh contact miss separately. Any further tuning
on these results requires another untouched validation set.

Paid generation reserved US$0.0620424 (conservative pre-call upper estimate), under
the US$0.50 experiment cap and the prior US$1 total authorization. Actual usage
estimates above use conservative rates of US$0.20/M input and US$0.80/M output,
not an invoice. Model/pricing references: AWS Bedrock Qwen3 32B model card and
https://aws.amazon.com/bedrock/pricing/. No changes to chat routing, source bytes,
operational data, original benchmark results, production dependencies or AWS policy.

## Validation and delivery state

300 offline tests passed, including direct-condition expansion and context-size
boundaries. Ruff lint/format, strict mypy (80 source files), package build and
whitespace checks passed. Rechecked frozen question/protocol/rule hashes after
the experiment; no changes. All 24 generation records are present and pass the
limited numeric/output-shape checks; that is not proof of semantic correctness.
Changes remain uncommitted on experiment/policy-evidence-expansion. No production
policy tool or HTTP behavior was changed.
