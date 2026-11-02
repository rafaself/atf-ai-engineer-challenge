# Nemotron holiday-policy smoke evaluation (#43)

## Scope and setup

On 2026-11-02, the owner approved one bounded run of each model, with a total
US$0.60 spending cap, on the existing two-turn holiday conversation. The models
were `nvidia.nemotron-super-3-120b` and `nvidia.nemotron-nano-3-30b`, using
Bedrock Runtime Converse in `us-east-1`. The official [Super model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-nvidia-nemotron-super-3-120b.html)
and [Nano model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-nvidia-nemotron-nano-3-30b.html)
list Runtime Converse. Prices were checked against [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/)
on the run date: Super $0.15/$0.65 and Nano $0.06/$0.24 per million input/output
tokens, standard tier. The exact model IDs, rates, and source links are frozen in
[`nemotron-pricing.json`](nemotron-pricing.json).

The runner used the production ASGI chat service, current context-aware persona,
local E5/Chroma policy retrieval and the existing evidence recorder. It did not
change production code or policy sources. The production revision was
`d8a80173c730aaf72653e230bfc4cc98bce5f56c`; capture source freezes record the
evaluation working tree and policy-index hashes. Cached local E5 retrieval was
preflighted before inference. Both preflight captures show `policy-v2.1-s2` from
`store_policies.pdf`, section 2, page 2. That one record contains normal hours,
holiday closure and the qualification that hours may be extended on special
dates including Natal.

The exact user turns were:

1. `Qual é o horário normal de funcionamento da loja?`
2. `E nos feriados e no Natal, há atendimento?`

Each model received one fresh conversation. The run used a 15-second HTTP request
timeout, 1,024 output-token limit, at most three provider requests and five tool
calls per HTTP turn. The first sandboxed attempt stalled before recording a
response. Its provider request count is unknown, up to five, and the full
US$0.19532800 first-turn reservation is carried forward. The retry was bounded to
12 possible requests; it observed eight. The combined worst-case reserve was
US$0.52335616, within the approved US$0.60 cap. The original 20-request approval
was therefore respected without exhausting the cap.

## Results

Tool selection and answer faithfulness are evaluated separately. In this
context-aware setup, a second policy lookup was unnecessary when the first
assistant answer had already conveyed both the normal rule and the special-date
qualification. A faithful follow-up should say that holidays are normally closed,
special Christmas hours are possible, and the specific Christmas schedule is not
confirmed by the available evidence.

| Model | First-turn retrieval | Follow-up tool choice | Follow-up faithfulness | End-to-end latency, turn 1 / 2 |
| --- | --- | --- | --- | ---: |
| Nemotron 3 Super 120B | Called `search_store_policies`; returned/cited section 2, p. 2 | No repeat lookup; appropriate because the prior answer retained the relevant rule and exception | **Fail.** Said the store was closed on holidays and Natal, omitting the possible extension and giving a definite Christmas outcome. It also asserted no WhatsApp service, which the source does not establish for that specific date. | 7.890 / 1.419 s |
| Nemotron 3 Nano 30B | Called `search_store_policies`; returned/cited section 2, p. 2 | No repeat lookup; appropriate for the same reason | **Fail.** Omitted the possible extension and invented continuous online service, email/chat support, delivery cutoffs and 24-hour availability. | 7.414 / 2.370 s |

Both first-turn answers accurately included the general holiday closure and the
possibility of extended special-date hours. Both completed the Runtime tool
round-trip and cited the policy source. The failure came on the follow-up: neither
model preserved the qualification in its answer. This shows retrieval supplied
sufficient evidence and that context reuse was a reasonable tool decision; it
does not show that either model reliably reasons about conditional policy text.

| Model | Reported input / output tokens | Provider requests observed | Known-usage cost plus missing-usage reserve |
| --- | ---: | ---: | ---: |
| Nemotron 3 Super 120B | 10,630 / 266 | 4 | US$0.04083300 |
| Nemotron 3 Nano 30B | 10,597 / 279 | 4 | US$0.01630854 |
| **Retry total** | **21,227 / 545** | **8** | **US$0.05714154** |

Costs are estimates, not invoice data. The retry reports positive provider token
usage and reserves one full-context request for each follow-up whose usage was not
captured. The initial interrupted attempt remains an additional US$0.19532800
reserve with unknown request count. The resulting conservative aggregate estimate
or reserve is US$0.25246954; the worst-case bound remains US$0.52335616.

## Accounting erratum

The original retry capture priced a zero-token replay of the previous assistant
response as though it were a metered provider response. The Boto request counter
observed two requests on each follow-up, while only one response in each follow-up
had positive token usage. The cost-derived fields now reserve one full request for
each missing usage record. `model_trace`, prompts, answers, tool calls, request
counts, timings and source freezes are unchanged. The original estimate
(US$0.00247018) is retained in the capture as an erratum reference. The first
interrupted capture now records its request count as unknown rather than zero.

## Recommendation and limits

The two samples support the current context-aware tool behavior for this case:
search once when the policy is missing, then reuse a prior answer that preserves
the evidence. They do **not** support choosing either Nemotron model for production
or claiming reliable conditional-policy reasoning. Both failed the same
follow-up, despite receiving the relevant policy through retrieval. Keep the model
selection unchanged based on this evidence alone; do not add another lookup or
prompt rule solely to compensate for this one sample.

This was a smoke comparison, not the full issue #40 matrix. It tested no product
topic switch, operational lookup or other policy. One conversation per model
cannot establish a model ranking, reliability, cost profile, or latency profile.
No further Bedrock inference was performed after this run. The earlier Qwen and
Nova captures and verdicts remain unchanged.

## Captures and reproduction

- [Retry preflight, no paid calls](nemotron-preflight-2026-11-02-retry.json)
- [Interrupted first attempt](nemotron-capture-2026-11-02.json)
- [Completed model traces](nemotron-capture-2026-11-02-retry.json)
- [Initial preflight](nemotron-preflight-2026-11-02.json)
- [Pricing manifest](nemotron-pricing.json)
- [Focused runner](../../../apps/backend/scripts/evaluate_nemotron_holidays.py)

The completed retry records the full prompt/evidence/answer traces and per-turn
HTTP timings; the interrupted first attempt preserves only its available attempt
metadata. A future run requires separate approval, a fresh output path and current
price/preflight checks; it must not overwrite these historical records.
