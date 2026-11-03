# Effective prepared data and simulation evaluation — 2026-11-03

## Delivery

Implemented the [data-processing plan](../../guides/data-processing.md) locally:

- Canonical opening hours put exceptions in the holiday label and introduce
  possible special service for Natal, Black Friday and the store anniversary.
- One effective freight section applies the approved inclusive R$500 boundary
  before embedding. Original PDF and approval provenance remain internal.
- Return conditions and exclusions are prepared once; retrieval passes the
  structured rule through rather than reconstructing it at runtime.
- UI and CLI identify the fictional simulation once. Operational reads represent
  current simulated records. Per-answer snapshot and freight-history notices
  are removed; actual-receipt uncertainty, truncation and references remain.
- Product-ID lookups, customer-facing product codes, a category-derived
  alternatives tool and deterministic discount explanations are implemented.

The rebuilt corpus contains 29 records, parser `poppler-effective-policies-v6`,
and current labels `questions-v3.json`. Preparation updates the corpus and freeze
hashes reproducibly; E5 was rebuilt locally with cached weights. Supplied CSV/PDF
bytes and dependency versions were unchanged.

## Evaluation and spending

The [v4 fixture](scenarios-current-v4.json) was frozen before inference. Its user
prompts match v3; factual correctness, required tool use, efficiency and
presentation are assessed separately. An extra successful lookup alone does not
lower the semantic verdict. A missed fresh lookup remains a tool defect even if
the repeated value happens to be correct.

Both models completed 9/9 conversations and 16/16 turns, all HTTP 200. The 82
provider calls cost an estimated **US$0.03106815**, with no missing usage. This
run's cap was US$0.948238, reserving the preceding two runs' US$0.051762.
Cumulative estimated spend is **US$0.08283015**, within the approved US$1.00.
Estimates are not invoices.

| Model | Semantic pass / partial / fail | Rubric-defined critical errors | Missing required reads | Unsupported claim groups | Calls | Cost | Median / max latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 8 / 1 / 0 | 0 | 1 | 1 | 39 | $0.01604100 | 1.592 / 5.779 |
| GPT-OSS 120B | 8 / 1 / 0 | 0 | 0 | 4 | 43 | $0.01502715 | 2.439 / 9.001 |

Zero rubric-defined critical eligibility/privacy errors does not make fabricated
contacts or workflows acceptable. The reviewed
[capture](capture-effective-data-qwen32-gptoss120-2026-11-03.json) preserves every
response, trace, source freeze and separate dimension review. The
[preflight](preflight-effective-data-qwen32-gptoss120-2026-11-03.json) verified
the current index and model availability without inference.

## Observations

**Natal:** neither model asserted categorical closure on the follow-up. Qwen's
wording was awkward (generally closed on Natal, except Natal), but it explicitly
retained possible special service and concluded the specific schedule is unknown.
GPT-OSS preserved the distinction but repeated retrieval despite sufficient
context. Both received the new evidence; a single pass cannot establish causality
or that the behavior is reliably fixed.

**Freight and presentation:** both applied the inclusive threshold in the named
region with an effective-policy reference and no ingestion notice. Neither
repeated snapshot footers. Qwen generated its own return-policy source list,
duplicating the application footer.

**Alternatives and attributes:** both used `find_product_alternatives(96)`,
returned real available products and avoided invented budgets. Described
materials, strings and other attributes were present in the tools. GPT-OSS's
comparison referred to shared structured materials rather than invented sound or
comfort. It omitted the original product code initially and needed another lookup
to recover the ID.

**Follow-up tool compliance:** Qwen skipped the ordinal refresh, although its
stated price and stock matched the prior result. Other detail follow-ups used
names rather than IDs. Stable-ID support is implemented and tested, but adherence
is not established. GPT-OSS also omitted `payment_method=pix` on its PIX lookup;
the standard promotional quote happened to have the same amount. Both final
discount explanations were correct; these tool-argument defects remain separate.

**Returns remain Partial for both.** Both retrieved order details and policy
evidence and put five days inside the deadline. Qwen omitted purchase channel
from initial questions, did not explicitly request all remaining confirmations
on the follow-up, and mixed preference-exchange wording (“perfect condition”)
into online-return conditions. It invented no contact or posting-label workflow.

GPT-OSS additionally treated payment method as an eligibility prerequisite,
added documents and an unsupported refund-clock anchor, and invented SAC email
`sac@emporiodamusica.com.br`, telephone `(67) 3221-1234`, label issuance and a
distribution-center process. Neither contact appears in the prepared corpus.
This remains a material support risk despite avoiding the rubric's definitive
eligibility/privacy critical errors. Prepared facts and instructions did not
prevent those unsupported additions.

## Comparison and limits

Published v3 scores include efficiency/presentation penalties and cannot be
compared directly with v4 semantic scores. A separate
[same-rubric retrospective review](semantic-review-v4-effective-data-2026-11-03.json)
rates the preceding responses at Qwen 5/3/1 and GPT-OSS 7/2/0 for semantic quality,
versus 8/1/0 each here. Original captures and published verdicts are untouched;
the retrospective review does not apply new tool contracts to old code.

Several changes were bundled and each model was sampled once on nine familiar
conversations. These observations establish exercised paths, not general
reliability or isolated causal effects. Additional prompt repetition is not an
enforcement guarantee. Eliminating invented return procedures would require a
bounded response contract or an explicit return workflow; this task grants no
unsupported order-mutation capability.

## Validation

- Backend: **366 tests passed**, Ruff lint/format and strict mypy passed.
- CLI: **six tests passed**, strict types passed; both Python packages built.
- Frontend: lint, TypeScript and production build passed after installing the
  existing lockfile. Its audit reported ten moderate development findings;
  the runtime-only audit reported zero vulnerabilities. No versions changed.
- Canonical-policy regressions were observed failing before implementation,
  then passing. Real-SQLite regressions cover stable IDs, alternative category,
  original-product exclusion and discount-origin explanation.
- Old assertions requiring footers or a separate active freight-overlay chunk
  were updated for the approved replacement. Exact prices, customer scoping,
  source integrity and truncation remain checked.
- No frontend visual inspection was performed. Index build and live readiness
  succeeded without downloads; supplied-source checksum regressions passed.
