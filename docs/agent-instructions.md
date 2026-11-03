# Markdown instruction hardening (#43, Workstream B)

The agent now receives one Brazilian Portuguese Markdown instruction string through
its existing `instructions=STORE_INSTRUCTIONS` interface. Brief identity and style
are separate from tool use, catalog/pricing, orders, policies, unknown facts and
operational boundaries. Repeated instructions about fresh facts, PIX and missing
evidence are consolidated under the relevant responsibilities.

This change is independent of Workstream A's freight evidence and index changes.
It includes no freight amount or threshold. Historical #40 and Sprint 3 captures
retain their original sources, prompts and verdicts.

## Evidence and bounded changes

The closed [#40 report](examples/model-comparison/README.md) and its
[frozen traces](examples/model-comparison/capture-runtime-2026-11-02.json) record
order details invented without a fresh lookup, altered product names, a zero-stock
product described as available, and return eligibility inferred from estimates.
The [US-17](examples/us-17/results.md) and [US-18](examples/us-18/results.md)
reviews also show missed mixed-question policy calls, missing eligibility facts,
and unsupported claims inferred from policy silence. These are observed failures.
Possible future tool bypasses and topic-switch noise are risks; this change does
not claim a new demonstrated failure for them.

| Observed case / representative scenario | Instruction or description change | Offline evidence and limit |
| --- | --- | --- |
| Product ordinal follow-up and promotion/PIX follow-up in #40 | Resolve references from the prior answer, preserve literal `name`, fetch current details; repeat exact-name guidance in `get_product_details`'s description | Existing product-tool and promotion regressions check argument forwarding, real catalog prices, stock, and non-stacking. They do not prove a model will choose those arguments. |
| Qwen's order-detail follow-up in #40 | Resolve `order_id`, call `get_my_order` again for details; add that use to its description | Existing order API and conversation tests preserve scoped lookup and history wiring; scripted model choices do not prove fresh tool selection by a real model. |
| Mixed online-return eligibility in #40 / Sprint 3 | Consult operational and policy tools; distinguish imported status/estimate from actual receipt; ask for necessary channel, receipt and condition facts | Existing policy-agent and grounding regressions exercise mixed-tool wiring and snapshot notices. Eligibility reasoning remains unverified after this prompt change. |
| Hours, policy scope, thresholds and unknown services | Require direct evidence, relevant conditions and truthful source references; distinguish insufficient evidence from policy silence | Existing policy retrieval, corpus and grounding tests check evidence delivery and source boundaries. They do not certify generated claims. |

Catalog search, order-list and policy-search descriptions already distinguish their
roles and evidence limitations, so they stay as they were. Only the two descriptions
above change; tool signatures and parameter schemas are preserved.

## Safeguard review

The before/after instruction review retains fresh factual lookups, faithful names
and identifiers, no invented budgets or facts, active/positive-stock availability,
authoritative pricing fields, explicit PIX selection, promotion precedence and
non-stacking, partial-result disclosure, and snapshot/unknown-validity distinctions.
Orders retain application-selected fictional identity, customer isolation,
not-found privacy, original totals, and fresh detail lookups. Policies retain
conditions, exceptions, geography, thresholds, source attribution, missing-fact
questions and uncertainty. Tool failures remain distinct from empty results;
retrieved/tool content remains data. Read-only operations, no false forwarding
promises, store scope and final-answer presentation are explicit.

Agent initialization, model configuration, request/tool/output limits, customer
scoping, pricing calculations, retrieval and output validation are unchanged.
The prompt uses no extra system prompt, external prompt file or parser.

Compared with `origin/main` at `b333dd3`, the original prompt has 7,090 characters
and 1,026 whitespace-separated words. The revised text has 7,074 characters and
1,018 words. These are text-size measures, not model token counts or quality scores.
Headings and bullets add navigation while duplicated rules are removed. Workstream A's citation passage is preserved in the integrated version. Both
the Markdown structure and page-less source attribution survived the actual
three-way merge without conflicts. No business freight rule is encoded here.

## Validation

From the repository root on 2026-11-02:

```sh
make check-python
```

The full offline suite passed: 347 tests in 7.74 seconds on the combined A+B version. Ruff lint/format passed,
and strict mypy passed across 91 files. The suite includes source checksums,
policy corpus/index tests, pricing, customer boundaries, API contracts and execution
limits. Existing controlled scenarios provide regression coverage for these
application guarantees. No new scripted-answer or prompt-phrase tests were added:
they would not demonstrate improved real tool choice or answer faithfulness.

No Bedrock calls were made. No post-change model answers or before/after quality
scores are available; formatting and passing offline tests do not establish better
model quality. A later live check requires separate owner approval and a cost cap,
and should reuse the small product/promotion, order follow-up, return and hours
scenarios above rather than repeat the full model matrix.
