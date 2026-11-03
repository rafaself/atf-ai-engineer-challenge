# Remediated Qwen3 32B and GPT-OSS 120B benchmark — 2026-11-03

## Outcome

After tightening the agent instructions and clarifying policy evidence in the
processed corpus, Qwen3 32B and GPT-OSS 120B each completed all nine conversations
and 16 planned chat turns. Every HTTP turn returned 200; there were no HTTP
errors or missing token-usage records. The 82 model calls cost an estimated
**US$0.03868080**, under the separately approved US$0.95 cap. This is a token-rate
estimate, not an AWS invoice.

| Model | Pass / partial / fail | Critical errors | Missed tools | Unsupported claims | HTTP errors | Model calls | Estimated cost | Cost per pass | Median / max latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 6 / 2 / 1 | 1 | 1 | 2 | 0 | 39 | $0.01945620 | $0.00324270 | 1.891 / 5.964 |
| GPT-OSS 120B | 5 / 4 / 0 | 0 | 0 | 2 | 0 | 43 | $0.01922460 | $0.00384492 | 2.995 / 6.081 |

The reviewed
[`capture-remediated-qwen32-gptoss120-2026-11-03.json`](capture-remediated-qwen32-gptoss120-2026-11-03.json)
contains the prompts, responses, tool traces, token usage, costs, and manual
verdicts. The capture records 119,680 input and 2,507 output tokens for Qwen,
and 106,368 input and 5,449 output tokens for GPT-OSS 120B.

## Changes evaluated

- The system instructions now prohibit inferring instrument specifications from
  product names, categories, brands, prices, or appearance. They also require
  confirming each return condition instead of treating the seven-day window as
  sufficient for eligibility.
- The processed policy corpus now makes the Natal ambiguity explicit: regular
  Sundays and holidays are closed, but the manual names Natal as a special date
  when hours may be extended. It gives no schedule for a specific Natal; an
  extension is possible, not confirmed, and changes are announced in advance.
  The original supplied PDF remains unchanged.
- The application labels the inclusive freight threshold as coming from the
  approved clarification, separately from the manual's strict “above R$500”
  wording.

## Findings

- **Natal:** GPT-OSS 120B preserved the distinction between regular holiday
  closure and a possible announced special schedule. Qwen's first answer stated
  the exception correctly, then on the follow-up categorically said the store
  was closed on Natal and that there would be no service. This contradicts both
  the retrieved evidence and its own prior answer, so the critical failure
  remains. Processed data made the rule clearer but did not prevent Qwen from
  overriding it in conversational context.
- **Product specifications:** Qwen reported the zero-stock item and catalog
  alternatives without inventing characteristics. GPT-OSS 120B still added
  unsupported comparisons about nylon comfort and steel sound, and inferred a
  color preference from the unavailable product's name. The prompt reduced this
  failure for Qwen but did not eliminate it across models.
- **Return eligibility:** both models kept the five-day report within the
  seven-day period but failed to gather every required condition. Qwen suggested
  checking order data for product-condition facts that the order tool cannot
  establish. GPT-OSS 120B did not ask the customer to confirm those facts and
  invented contact and return-shipping steps absent from the policy evidence.
- **Freight provenance:** GPT-OSS 120B correctly distinguished the PDF wording
  from the approved equality clarification. Qwen gave the correct amount and
  region, but its inline citation still attributed equality to the PDF; the
  application's appended note then gave the correct separate provenance.
- **Tool use:** Qwen missed the policy lookup on the first return turn. GPT-OSS
  120B made an unnecessary extra catalog lookup after already answering the
  product-detail question, and repeated a policy lookup when prior evidence was
  sufficient.
- **HTTP reliability:** both models completed every turn. This run observed no
  transport, provider, or local HTTP failures.

Compared with the preceding Qwen control in the
[GPT-OSS 20B retry report](gpt-oss-20b-retry-2026-11-03.md), this Qwen run had
one more Pass (6 versus 5), while retaining the same Natal critical error. The
earlier GPT-OSS 120B run had 4 Pass / 4 Partial / 1 Fail and one critical error;
this run had 5 / 4 / 0 and no critical errors. These are single-run observations,
not evidence that the code changes alone caused the score differences or that
either model is broadly reliable.

End-to-end latency is `/api/chat` wall time, including model inference, local
tools, retrieval, and local initialization. It is not model-only latency.
