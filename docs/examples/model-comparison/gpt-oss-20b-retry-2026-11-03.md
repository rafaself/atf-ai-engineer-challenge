# GPT-OSS 20B retry — 2026-11-03

## Result

The second GPT-OSS 20B run completed all nine conversations and all 16 planned
HTTP turns. The two conversations that had previously stopped with local
execution HTTP 500s now completed, and the retry produced **zero HTTP errors**.
The 20B model cost an estimated **US$0.00732175** for this run.

The HTTP failures were addressed, but 20B still does not meet the selection
gate. It had **5 Pass / 2 Partial / 2 Fail** conversations, including **two
critical errors**. Fresh Qwen 3 32B completed the same fixture with 5 Pass / 3
Partial / 1 Fail and one critical error. Both have five passing conversations;
neither has zero critical errors.

## Changes tried

The prior failures suggested three small adjustments:

- Increase the default per-turn model request limit from five to six, leaving
  room for final answer synthesis after a turn uses five tool calls.
- Retry an unknown tool name once. The malformed
  `search_store_policies<|channel|>commentary` call in the first return turn was
  rejected, then the valid policy lookup ran and the HTTP request completed.
- Normalize Unicode dash punctuation during catalog name matching. The PIX
  follow-up now found the Ohana CK-20 in one `get_product_details` call and
  correctly returned R$ 439.20 without stacking the PIX discount.

These changes target the observed failure modes. This was one retry per
scenario, so it does not establish that HTTP reliability is stable across runs.

## Manually reviewed results

| Model | Pass / partial / fail | Evaluated / attempted conversations | HTTP turns attempted / planned | Critical errors | Missed tools | Unsupported claims | HTTP errors | Model calls | Estimated cost | Cost per pass | Median / max end-to-end latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen 3 32B | 5 / 3 / 1 | 9 / 9 | 16 / 16 | 1 | 0 | 2 | 0 | 40 | $0.01841040 | $0.00368208 | 1.850 / 5.241 |
| GPT-OSS 20B | 5 / 2 / 2 | 9 / 9 | 16 / 16 | 2 | 0 | 2 | 0 | 41 | $0.00732175 | $0.00146435 | 3.288 / 6.937 |

Latency is end-to-end `/api/chat` wall time, including model inference and local
tool execution; it does not isolate inference speed. No calls had missing token
usage. The combined estimated cost for the two models was **US$0.02573215**.
Including the prior GPT-OSS comparison and its separate compatibility probe,
the recorded cumulative estimate is **US$0.06782846**. These are estimates,
not an AWS invoice.

## Remaining quality issues

- **Policy hours — critical for both models:** both answered that the store is
  closed on Natal, despite also retrieving the policy that special-date hours
  may be extended. The evidence does not establish the schedule for a specific
  Natal. GPT-OSS 20B repeated the policy lookup but still contradicted it.
- **Return eligibility — critical for GPT-OSS 20B:** after the customer said the
  online order was received five days ago, 20B said the item could be returned
  without checking whether it was unused, in original packaging, and included
  its accessories and manuals. It also invented a “Meus Pedidos” → “Solicitar
  Devolução” workflow absent from the policy and application tools. Qwen listed
  the conditions but did not ask the customer to confirm them, so that answer
  was rated Partial.
- **Unsupported product descriptions:** 20B described guitar body types and
  relative sizes that were not returned by the catalog tool.
- **Internal-style text:** the guest-order answer began with “We need to ask user
  to select a customer.” before continuing in Portuguese. The tool guard still
  withheld order details.

## First run versus retry

| GPT-OSS 20B run | Pass / partial / fail | Evaluated / attempted conversations | HTTP turns attempted / planned | Critical errors | HTTP errors | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First run | 3 / 4 / 0 | 7 / 9 | 15 / 16 | 0 among evaluated cases | 2 | $0.00713695 |
| Retry | 5 / 2 / 2 | 9 / 9 | 16 / 16 | 2 | 0 | $0.00732175 |

The first run's two failed conversations had no semantic verdict. The retry
made them reviewable and exposed the policy and return-condition failures. Its
slightly higher total reflects completing both conversations; the per-pass
estimate decreased from $0.00237898 to $0.00146435.

The raw
[`capture-gpt-oss-20b-retry-2026-11-03.json`](capture-gpt-oss-20b-retry-2026-11-03.json)
preserves responses, tool traces, usage, costs and manual verdicts. The earlier
[`GPT-OSS comparison report`](gpt-oss-runtime-2026-11-03.md) and its captures
remain unchanged.
