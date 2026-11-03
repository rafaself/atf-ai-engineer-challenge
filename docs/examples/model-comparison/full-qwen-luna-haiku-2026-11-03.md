# Full Qwen / GPT-6 Luna / Haiku 5.5 benchmark

GPT-6 Luna and Haiku 5.5 both completed the full benchmark with substantially
stronger answers than the fresh Qwen control in this sample. Each new model has
one minor partial result and no failed conversation or critical error. Luna
produced shorter answers, used fewer reported input/output tokens, and had lower
observed latency and conservative estimated cost than Haiku.

## Setup and comparability

The owner approved a fresh **US$4.00 cap** after the no-inference preflight.
The runner used `--profile towelbooks-management-admin`, the current application
and v9 prepared corpus, and the unchanged [full v7 fixture](scenarios-current-v7.json):
12 conversations / 20 HTTP turns per model. Each model had isolated conversation
storage and a temporary policy-index copy. No model-specific prompt tuning,
dependency update, production default-model change or added inference stage was
made. All inference used Bedrock Runtime Converse:

- Qwen control: `qwen.qwen3-32b-v1:0`.
- Luna: `us.openai.gpt-6-luna`.
- Haiku: `us.anthropic.claude-haiku-5-5`.

The application requested temperature zero, six requests / five tool calls,
1,024 output tokens and a 15-second provider timeout. The installed SDK recognizes
the new models and omits their unsupported sampling parameters. Their effective
temperature was therefore not controlled at zero; reasoning used provider defaults
without an effort override. This comparison assesses the existing application
through its supported provider interface, not identical decoding conditions.

AWS CLI confirmed both system profiles ACTIVE and both foundation models
authorized/available. The live benchmark additionally established successful
client-tool Converse roundtrips for both profiles. The preflight by itself did
not establish that compatibility. See [readiness and sources](luna-haiku-full-2026-11-03.md).

## Results

| Model | Pass / partial / fail | Critical errors | HTTP turns | Provider attempts / responses | Median / max end-to-end seconds | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 9 / 1 / 2 | 1 | 20/20 successful | 42 / 42 | 1.498 / 4.279 | US$0.02307285 |
| GPT-6 Luna | 11 / 1 / 0 | 0 | 20/20 successful | 41 / 41 | 2.006 / 6.533 | US$0.0137254425 |
| Haiku 5.5 | 11 / 1 / 0 | 0 | 20/20 successful | 41 / 41 | 4.804 / 10.715 | US$0.02924273 |

All **60 HTTP turns** returned 200. There were **124 provider attempts and 124
current model responses**, no missing usage, no recorded corrective retry parts,
and no final responses stopped by the token cap. Each model has 20 normal final
stops. Model responses reconstructed from assistant history are excluded from
the current-call counts. No false refusal was observed. Qwen unnecessarily asked
to repeat a product lookup after supplying a wrong ID; the new models did not
block a supported answer with that question.

| Conversation | Qwen | Luna | Haiku |
| --- | --- | --- | --- |
| Budget / ordinal product follow-up | Pass | Pass | Pass |
| Unavailable named product / alternative | Fail | Pass | Pass |
| Promotion / PIX stacking follow-up | Fail | Pass | Pass |
| No catalog match | Pass | Pass | Pass |
| Selected customer's orders / detail | Pass | Pass | Pass |
| Guest order request | Pass | Pass | Pass |
| Regular hours / Natal / product topic change | Pass | Pass | Pass |
| Mixed order / return follow-up | Pass | Partial | Pass |
| Exactly R$500 metropolitan freight | Pass | Pass | Pass |
| Outside online-return window | Pass | Pass | Pass |
| Used item without marks / SAC and label | Partial | Pass | Partial |
| In-store preference exchange | Pass | Pass | Pass |

## Failures and partials

**Qwen — unavailable-product alternatives, fail.** It correctly found the
zero-stock Giannini as product 96, then called alternatives with product 1002.
The tool could not resolve that original ID. Qwen asked permission to look up a
model already identified and delivered no usable alternative. It also offered
future-availability checks that the tools do not provide. This is an answer/tool
failure despite HTTP 200; no specific new stock or restock date was invented.

**Qwen — promotion/PIX, fail and critical availability error.** Its promotion list
and prices were correct, but it interpreted second item as product ID 2 rather
than the Ohana code 121. The empty wrong-ID result became a false claim that the
requested product was unavailable, although the actual item had six in stock.
It also failed to answer the discount-stacking question. The initial promotion
list omitted product codes, a presentation defect that may contribute to this
kind of reference failure; the causal link is not established here.

