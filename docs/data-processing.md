# Data processing decisions and next changes

Recorded: 2026-11-03. Related work: issue #43 and the model-comparison experiments.

This document explains the processing applied to the supplied data, why it is
needed, and the next agreed changes. It is a decision log, not evidence that
every planned transformation has been implemented or evaluated.

## Purpose and source boundaries

The challenge permits cleaning, transformation and indexing of the supplied
data. Processing should present coherent, useful evidence to the agent while
preserving the supplied CSV/PDF bytes and their original checksums.

Keep the original sources, approved business clarifications and derived effective
rules distinguishable in internal provenance. Customer answers should communicate
the effective store rule without explaining ingestion history. Unknown schedules,
contacts, customer facts and procedures must remain unknown unless a source or
explicit business decision resolves them.

## Existing processing

| Data | Processing already present | Reason |
| --- | --- | --- |
| Catalog CSVs | Validate records/references; convert prices to exact integer centavos; normalize lookup names; preserve source fields and expose structured specifications | Reliable search, exact prices, and evidence for product characteristics |
| Promotions | Calculate final quotes with promotion precedence and non-stacking PIX rules | Keep authoritative monetary calculations outside model prose |
| Order CSVs | Validate and import customer-scoped order/item projections; preserve historical totals | Simulate operational lookups without reconstructing historical prices from current catalog prices |
| Policy PDF | Extract with Poppler; normalize layout, tables and sections; preserve source sections/pages; build the local E5 index | Make policy evidence searchable and readable |
| Freight | Add the separate owner-approved inclusive R$500 clarification to the prepared corpus | Resolve the PDF's equality gap using an approved business decision |
| Natal | Append an explicit interpretation that the specific Natal schedule remains unconfirmed | Preserve the special-date qualification alongside the general holiday rule |
| Online returns | Attach structured section 4.1 metadata at retrieval time: seven-day request deadline, zero minimum wait, and required customer facts | Reduce confusion between a deadline and a waiting period |

The preparation code is in `apps/backend/src/emporio_music_backend/policy_corpus.py`;
the return metadata is currently attached in `agent/policies.py`. The current
Natal representation still combines the original schedule with a longer appended
interpretation. The canonical replacements below are planned, not yet generated.

## Planned canonical opening-hours evidence

Prepare one coherent model-facing schedule in place of the original schedule plus
an appended explanation. Retain internal provenance to manual section 2, page 2.

Proposed Portuguese evidence:

> **Segunda a sexta-feira:** 09h às 18h.
>
> **Sábado:** 09h às 13h.
>
> **Domingos e feriados, com exceções de datas especiais:** fechado no horário
> regular; veja a regra de datas especiais abaixo.
>
> **Datas especiais — Natal, Black Friday e aniversário da loja:** pode haver
> atendimento em horário especial ou estendido. Os horários especiais de cada
> ocorrência não estão informados. Para um Natal específico, o manual não confirma
> abertura nem fechamento. Alterações são comunicadas previamente nas redes sociais
> e no atendimento via WhatsApp.
>
> O atendimento via WhatsApp segue os horários da loja, com respostas automáticas
> fora do expediente.

The exception is visible in the holiday label itself, and the special-date rule
starts with the possibility of service. Natal, Black Friday and the anniversary
are all retained because the source names all three; this does not classify all
three as public holidays. Possible special service is an interpretation of the
manual's extended-hours clause, not confirmation that the store will open.
No opening time, universal holiday exception, or Monday reopening is inferred.

Observed motivation: Qwen retrieved the existing explicit Natal interpretation
and still asserted closure. This is an answer-faithfulness failure. The proposed
representation removes competing emphasis; its effect on model behavior remains
to be evaluated.

## Planned effective freight evidence

During preparation, apply the already-approved clarification directly to the
effective section 5.1 presented to the model:

| Delivery area | Total | Fee |
| --- | --- | --- |
| Região Metropolitana de Campo Grande | Below R$500.00 | R$35.00 |
| Região Metropolitana de Campo Grande | R$500.00 or more | Free |

Preserve the source's delivery estimate and other applicable clauses. Retain the
original PDF and separate approval record internally. Avoid returning the original
ambiguous threshold as a competing active rule. Remove the automatic customer
notice explaining the equality clarification; customer-facing references must
still describe the processed policy truthfully rather than attribute amended
wording literally to the original PDF.

## Planned return-rule preparation

Move the existing structured projection from retrieval-time code to prepared
policy evidence. Retain the text and provenance, the online-purchase scope, actual
receipt basis, calendar-day deadline, packaging/use/accessory/manual conditions,
and applicable exclusions from section 4.4. Distinguish core conditions from a
complete eligibility determination. A product having been used does not by itself
establish signs of use; original packaging does not imply sealed packaging.

Do not add return labels, addresses, notification features or return-initiation
capabilities absent from the sources and tools. Preparation cannot help a turn
that never retrieves the relevant policy; tool-choice failures remain separate.

## Planned simulation and presentation semantics

Treat successful catalog/order lookups as authoritative current results inside
the fictional simulation. Explain the simulation once in the demo interface or
startup message and document it in the README. Give the model the same internal
context, replacing repeated snapshot explanations in prompts/tool guidance.

Remove automatic per-answer inventory/order snapshot footers and the repeated
promotion-snapshot footer. Preserve meaningful limits: an estimated delivery date
is not actual receipt, an order status does not supply a missing receipt timestamp,
and missing promotion validity dates must not be invented. The local simulation
does not imply an actual external carrier request. Keep customer isolation,
historical totals, fresh operational lookups, and partial-list indicators.

## Related partial errors to address

- Product-name drift: use returned product IDs for detail follow-ups.
- Invented budgets: alternative searches should derive the category and remain
  broad unless the customer provided a budget.
- Invented sound/comfort/suitability: limit claims to supported catalog attributes;
  consider rendering verified fields directly if the behavior persists.
- Incorrect discount explanations: derive the explanation from the same pricing
  fields used for the final amount.
- Extra successful lookups and repetitive text: measure efficiency/presentation
  separately from incorrect facts, missed required lookups and customer isolation.

These are planned tool/output changes, not transformations that embeddings alone
can enforce. The current model instruction already prohibits several of these
behaviors; repeating that instruction is not a verified solution.

## Implementation and validation sequence

1. Implement deterministic preparation for canonical hours, freight and return
   evidence; keep original bytes and internal provenance.
2. Regenerate the corpus, fingerprints and embedding index together. Do not
   hand-edit generated corpus JSON or reuse an index built for older chunks.
3. Align tools, prompt and presentation with the simulation contract and effective
   policy evidence; remove superseded notices and duplicated rules.
4. Verify holidays, all three special dates, freight boundaries and area scope,
   return deadlines/conditions/exclusions, pricing, and customer scoping.
5. Freeze new evaluation expectations before a live experiment. Assess answer
   faithfulness, necessary tool use, efficiency and presentation separately.
   Preserve historical captures and their original criteria.

The existing experiments demonstrate the failures motivating this plan. They do
not establish that the planned canonical preparation or presentation changes work.
