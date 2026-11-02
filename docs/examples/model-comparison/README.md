# Bedrock Runtime model comparison (#40)

The recorded run evaluated Qwen3 32B, Nova Micro, and Nova Lite through Bedrock
Runtime Converse. All application tools ran locally. Nemotron Nano 3 was excluded
as an architectural scope decision: this comparison stayed on Runtime Converse
and did not add a Mantle adapter solely for that candidate. Its Runtime Converse
tool support was not verified; this is not a general claim that Runtime lacks
tool calling. See the [protocol](protocol.md), current
[scenario fixture](scenarios.json), [frozen v1 fixture](scenarios-frozen-v1.json),
and [reviewed capture](capture-runtime-2026-11-02.json).

Each model had nine planned conversations and 16 planned HTTP turns. Nova Micro
and Nova Lite completed all nine conversations and 16 turns. Qwen attempted nine
conversations and 14 of 16 turns; its policy-hours conversation stopped on a
local retrieval HTTP 503, leaving two turns unexecuted. That conversation is an
execution failure, not a semantic model failure. Qwen's other eight completed
conversations were reviewed. The original failed request was not retried; after
the missing local dependency group was activated, the runner continued only with
unattempted conversations.

Post-run review changed Qwen's `mixed-order-return-followup` from Pass to Partial:
the order follow-up answered without a fresh policy lookup and the first answer
described imported tracking status as delivery before qualifying it. The review
also corrected the `no-match` required-tool name after the protocol was frozen;
the original v1 fixture and all captured prompts, responses, and tool traces are
preserved. See the erratum in the [protocol](protocol.md). No additional model
inference was used for these corrections.

## Reviewed results

Pass/partial/fail counts use only completed, semantically evaluated
conversations. The next column shows evaluated/attempted conversations and
attempted/planned HTTP turns. The Qwen 503 and its two unexecuted turns remain in
the reliability counts. All 26 completed conversations were manually reviewed.

| Model | Pass / partial / fail (evaluated n) | Evaluated / attempted; HTTP turns attempted / planned | Critical errors | Missed tools / unsupported claims | HTTP errors | Model calls | Input / output tokens | Estimated cost | Cost per pass | Median / max end-to-end latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 4 / 2 / 2 (8) | 8 / 9; 14 / 16 | 2 | 3 / 2 | 1 | 30 | 81,107 / 1,734 | $0.01320645 | $0.00330161 | 1.598 / 18.625 |
| Nova Micro | 4 / 1 / 4 (9) | 9 / 9; 16 / 16 | 4 | 2 / 2 | 0 | 39 | 105,107 / 3,004 | $0.00409930 | $0.00102483 | 1.842 / 48.293 |
| Nova Lite | 5 / 1 / 3 (9) | 9 / 9; 16 / 16 | 3 | 1 / 2 | 0 | 42 | 116,232 / 3,099 | $0.00771768 | $0.00154354 | 2.227 / 5.349 |

Total estimated spend was **$0.025023435 of the approved $1.00 cap**, across
111 paid model calls. No requests had missing token usage. Nova Lite had more
passing conversations than Qwen's eight evaluated cases, but had three critical
errors; Nova Micro had four. No cheaper model meets the zero-critical-error
selection gate. Keep Qwen as the default provisionally; the one-pass sample does
not establish reliability or justify automatic routing.

Key failures:

- All three models said an order of exactly R$500 qualifies for free freight,
  although the policy says “above R$500” and does not resolve equality.
- Nova Micro denied a return five days after receipt. Nova Lite treated estimated
  delivery as actual receipt and made an unsupported eligibility decision.
- Nova Lite called a zero-stock product available. Nova Micro missed an
  in-stock promotional product after searching with a mismatched name.
- Qwen omitted the order-detail tool on a follow-up and invented the order item.
- Qwen's policy-hours conversation had one local HTTP 503; it is reported as an
  infrastructure failure and is excluded from semantic verdicts.

## Latency interpretation

Latency is end-to-end `/api/chat` request wall time, including model inference,
local tool execution, policy retrieval, and any local initialization. These
measurements do not isolate model inference speed. The maximum is reported
because this small sample does not support stable tail-latency estimates.

## Reproducing the run

The runner now checks local policy dependencies, cached E5 weights, and the
existing policy index before any paid model request. It does not download model
weights. Refresh rates and route checks on the day of a new run. The runner loads
only AWS settings silently and never writes credential values to a capture.

```sh
uv run --group benchmark --directory apps/backend --locked \
  python -m scripts.compare_models \
  --live --max-cost-usd 1.00 \
  --output ../../docs/examples/model-comparison/new-capture.json
```

The command requires separate approval for any new paid run. Choose a fresh
output path; captures are opened exclusively and never overwritten. A resumed
run uses `--resume-from <partial-capture>`, skips every scenario that already had
an attempted turn, and carries prior estimated spend into the same cap.

## Runner scope review

The one-off runner retains only safeguards used by this comparison: the spend
reservation, Runtime route checks, source hashes, local policy copies, resumable
checkpoints, and turn-level evidence. The review added a local retrieval
readiness check and consolidated duplicated candidate metadata setup. It did not
add a provider framework, Mantle adapter, or model-speed instrumentation.

## Implementation validation (2026-11-02)

- Offline backend suite: **338 passed**.
- Ruff lint, Ruff formatting check, strict mypy, and the locked dependency check:
  all passed.
- All seven supplied CSV/PDF checksum entries passed.
- The frozen v1 scenario and original capture hashes match their recorded values;
  all 46 attempted HTTP turns preserve their original traces and timings. The
  26 evaluated conversations and 111 recorded model calls reconcile.
- The local retrieval readiness check loaded cached E5 weights and found evidence
  in the existing `policy-e5` index. No Bedrock inference was made during
  validation.
