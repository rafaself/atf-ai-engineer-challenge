# Four representative Portuguese conversations

These are actual recorded Bedrock conversations, not mocks or new US-23 runs.
The linked transcripts retain prompts, answers and tool evidence. They demonstrate
behavior at their recorded revisions; they do not prove current model quality.
No new paid evaluation was performed for this selection.

| Conversation | Coverage | Model, date and revision | Review boundary |
| --- | --- | --- | --- |
| [Catalog and contextual follow-ups](sprint-2/closure/01-guest-catalog-context.md) | Availability, GD20 price, budget, fresh product lookup, weather scope redirection | Qwen3 32B, 2026-11-01, `8b9c321` | Passed the recorded source-based review; predates current output handling and UI |
| [Promotions and PIX](sprint-2/closure/02-guest-promotions-pix.md) | Promotion pricing, contextual payment follow-up, no discount stacking | Same batch/model/revision | Passed the recorded review; does not establish current generated-price accuracy |
| [Customer orders](sprint-2/closure/03-customer-orders-context.md) | Fictional customer 1, list/detail context, historical totals and snapshot limits | Same batch/model/revision | Passed the recorded review; snapshot caveat was explicit when asked |
| Mixed order/return, below | Real operational and policy tool calls, unresolved eligibility facts and safe HTTP failure | Qwen3 32B, capture saved 2026-11-02, `4f36cf5` | Failed HTTP delivery and incomplete policy applicability; candidates were not delivered |

The first three conversations contain ten HTTP turns. Their [batch metadata and
failed attempts](sprint-2/closure/README.md) remain part of the evidence. Model:
`qwen.qwen3-32b-v1:0`, region `us-east-1`. The fourth is the first attempted turn in
[the US-18 grounding batch](us-18/grounding-batch-qwen.json), whose protocol records
application revision `4f36cf508d6e1be3cc0a6e4b8cff766f54d1b6ef`, the same model and
region, and capture-save time `2026-11-02T05:12:58.924347+00:00`.

## Mixed order/return: actual failed exchange

**User:** Meu pedido 4 consta como entregue. Confira o pedido e me diga se posso devolvê-lo agora.

**HTTP response:** 500, `{"detail":"Conversation failed"}`. No assistant answer
was successfully delivered. The batch stopped; its other five turns were not run.

Actual `get_my_order` and `search_store_policies` calls succeeded. Policy retrieval
returned sections 4.3, 4.1, 5.2 and 4.4. The generated candidates were rejected by
the citation parser used at that revision. Their policy reasoning also omitted
online-purchase applicability and failed to resolve channel, receipt date and
condition before applying the rule. The exact candidate text and tool results
remain in the linked capture; the [source-based review](us-18/results.md#finding-5-authorized-current-code-grounding-batch)
explains the failure without rewriting a candidate as a successful delivered reply.

Current code has retired that citation grammar. A controlled replay accepts the
saved candidate; this proves delivery under the changed validator, not correction
of its semantic omissions or a new live-model success. Earlier
[US-18 policy conversations](us-18/live-captures.json) include an actual successful
return-policy response, with a [review](us-18/results.md); they are supplemental
historical evidence and lack an exact application SHA in their capture.

## Failures and current limits

The same US-18 batch failed the mixed order/return case: the answer treated an
estimated delivery date as evidence of receipt and omitted important qualifications.
The [US-17 comparison](us-17/results.md) also preserves missed policy lookups,
unsupported claims and a RAG HTTP 500. Later [US-18 results](us-18/results.md)
record repeated attempts and the eventual removal of brittle prose validators.
A saved answer accepted by a controlled replay is not a new successful model run.

Offline tests establish application contracts, persistence, isolation and error
handling. They cannot establish autonomous tool choice, generated price accuracy
or policy applicability. Further paid model runs require separate explicit approval.
