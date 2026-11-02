# Current-harness Qwen3 32B and Nova Lite comparison (#40)

## Scope and evidence

On 2026-11-02, the owner approved a fresh run of only Qwen3 32B
(`qwen.qwen3-32b-v1:0`) and Nova Lite (`amazon.nova-lite-v1:0`) under a hard
US$0.25 Bedrock inference cap. It used the current agent instructions and output
handling at `d8a80173c730aaf72653e230bfc4cc98bce5f56c`, the production
`/api/chat` harness, and a new version of the same nine-scenario, sixteen-turn
matrix. The [current fixture](scenarios-current-v3.json) incorporates the
owner-approved inclusive freight threshold, context-aware holiday expectations,
return-condition requirements and the deterministic imported-inventory notice.
The original #40 fixture and capture were not edited.

The local E5 preflight was ready and returned the holiday, return and approved
freight evidence. The no-inference AWS availability check was denied for
`GetFoundationModelAvailability`; the live runner used its Qwen Runtime baseline
call as the access probe. That request was included in the cap. Both model runs
completed all 16 chat turns. There were 86 provider requests, no HTTP errors and
no requests with missing token usage. Estimated spend was US$0.02764770 of the
approved US$0.25 cap. Estimates are not invoice data.

## Reviewed results

Tool choice and answer faithfulness are reviewed separately. Verdicts are a
manual review by the root coding agent against the actual calls, tool results,
policy records and scenario criteria; this is not independent human review.

| Scenario | Qwen3 32B | Nova Lite | Main observation |
| --- | --- | --- | --- |
| Catalog budget and ordinal follow-up | Pass | Pass | Both used the correct category and budget, resolved the second item correctly, and included the deterministic snapshot notice. |
| Named zero-stock item and alternative | Partial | Pass | Both found available alternatives. Qwen also offered to check for a future availability forecast that no tool provides. |
| Promotion and PIX | Pass | Fail | Nova Lite returned R$ 417.24 by stacking 5% PIX onto the R$ 439.20 promotion while also saying stacking was not allowed. |
| No match | Pass | Partial | Nova Lite used an available-only product search for an exact named item, then claimed it was absent from the entire catalog. |
| Selected order details | Pass | Pass | Both called `get_my_order` and returned the correct Giannini item, quantity and tracking. |
| Guest order request | Pass | Pass | Both withheld order data until a fictional customer is selected. |
| Hours, holiday follow-up and product switch | Fail | Partial | Qwen reused prior evidence appropriately but asserted closure on Natal despite the exception. Nova Lite preserved the qualification but repeated the same policy lookup unnecessarily. Both made a fresh product lookup. |
| Mixed order and return eligibility | Partial | Fail | Qwen gave a conditional answer but omitted required accessories/manuals and misattributed return-policy citations. Nova Lite treated an estimated delivery date as actual receipt, denied eligibility, then said the return was allowed without confirming item condition. |
| Exact R$ 500 freight threshold | Partial | Pass | Both gave the owner-approved free-shipping outcome. Nova Lite's source list identifies the clarification. Qwen's inline citation incorrectly attributes equality to the original PDF, though its automatic source list also includes the clarification. |

| Model | Pass / partial / fail | Critical errors | Missed tools | Provider requests | Input / output tokens | Estimated cost | Median / max end-to-end seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 5 / 3 / 1 | 1 | 0 | 39 | 108,798 / 2,716 | US$0.01794930 | 2.038 / 6.079 |
| Nova Lite | 5 / 2 / 2 | 3 | 1 | 47 | 146,196 / 3,861 | US$0.00969840 | 2.758 / 5.881 |

Latencies are end-to-end `/api/chat` request times, including local retrieval and
tool execution; they are not model-only timing. The same-day rates are recorded
in the [pricing manifest](pricing.json).

## Interpretation and recommendation

Keep Qwen3 32B as the base **provisionally**. Both models had five passing
scenarios, but Qwen had fewer critical errors in this one run. Nova Lite cost
about 46% less, so it remains a possible cost-first option only if the project
accepts its observed PIX-price and return-eligibility risks. Neither model passed
the conditional Christmas question reliably: Qwen skipped a redundant lookup
but still concluded the store was closed; Nova Lite searched again and gave a
more qualified answer. Tool reuse improved for Qwen on that turn, while factual
interpretation did not.

The current run did not reproduce Qwen's old invented-order-item error or
Nova Lite's old zero-stock availability error. It still found Qwen's Christmas
overstatement and Nova Lite's return-eligibility failure; it also found a
critical Nova Lite PIX arithmetic error. This single run does not establish that
the harness updates caused either the improvements or the remaining errors. The exact
R$ 500 business outcome now follows the approved clarification, so the old #40
freight error classification must not be carried into this current result. Qwen
has a separate source-attribution defect on that answer.

This is one run per model on nine conversations. It does not establish general
reliability, a statistically meaningful quality difference, or stable cost and
latency. No further Bedrock inference was made after this run.

## Capture and reproduction

- [Reviewed raw capture](capture-context-updated-2026-11-02.json)
- [Current fixture](scenarios-current-v3.json)
- [Preflight: sandbox endpoint unavailable](preflight-context-updated-2026-11-02.json)
- [Preflight: AWS availability action denied, no paid calls](preflight-context-updated-network-2026-11-02.json)
- [Pricing and endpoint manifest](pricing.json)
- [Focused runner](../../../apps/backend/scripts/compare_models.py)

Reproduction command used the approved cap and selected only the two candidates:

```sh
uv run --group benchmark --directory apps/backend --locked \
  python -m scripts.compare_models \
  --live --max-cost-usd 0.25 \
  --model-key qwen3_32b --model-key nova_lite \
  --scenarios-file ../../docs/examples/model-comparison/scenarios-current-v3.json \
  --output ../../docs/examples/model-comparison/capture-context-updated-2026-11-02.json
```

The capture contains per-turn calls, arguments, returned evidence, actual
answers, usage, latency, source hashes and the manual verdicts. Its raw prompts,
responses and tool traces were unchanged during review. A future live run needs
its own explicit spending cap and a new output path.
