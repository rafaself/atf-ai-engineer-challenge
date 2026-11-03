# GPT-OSS Bedrock Runtime benchmark — 2026-11-03

## Result

Neither GPT-OSS size clears the project’s comparison gate. GPT-OSS 20B cost less
than half of the Qwen control but failed to complete two conversations with
local tool-execution HTTP 500s and produced only three passing conversations in
the seven that completed. GPT-OSS 120B completed the full set and matched Qwen’s
four passing conversations, but made one critical return-eligibility error.
Both sizes showed unsupported product descriptions or imprecise freight-source
attribution during manual review.

The fresh Qwen control itself had one critical error: it stated that the store
would be closed on Natal even though the retrieved policy leaves special-date
hours open to change. This one-pass comparison is a small, fixed Portuguese
sample; it does not establish broad model quality or stable latency.

## Run details

- **Route:** Bedrock Runtime Converse in `us-east-1`, through the project’s
  `/api/chat` and Pydantic AI path. Catalog, order and policy tools ran locally.
- **Scenarios:** the nine-conversation, 16-turn
  [`scenarios-current-v3.json`](scenarios-current-v3.json) fixture. Each model
  used one fresh session per conversation and the same session for follow-ups.
- **Control:** Qwen 3 32B was run alongside both GPT-OSS candidates.
- **Context ceilings:** the verified manifest records 128,000 tokens for each
  GPT-OSS model and 32,000 for the Qwen control.
- **Access:** the account availability preflight reported all three selected
  models available. A separate direct Converse probe verified a tool call and
  follow-up response for each GPT-OSS model.
- **Policy retrieval:** the existing local E5/Chroma path was prepared before
  inference. No paid embedding request was made.
- **Prices:** standard on-demand rates were checked against the
  [AWS Bedrock us-east-1 price list](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/us-east-1/index.json),
  offer version `20261102165015`, published 2026-11-02 at 16:50:15 UTC.
  GPT-OSS 20B was priced at $0.07/$0.30 per million input/output tokens;
  GPT-OSS 120B and Qwen 3 32B were each $0.15/$0.60.
- **Spend:** the comparison estimate was **$0.04194625**. The four-call
  compatibility probe added **$0.00015006**, for **$0.04209631 estimated total**
  under the $1.00 combined ceiling. These are token-rate estimates, not an AWS
  invoice.

The raw
[`capture-gpt-oss-2026-11-03.json`](capture-gpt-oss-2026-11-03.json) preserves
the full responses, traces, usage, costs and manual verdicts. The
[`gpt-oss-runtime-tool-probe-2026-11-03.json`](gpt-oss-runtime-tool-probe-2026-11-03.json)
preserves the separate compatibility probe. No credentials are included.

## Manually reviewed results

Pass/Partial/Fail verdicts apply only to conversations that completed all planned
turns. The two failed GPT-OSS 20B conversations remain in reliability counts and
cost accounting, but are excluded from semantic verdicts. “Missed tools” and
“unsupported claims” count the manually recorded conversation-level findings.

| Model | Pass / partial / fail | Evaluated / attempted conversations | Critical errors | Missed tools | Unsupported claims | HTTP errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen 3 32B | 4 / 4 / 1 | 9 / 9 | 1 | 2 | 2 | 0 |
| GPT-OSS 20B | 3 / 4 / 0 | 7 / 9 | 0 | 0 | 2 | 2 |
| GPT-OSS 120B | 4 / 4 / 1 | 9 / 9 | 1 | 0 | 3 | 0 |

| Model | Attempted turns / planned | Model calls | Input / output tokens | Estimated cost | Cost per pass | Median / max end-to-end latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen 3 32B | 16 / 16 | 38 | 104,565 / 2,376 | $0.01711035 | $0.00427759 | 1.623 / 5.268 |
| GPT-OSS 20B | 15 / 16 | 40 | 88,525 / 3,134 | $0.00713695 | $0.00237898 | 2.868 / 7.354 |
| GPT-OSS 120B | 16 / 16 | 44 | 98,713 / 4,820 | $0.01769895 | $0.00442474 | 2.644 / 7.630 |

Latency is end-to-end `/api/chat` wall time, including inference, local tool
execution, policy retrieval and local initialization. It is not model-only
latency. The sample is too small for stable tail-latency claims.

## Findings

- **GPT-OSS 20B:** the budgeted catalog lookup, ordinal follow-up, no-match,
  and selected-order scenarios were accurate. It failed on the PIX promotion
  follow-up after repeated unsuccessful product-name searches, then failed on
  the mixed return question with a malformed tool name containing a channel
  token. Both turns returned HTTP 500 and were categorized as local execution
  failures. The guest-order answer also began with an English internal-style
  sentence before asking for customer selection in Portuguese.
- **GPT-OSS 120B:** all 16 turns completed. The critical error was its first
  mixed-return answer: it said the return was still within the allowed period
  based on an imported delivered status, before learning the purchase channel or
  actual receipt date. It later handled the user’s five-day online-purchase
  follow-up conditionally. In other turns it added unsupported guitar
  specifications or preferences and repeated a policy lookup when the earlier
  answer already contained sufficient evidence.
- **Freight provenance:** all three models gave the correct R$ 500 result for
  the named metropolitan region. Each answer’s inline citations also associated
  PDF section 5.1 with the inclusive threshold, although equality is established
  by the separate owner-approved clarification. This is partial grounding, not
  a wrong amount or region.
- **Control:** Qwen was cheaper than GPT-OSS 120B in this run and completed all
  turns, but its missed fresh lookups, freight attribution and Natal answer
  remain relevant. The Natal claim is a critical policy-grounding failure.

These results do not support switching the project default. GPT-OSS 20B did not
match the control’s four passing conversations and had two execution failures;
GPT-OSS 120B matched the pass count but had a critical error. Neither GPT-OSS
candidate combined at least the control’s pass count with zero critical errors.