**Qwen — used item / procedure, partial.** It correctly said no dedicated returns
SAC email or label process was documented, and did not promise label issuance.
It gave only the unaccented general email without disclosing the other source
spelling. Its initial assessment was more tentative than the supplied facts
required. No new email address was fabricated.

**Luna — mixed order/return, partial for clarity.** The initial answer says the
order contains one Giannini followed immediately by `(R$799,90)`. The returned
field labels that amount only as the order total, not item unit price. The number
is supported; the partial records ambiguous total-versus-item presentation,
not a proven invented numeric price. Its tool use, remaining-condition questions,
seven-day window and conditional follow-up were correct. No critical error was
assigned.

**Haiku — used item / procedure, partial.** It preserved opened packaging versus
sealed packaging, use versus signs of use, both email spellings, contact roles
and the undocumented label/paperwork limit. It also stated that the physical
condition would be checked by the store and that only store analysis confirms
the condition. This is an undocumented inspection/confirmation step. It did not
invent a documentary requirement or promise a label. No critical error was
assigned.

Both new models preserved Natal uncertainty and the inclusive freight boundary,
resolved ordinal product references, kept promotion/PIX discounts separate and
respected customer selection. Their contact/label answers explicitly said the
manual did not designate a returns SAC and that the assistant could not issue
labels. This contrasts with earlier GPT-OSS/Qwen procedure hallucinations, but
those historical runs used different source/harness revisions and are not a
fresh controlled comparison against GPT-OSS 120B.

## Separate tool and UX review

Current instructions route label/contact questions through `return_contact`.
The frozen v7 text names `online_return` on that follow-up, but both scopes supply
4.1/4.4 and the current contact scope additionally supplies contact excerpts. Using
that current route was recorded as appropriate evidence selection, not an automatic
factual failure. General contacts may be suggested for questions without promising
that a particular team fulfills a return.

Qwen and Haiku repeated a policy lookup after already preserving sufficient Natal
context. Qwen unnecessarily reread the order after the customer supplied receipt
and purchase-channel facts. Luna fetched original-product details before calling
alternatives; Haiku additionally read return contacts on the initial used-item
turn. These efficiency notes did not turn otherwise factual answers into failures.
Minor product-code omissions and repeated partial-list notices were recorded
separately from wrong product selection, incorrect availability or unsupported
operational claims. Each scenario's exact judgment is in the reviewed capture.

Mean answer words excluding the source footer: Qwen **69.6**, Luna **47.6**,
Haiku **110.3**. Haiku's extra detail is often supported but can exceed what the
question needs. End-to-end latency includes tool work and local initialization;
20 samples per model do not establish stable tail latency or inference-only speed.

## Accounting

| Model | Input tokens | Output tokens | Cache read / write tokens |
| --- | ---: | ---: | ---: |
| Qwen3 32B | 140,715 | 3,276 | 0 / 0 |
| Luna | 101,653 | 3,118 | 71,436 / 30,135 |
| Haiku | 213,913 | 10,386 | 0 / 0 |

Reported input totals include cache tokens. The Luna estimate charges cache reads
at full standard input rates and includes the documented implicit cache-write
premium, so it is conservative rather than a discounted invoice calculation.
Haiku explicit caching was not enabled. No request entered a long-context tier:
maximum reported request input was 3,597 for Luna and 8,273 for Haiku. The budget
reservation nevertheless covered their verified full context and long-context
rates before every HTTP turn.

Total estimated run cost: **US$0.0660410225 of the fresh US$4.00 approval**;
remaining fresh cap: US$3.9339589775. Adding the prior session's US$0.38084325
gives cumulative estimated session spend US$0.4468842725. These are token-based
estimates, not invoice amounts. No credential values were inspected or printed.

## Validation and decision

Final backend suite: **379 passed**. The 26 benchmark tests also passed after
changing the owner-approved ceiling from US$1 to US$4, including rejection above
the approved cap, exact profile routes, explicit profile precedence, tiered
pricing, implicit cache-write accounting and provider-failure stopping behavior.
Ruff lint/formatting and diff checks passed. Application instructions, tools,
operational data and prepared policy content were not changed for this evaluation.

Luna is the strongest next candidate from this run: it matched Haiku's overall
review outcome with shorter answers and lower observed latency/cost. These are
one-pass diagnostic results on 12 conversations, with subjective partial judgments
and different effective decoding behavior. They do not prove general reliability
or authorize changing the production default. No further paid evaluation was run.

- [Reviewed full capture](capture-full-qwen-luna-haiku-2026-11-03.json)
- [Separate metrics](full-qwen-luna-haiku-metrics-2026-11-03.json)
- [Frozen full fixture](scenarios-current-v7.json)
- [Pricing manifest](pricing.json)
- [Readiness and official pricing/API references](luna-haiku-full-2026-11-03.md)
