# Three-model Runtime comparison (#40)

This comparison uses nine frozen Portuguese conversations (16 planned HTTP
turns per model) through the existing app. Qwen3 32B, Nova Micro, and Nova Lite
use Bedrock Runtime Converse for inference; the app executes every tool locally.
Nemotron Nano 3 was excluded because its documented tool-calling route uses
Bedrock Mantle. See the [protocol](protocol.md), [scenario fixture](scenarios.json),
and [reviewed capture](capture-runtime-2026-11-02.json).

The live run completed all nine conversations for Nova Micro and Nova Lite. Qwen
completed eight conversations and had one local policy-retrieval failure. After
activating the existing benchmark dependency group, the runner continued the
two unattempted conversations without repeating any attempted turn. The policy
failure was an HTTP 503 caused by running without that dependency group; the
failed Qwen turn was left failed per protocol.
The availability API was denied by IAM, but the Qwen Runtime baseline call
succeeded and the Runtime comparison proceeded.

## Reviewed results

Pass/partial/fail counts are conversations out of nine. Critical errors and
missed tools/unsupported claims were reviewed against tool results and the
policy source. Cost and latency totals include every paid inference request.

| Model | Pass / partial / fail | Critical errors | Missed tools / unsupported claims | HTTP errors | Model calls | Input / output tokens | Estimated cost | Cost per pass | Median / max latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 5 / 1 / 3 | 2 | 2 / 2 | 1 | 30 | 81,107 / 1,734 | $0.01320645 | $0.00264129 | 1.598 / 18.625 |
| Nova Micro | 4 / 1 / 4 | 4 | 2 / 2 | 0 | 39 | 105,107 / 3,004 | $0.00409930 | $0.00102483 | 1.842 / 48.293 |
| Nova Lite | 5 / 1 / 3 | 3 | 1 / 2 | 0 | 42 | 116,232 / 3,099 | $0.00771768 | $0.00154354 | 2.227 / 5.349 |

Total estimated spend was **$0.025023435 of the $1.00 cap**, across 111 paid
model calls. No requests had missing token usage. All 27 attempted
model-conversations have completed human review. No cheaper candidate qualifies
for a recommendation: each had critical errors. Keep Qwen as the default; this
one-pass sample does not establish reliability or justify automatic routing.

Key failures:

- All three models asserted that an order of exactly R$ 500 receives free
  freight, although the policy says “above R$ 500” and leaves equality
  unspecified.
- Nova Micro denied a return five days after receipt; Nova Lite used the
  estimated delivery date as actual receipt and made an unsupported eligibility
  decision.
- Nova Lite said a zero-stock product was available. Nova Micro reported an
  in-stock promotional product unavailable after using a non-matching product
  name.
- Qwen omitted the order-detail tool on a follow-up and invented the order item.
- Qwen's policy-hours scenario has one HTTP 503 from local policy retrieval; the
  failed turn was not retried.

## Reproducing the run

Use the existing CPU benchmark group so local policy retrieval can load its
cached E5 model; the runner does not download model weights. Refresh the rates
and route checks on the day of a new run. The runner loads only AWS settings
silently and never writes credential values to a capture.

```sh
uv run --group benchmark --directory apps/backend --locked \
  python -m scripts.compare_models \
  --live --max-cost-usd 1.00 \
  --output ../../docs/examples/model-comparison/new-capture.json
```

Choose a fresh output path; captures are opened exclusively and never
overwritten. A resumed run uses `--resume-from <partial-capture>`; it skips
every scenario that already had an attempted turn and carries prior estimated
spend into the same cap.
