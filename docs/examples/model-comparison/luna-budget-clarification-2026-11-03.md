# Luna budget-echo clarification benchmark

This experiment addresses Luna's one partial from the preceding v7 review: it
repeated the customer's budget amount in a catalog answer. It runs Luna alone
over the full v7 fixture and retains the prior order-total clarification.

## Finding and prompt change

The order-total sentence is scoped to order values and does not directly cover a
customer-provided catalog budget. In the first Luna-only run, the prompt included
the order-total clarification and an inline budget hint, but Luna still said
“por até R$ 1.000.” The captured system prompt confirms that hint was present.
The same budget wording appeared before the order-total change, so these runs
show no observed effect from that order-specific sentence on budget phrasing.

The smallest successful adjustment was to make the budget rule a separate,
direct sentence beside the catalog-search instruction:

> Não repita na resposta o valor de orçamento informado pelo cliente; diga “dentro do seu orçamento”.

With that sentence, Luna omitted the budget amount while still returning three
matching guitars with their current catalog prices, stock and the correct
ordinal follow-up. It did not need to repeat the budget to show which products
fit the requested filter.

## Luna-only full v7 runs

Each run used `--profile towelbooks-management-admin`, the frozen [v7 fixture](scenarios-current-v7.json),
12 conversations and 20 `/api/chat` turns. Qwen and Haiku were not invoked. The
runner was narrowly adjusted to permit a single selected model; multi-model
comparisons still require Qwen as the baseline.

| Prompt variant | Pass / partial / fail | Critical errors | Missed tools / unsupported claims | HTTP errors | Provider attempts / responses | Estimated cost | Median / max latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Inline budget hint | 11 / 1 / 0 | 0 | 0 / 0 | 0 | 40 / 40 | US$0.0134202200 | 2.478 / 5.174 s |
| Standalone direct rule | 12 / 0 / 0 | 0 | 0 / 0 | 0 | 40 / 40 | US$0.0136800125 | 2.332 / 9.203 s |

The first run's only Partial was `catalog-budget-ordinal`, for repeating
`R$ 1.000`; its products, prices, stock and ordinal follow-up were correct. The
second run passed that conversation and all 11 others. The mixed order/return
case also remained a Pass: Luna omitted the irrelevant total beside the item.
There were no execution failures, missing usage records, unknown request counts
or false refusals. Each run had 40 provider attempts/responses for 20 chat turns.

Combined estimated spend was **US$0.0271002325** of the approved **US$2.00** cap,
leaving **US$1.9728997675**. The second run used only the remaining cap after
the first run. These token-based estimates are not invoice amounts.

## Interpretation and limits

The direct wording coincided with the desired response in one full-suite sample;
it does not establish a general reliability rate or prove causality. Luna's
installed SDK ignores the requested temperature, so provider-default sampling
was used. Latencies include application and tool work, and the 20-turn sample is
too small for stable tail estimates.

The application output handler was unchanged; no semantic validator, retry or
additional model call was added. The benchmark's manual review scores factual
correctness, tool selection and presentation separately. The preflights made
zero paid calls. `git diff --check` passed; no test suite was run.

- [Reviewed first-run capture](capture-luna-budget-clarification-2026-11-03.json)
- [Reviewed second-run capture](capture-luna-budget-clarification-v2-2026-11-03.json)
- [Metrics](metrics-luna-budget-clarification-2026-11-03.json)
- [Second-run no-inference preflight](preflight-luna-budget-clarification-v2-2026-11-03.json)
