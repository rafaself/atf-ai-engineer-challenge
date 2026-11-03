# Structured return evidence experiment — 2026-11-03

Both models completed all nine conversations and 16 turns using the active v3
fixture, with zero HTTP errors and no missing token usage. The 80 provider calls
cost an estimated **US$0.02733330**. Combined with the preceding run's
US$0.02442870, cumulative estimated spend is **US$0.05176200**, within the
approved US$1.00. This run's enforced cap was the remaining US$0.97557130.

| Model | Pass / partial / fail | Critical errors | Missed tools | Unsupported claims | Calls | Estimated cost | Median / max latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 4 / 4 / 1 | 1 | 1 | 4 | 39 | $0.01443150 | 2.123 / 6.695 |
| GPT-OSS 120B | 5 / 4 / 0 | 0 | 2 | 3 | 41 | $0.01290180 | 2.561 / 5.750 |

The reviewed [capture](capture-structured-return-qwen32-gptoss120-2026-11-03.json)
preserves prompts, outputs, traces, hashes, usage, and per-conversation notes.
Scores use the unchanged [v3 criteria](scenarios-current-v3.json).

## Changes

Retrieved manual section 4.1 now carries a typed `online_return_rule` alongside
the original excerpt and source: seven calendar days after actual receipt is
the request deadline, zero days is the minimum wait, and eligibility requires
online purchase, actual receipt date, original packaging, no signs of use,
accessories, and manuals. This reviewed source projection does not decide
eligibility or remove exclusions. Other sections receive no such metadata.
The original corpus, supplied CSV/PDF bytes, index, model settings, and scenario
prompts were unchanged in this experiment.

The policy tool description explicitly covers mixed order/policy questions.
The prompt clarifies deadline versus waiting period. The alternative-search
description tells models to omit the unavailable model name and use only a
customer-requested budget.

## Target outcomes

- **Qwen return reasoning improved.** It called both order and policy tools,
  received the structured rule, correctly put five days inside the window,
  and explicitly requested the remaining condition facts. The conversation
  remained Partial because it repeated the order lookup unnecessarily and
  suggested proceeding with a return process beyond the read-only tools.
- **GPT-OSS did not test the structured evidence path.** It called only
  `list_my_orders`, omitting both the requested order details and policy lookup.
  It gave the correct seven-day window this time, but added sealed/intact
  packaging, automatic exclusion for any use, and a posting-label/return workflow
  unsupported by the manual or tools. Its return conversation remained Partial.
  The absence of the preceding run's day-eight error cannot be attributed to
  metadata it never received.
- **Both alternative searches removed the unavailable-name filter.** Qwen
  then invented a R$700–800 budget. GPT-OSS returned real alternatives but
  invented sound, projection, softness, and suitability claims absent from the
  structured specifications. Both conversations remained Partial.

## Other observed failures

Qwen again skipped the ordinal product refresh. Its PIX final price was correct,
but it inaccurately said the PIX discount was already included in the promotion.
It retrieved normal hours correctly, then categorically denied Natal service
despite the explicit exception and invented a general Monday reopening. The
Natal contradiction was the sole critical error in this run.

GPT-OSS preserved uncertainty about a specific Natal, but searched policy twice
despite sufficient context. It also changed a product name by inserting a dash,
causing a failed PIX lookup followed by a corrective search and lookup. Final
prices, scoped order facts, guest isolation, no-match handling, and freight
clarification were otherwise correct.

## Interpretation and validation

Compared with the preceding run, Qwen went from 5/3/1 to 4/4/1 and GPT-OSS from
6/2/1 to 5/4/0. The critical error moved from GPT-OSS return handling to Qwen
Natal handling. These single-pass results show a useful local improvement in
Qwen's return evidence path, without establishing a general reliability gain.
Tool selection remains a prerequisite for structured evidence to help.

The focused policy checks passed (15 tests); Ruff and strict mypy passed.
The full suite initially found seven stale assertions from earlier authorized
changes: request allowance, freight provenance notice, registered model count,
and manifest review dates. Those expectations were corrected while retaining
expiry and provider-stop assertions. The final full suite passed: **362 tests**.
A failing baseline for the new regression was not
independently captured; its passing result verifies the implemented path.
