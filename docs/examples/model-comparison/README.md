# Bedrock Runtime model comparison (#40)

The latest [Luna budget-echo benchmark](luna-budget-clarification-2026-11-03.md)
records two Luna-only full v7 runs. The first inline instruction did not stop the
budget echo; the clearer standalone instruction produced 12/0/0 in the second
manual review. The order-total clarification remained in both prompts.

The preceding [Luna order-total clarification benchmark](luna-order-total-clarification-2026-11-03.md)
resolved its target mixed order/return presentation issue. Its 11/1/0 score
included the budget echo, which this later experiment addresses.

The latest [full Qwen / Luna / Haiku benchmark](full-qwen-luna-haiku-2026-11-03.md)
completed 60 HTTP turns with no execution errors under a fresh approved US$4 cap.
Qwen scored 9/1/2 and Luna/Haiku each scored 11/1/0 (pass/partial/fail).
Luna had the lowest estimated cost and shorter answers than Haiku in this sample.

The current [minimal grounding comparison](grounding-v9-2026-11-03.md) records a
controlled baseline, two rejected prompt/scope variants and the retained
source-only evidence improvement. It reviews correctness, tools and UX separately;
return-procedure hallucinations remain unresolved.

The latest focused [return-contact experiment](return-contact-v8-2026-11-03.md)
tests a dedicated lookup and explicit guidance on four conversations / five turns
per model. Both models still make unsupported conclusions; GPT-OSS invents a
document checklist and label workflow despite retrieving the new evidence.

The latest [scoped harness evaluation](scoped-harness-qwen32-gptoss120-2026-11-03.md) records the 12-conversation v7 run, corrected historical call accounting, and the rejected structured-return output experiment.

The current default is [v7](scenarios-current-v7.json), covering 12 conversations
and 20 HTTP turns per model. It retains scoped policies, explicit product/payment
contracts and stronger severity review. The bounded-output experiment was rejected
after live failures; its captures and patch remain available. See the
[scoped harness review](scoped-harness-qwen32-gptoss120-2026-11-03.md).

See the [accounting erratum](accounting-erratum-2026-11-03.md) before comparing
historical model-call totals. Version 2 separates current responses, provider
attempts, data tools and structured output functions.


The latest [effective-data and simulation evaluation](effective-data-qwen32-gptoss120-2026-11-03.md)
records canonical prepared policies, one-time disclosure and reviewed v4 dimensions.
Historical results below retain their original criteria.

The latest [structured return evidence experiment](structured-return-qwen32-gptoss120-2026-11-03.md)
records the next Qwen/GPT-OSS 120B run and its reviewed capture.

The results below preserve the original one-pass issue #40 comparison. They used
the earlier harness and original freight text; in particular, their exact
R$ 500 freight finding predates the approved inclusive clarification. See the
[current-harness Qwen and Nova Lite refresh](current-harness-qwen-nova-lite-2026-11-02.md)
for the fresh two-model run, current policy rule and updated answer/tool-use
review. The historical capture remains unchanged. The separately run GPT-OSS
comparison, with a fresh Qwen control and the current policy clarification, is
documented in the [GPT-OSS Runtime benchmark](gpt-oss-runtime-2026-11-03.md).
The subsequent [GPT-OSS 20B retry](gpt-oss-20b-retry-2026-11-03.md) records
the harness adjustments, retry results and remaining quality issues without
changing either earlier capture.
The later prompt and processed-corpus remediation run for Qwen3 32B and
GPT-OSS 120B is recorded in the
[remediation benchmark report](remediated-qwen32-gptoss120-2026-11-03.md), with
its reviewed [capture](capture-remediated-qwen32-gptoss120-2026-11-03.json).
The latest [prompt and harness evaluation](prompt-harness-qwen32-gptoss120-2026-11-03.md)
records the shorter instructions, structured product specifications, current-v3
manual review, and a fresh Qwen/GPT-OSS 120B comparison.

The recorded run evaluated Qwen3 32B, Nova Micro, and Nova Lite through Bedrock
Runtime Converse. All application tools ran locally. Nemotron Nano 3 was excluded
as an architectural scope decision: this comparison stayed on Runtime Converse
and did not add a Mantle adapter solely for that candidate. Its Runtime Converse
tool support was not verified; this is not a general claim that Runtime lacks
tool calling. See the [protocol](protocol.md), current
[scenario fixture](scenarios-current-v3.json), [legacy v2 fixture](scenarios.json),
[frozen v1 fixture](scenarios-frozen-v1.json),
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

## Current-harness refresh

The [fresh Qwen3 32B and Nova Lite run](current-harness-qwen-nova-lite-2026-11-02.md)
used the same nine scenarios with current harness instructions, the approved
freight clarification and updated behavioral expectations. Each model completed
16/16 chat turns. Qwen scored 5 pass / 3 partial / 1 fail with one critical error;
Nova Lite scored 5 / 2 / 2 with three critical errors. This new result does not
rewrite the original comparison above.

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
Use repeated `--model-key` options to select candidates and `--scenarios-file` to
provide a separately versioned fixture. A single-model diagnostic can select one
model; multi-model comparisons require Qwen as the baseline. The runner defaults
to [current v7](scenarios-current-v7.json), with 12 conversations and 20 planned
HTTP turns per model.

```sh
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.compare_models \
  --live --max-cost-usd 1.00 \
  --output docs/examples/model-comparison/new-capture.json
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
