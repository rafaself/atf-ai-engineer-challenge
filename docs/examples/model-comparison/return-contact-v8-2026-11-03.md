# Return-contact experiment — 2026-11-03

The dedicated contact lookup did not solve the target answer failures. Both models
retrieved the relevant records, but omitted or overruled their limits. GPT-OSS
invented required documents and a label-issuance workflow in the follow-up. Qwen
avoided those concrete inventions but still implied undocumented support steps
and omitted contact discrepancies.

## Frozen scope and intervention

The [v8 fixture](scenarios-return-contact-v8.json) contains four conversations and
five HTTP turns per model: direct SAC/label, a contextual follow-up, conflicting
general contacts, and a document-checklist question. Expectations were written
before inference. This is a targeted diagnostic sample, not the 12-conversation
v7 regression suite or a measured overall reliability estimate. It has no rerun
of the old harness on identical v8 prompts, so it cannot establish a causal
improvement over v7.

The new explicit `return_contact` policy scope selects cover, 1.2, 4.1, 4.4 and 7
directly. The existing corpus supplies the original contact spellings, general
phone/WhatsApp entries, online-return rule and exclusions. Its guidance says:

- These are general contacts, not a designated returns SAC.
- The return rule documents no label, posting process or extra paperwork list.
- Show conflicting contact variants without choosing an authoritative one.
- Accessories/manuals are product conditions; missing manual documentation does
  not prove that a service is unavailable elsewhere.

The system and tool instructions route SAC, return contacts, label, posting and
paperwork requests to this scope. No production dependency, supplied source
bytes, corpus records or embedding input changed. Processing rationale is in
[data-processing.md](../../data-processing.md).

## Reviewed results

| Model | Pass / partial / fail | High-severity error entries | HTTP turns | Provider attempts / responses | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 0 / 4 / 0 | 0 | 5/5 successful | 10 / 10 | US$0.00596820 |
| GPT-OSS 120B | 0 / 2 / 2 | 2 | 5/5 successful | 10 / 10 | US$0.00532560 |

All responses were HTTP 200; usage was present for all provider responses.
Both models chose the new scope on three of the four intended contact/procedure
turns. Both used `online_return` for the documents-only question. The initial
general-policy turn correctly used `online_return` in both models.

Partial verdicts include missing contact variants, unsupported procedural hints,
or a missed scope even when much of the answer is correct. Fail means an
actionable unsupported contact decision or invented documents/label workflow.
The stricter targeted criteria explain why zero full passes should not be
compared directly with the broader v7 score.

| Conversation | Qwen3 32B | GPT-OSS 120B |
| --- | --- | --- |
| Direct SAC/label | Partial: acknowledges no dedicated return email/label rule, then gives only one general contact pair and refers to an SAC for guidance. | Partial: labels one general email as SAC, omits discrepancies and assumes SAC staff can explain the missing procedure. |
| Follow-up | Partial: reads fresh evidence and invents no paperwork or label promise, but presents general contacts as a route to obtaining a label. Its first answer also adds an unsupported refund-clock starting point. | Fail: invents order number, invoice/purchase proof and photo requirements; says staff will send a label by email/WhatsApp and explain posting. |
| Contact conflict | Partial: gives both phones but omits the cover email spelling and uses an ambiguous official-SAC heading. | Fail: lists the variants correctly, then selects one pair as official and says any general contact can handle returns. |
| Documents only | Partial: wrong scope; correctly lists product conditions but turns manual silence into a categorical claim that no documents are needed. | Partial: wrong scope; correctly says the paperwork is not mentioned, then paraphrases no signs of use as no use and introduces an unsupported SAC. |

The [reviewed capture](capture-return-contact-v8-2026-11-03.json) contains the
unchanged turn prompts, HTTP answers, tool arguments, usage and source freeze,
plus per-conversation review notes. No exact-prose automated judge was used.

## Interpretation and next boundary

The key failure is answer faithfulness after retrieval. More complete source
selection helps expose the facts, but both models can ignore explicit guidance.
GPT-OSS's follow-up is direct evidence: it received the specialized scope, then
invented the exact document and label process the scope warned against. Qwen's
remaining errors are less specific but still prevent a fully supported answer.

A justified next experiment is a narrow application-owned response for these
procedure/contact questions, generated from reviewed policy data: show general
contact variants, retain unresolved authority, and state what the manual does
not document. The model can continue normal conversation, but should not author
operational return promises. This experiment did not implement that boundary.
More prompt repetition alone is not supported as a sufficient remedy.

## Validation and accounting

The focused retrieval regression was observed failing before the scope existed
and passing after implementation. Policy retrieval and fake-model agent checks:
17 passed. Ruff lint, formatting, strict mypy and diff checks passed. The initial
sandboxed agent tests stalled; the same focused checks passed outside the sandbox.

The first [no-inference preflight](preflight-return-contact-v8-2026-11-03.json)
found local retrieval ready but its Bedrock account check was network-blocked;
it made zero paid calls. The authorized network-enabled evaluation completed
under a US$0.70 remaining-budget cap. Estimated paired cost: US$0.01129380.
Adding the previously recorded US$0.29924685 gives US$0.31054065 of the approved
US$1.00, leaving US$0.68945935. These are token-based estimates, not an invoice.
