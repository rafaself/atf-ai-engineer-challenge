# Luna order-total clarification benchmark

This focused experiment tests one small system-prompt clarification against the
full frozen v7 benchmark, with Qwen3 32B as the required control. The target is
Luna's earlier ambiguous placement of an order total beside the product name.

## Change under test

The order instruction in `persona.py` now adds:

> Se mencionar um valor de pedido, identifique-o como total do pedido; não o apresente como preço unitário sem esse dado no registro do item.

Previously, Luna wrote the Giannini item followed by `(R$ 799,90)`. The order
evidence identified R$ 799,90 as the order total and did not give a unit price
for that item. The number was supported, but its placement could be read as an
item price; the earlier review marked that presentation Partial rather than
calling it a fabricated amount.

## Run and results

The user approved a fresh **US$2.00 cap**. The benchmark used
`--profile towelbooks-management-admin`, Bedrock Runtime Converse, and the
unchanged [v7 fixture](scenarios-current-v7.json): 12 conversations and 20
`/api/chat` turns per model. A no-inference preflight confirmed pricing, model
routes and local policy retrieval before the paid run.

| Model | Pass / partial / fail | Critical errors | Missed tools / unsupported claims | HTTP errors | Provider attempts / responses | Input / output tokens | Estimated cost | Median / max latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B control | 7 / 2 / 3 | 3 | 2 / 4 | 0 | 39 / 39 | 131,173 / 3,866 | US$0.02199555 | 2.167 / 4.630 s |
| GPT-6 Luna | 11 / 1 / 0 | 0 | 0 / 0 | 0 | 42 / 42 | 105,372 / 3,387 | US$0.01428724 | 2.434 / 6.668 s |

All **40 HTTP turns** returned 200. The 81 provider attempts/responses include
model steps used for tool calls; they are not additional customer turns. There
were no execution failures, missing token usage, or unknown request counts.
Estimated spend was **US$0.03628279** of the approved US$2.00, leaving
**US$1.96371721**. These are token-based estimates, not invoice amounts.

## Target result and remaining partial

Luna now passes `mixed-order-return-followup`. Its first answer names the item
without appending the order total where the amount is not needed. It still
preserves the seven-day return window and asks only for the remaining eligibility
conditions. In the separate order-list scenario, the order amount is explicitly
identified as `Total do pedido: R$ 799,90`.

The aggregate remains **11 / 1 / 0**. The current review marks Luna's
`catalog-budget-ordinal` conversation Partial because the answer repeats the
customer's `R$ 1.000` budget instead of referring to “seu orçamento,” per the
owner's source-only monetary-output preference. That is separate from the order
clarification and was not marked as a partial in the previous Luna review. The
target case improved, but the aggregate score is not an apples-to-apples measured
increase: the review basis now also records that budget-echo preference.

Qwen's control had three failures: it fabricated a Takamine code and price after
skipping the required lookup, described contacting general store channels as a
return procedure, and mislabeled the general email as a returns SAC while
inventing a follow-up process. Its two partials were the same budget echo and
an alternative-product response that used the wrong original product ID and
offered unsupported future-availability checks.

## Reproducibility and limits

The scenario fixture and supplied source-data hashes match the preceding full
v7 run. The captured system instructions differ by the added order-total
sentence, and nine compared policy lookup outputs had identical IDs and text.
The aggregate application-source hash differs, as expected after the prompt
edit, and the local Chroma index binary hash also differs; therefore the run is
not a byte-for-byte environment replay. Luna's installed SDK also omits the
unsupported temperature parameter, so provider-default sampling was used.

This is one full-suite run, not a repeated reliability estimate or proof that the
sentence alone caused the target change. No tests were run; `git diff --check`
passed. The complete traces, prompt snapshots and manual scenario judgments are
in the [reviewed capture](capture-luna-order-total-2026-11-03.json), with a
[metrics extract](metrics-luna-order-total-clarification-2026-11-03.json) and
[preflight record](preflight-luna-order-total-network-2026-11-03.json).
