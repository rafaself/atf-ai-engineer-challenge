# Minimal follow-up remediation and evaluation

The retained change guarantees an inventory-snapshot disclosure for current,
nonempty product results marked `inventory_basis=imported_snapshot`. It follows
the existing metadata-based order-notice pattern: no intent parsing, semantic
regex, retry or tool routing. Old-run, empty and unrelated metadata do not trigger
it; repeated results and an already-present notice do not duplicate it.

The persona also uses neutral examples for paginated and page-less source
references instead of a shipping-specific PDF citation example. This is source
clarity, **not a proven repair for model attribution**. Retrieval, pricing,
customer scoping, tool signatures, model settings and execution limits are unchanged.

## Tested hypotheses and decisions

The user approved implementation experiments and a total **US$1** inference budget.
The [protocol](protocol.md) fixed six conversations/twelve turns from the preceding
[post-#43 baseline](https://github.com/rafaself/atf-ai-engineer-challenge/pull/73).
All prompts and fictional customer selections were reused. No historical capture
was rewritten. The same production ASGI service, repositories, Qwen and cached
local E5 retrieval were used; each conversation started fresh.

1. Candidate `8cbf8db` implemented the purpose-led policy-tool description,
   broader capability paragraph, neutral citation examples and deterministic
   inventory notice. Its [first capture](qwen-after.json) retained policy follow-up
   misses, an unsupported future-stock offer and a new false Christmas-closure
   statement. The broader wording did not establish the intended improvement.
2. Restore the original policy-tool description and capability paragraph rather
   than layering on more instructions. Retain the notice and neutral examples.
   The [final capture](qwen-final.json) evaluates that reduced source at `3417a1e`.
   This second batch is a changed-source experiment, not an automatic repeat of
   the same failed answers. It does not prove the restored text caused a recovery.

No further inference is planned. Retaining extra unproven instructions or spending
up to the budget ceiling would not establish reliability. The candidate commit,
protocol and both raw captures remain available for review.

## Source-based results

Manual review by the root coding agent checks actual current tool calls, arguments,
returned evidence and final prose; it is not independent human review. HTTP 200
alone is not a behavioral pass. Verdicts use the criteria fixed in the protocol.

| Conversation | Before | Candidate | Final | Final evidence / limitation |
| --- | --- | --- | --- | --- |
| Unavailable stock and alternative | Partial | Partial | Pass | Fresh named lookup reports active/zero-stock as unavailable; alternative search returns supported products, no future-restock promise. Both product turns carry the snapshot notice. The deterministic notice is guaranteed; disappearance of the promise in one sample is not. |
| Promotion / PIX | Pass | Partial | Pass | Literal Ohana name is looked up with PIX; R$439.20 and non-stacking match pricing. Candidate incorrectly said PIX was already included in the promotion despite correct arithmetic; preserve that semantic defect. Final correctly states promotion precedence. |
| Selected order detail | Pass | Pass | Pass | Fresh `get_my_order(4)`, correct Giannini item, quantity, total and tracking, with receipt/estimate caveats. Passing control preserved. |
| Mixed order / online return | Fail | Partial | Partial | Initial turn calls order and policy tools. Final follow-up now calls policy search and does not invent contacts or scheduling. It still opens with approval, inadequately resolves item condition/exclusions and omits online-channel scope in the initial explanation. Do not classify this as solved eligibility reasoning. Candidate instead called only the order tool on the policy follow-up. |
| Hours / holiday / product switch | Partial | Fail | Fail | Initial hours lookup and product switch are supported. Holiday follow-up still skips fresh policy retrieval and says Christmas is closed, contradicting the source's possible extended Christmas hours; final answer also repeats the extension condition inconsistently. This is a semantic regression relative to the baseline; removing the unproven description change did not eliminate it. |
| Exact freight threshold | Partial | Pass | Partial | Correct regional inclusive value and clarification evidence are returned throughout. Candidate explicitly cites the separate clarification; final again attributes equality only to the PDF. The automatic consulted-source list is correct but does not establish claim-level support. Neutral examples alone are not a reliable fix. |

Final: **3 pass, 2 partial, 1 fail**, versus baseline **2 pass, 3 partial, 1 fail**.
That count is descriptive; changed failure categories, single samples and provider
variation prevent a claim of general accuracy improvement. Policy freshness,
eligibility and source attribution remain known limitations for US-23 (#70).
No classifier, additional model, output gate or orchestration was added to hide them.

## Holiday follow-up: retrieval reuse versus interpretation

A subsequent review distinguishes tool-call compliance from factual quality. The
customer first asked “Qual é o horário normal de funcionamento da loja?” and then
“E nos feriados e no Natal, há atendimento?”. These are related questions, so
reusing already available information is a plausible retrieval decision. A new
lookup for every named holiday is not inherently necessary when the relevant rule
and qualification are already available. The current persona nevertheless requires
fresh tools for each factual turn; skipping the call violates that instruction.
That compliance criterion alone does not prove the answer is factually wrong.

The hypothesis that general hours and Christmas rules were split across chunks
is **not supported in this case**. The first lookup returned one record,
`policy-v2.1-s2`, source `store_policies.pdf`, section 2, physical page 2. Its text
contained both:

> Dia: Domingo e Feriados | Horário: Fechado

> Em datas especiais (Black Friday, Aniversário da Loja, Natal), o horário pode ser estendido. Alterações serão comunicadas com antecedência nas redes sociais e no atendimento via WhatsApp.

Qwen's initial answer correctly repeated both statements. For the next turn,
`agent/factory.py` reconstructs conversational user/assistant text, not old tool
returns. Thus the original source record was not replayed as a tool result, but
its relevant contents remained available in the previous assistant answer. The
follow-up even repeated the possible Christmas extension after opening:

> A loja **não tem atendimento nos feriados e no Natal**, pois está fechada nesses dias.

This is the substantive failure: unsupported categorical Christmas closure plus
an inconsistent qualification in the same answer. The source describes general
holiday closure and possible special hours; it does not supply a confirmed
Christmas schedule for a particular date. A faithful response could present both
conditions and leave the specific schedule unconfirmed, without another retrieval
of the same record.

“Christmas is a holiday, therefore the general closure applies” is a plausible
explanation for the observed generalization, **not an observed internal reasoning
trace**. These captures do not establish why Qwen chose not to search. The case
supports an evidence-interpretation/qualification failure; it does not demonstrate
missing retrieval coverage, a chunk-boundary defect, or that another identical
search would have prevented the error. No rechunking, holiday-specific queries,
mandatory routing or new inference is justified by this observation alone.

The original fixed protocol, captures and verdicts remain unchanged. The final
hours case remains Fail because of its unsupported/contradictory answer. For the
final report, score these dimensions separately: retrieval sufficiency, tool-use
instruction compliance, and answer faithfulness. Do not equate a redundant lookup
with better grounding, or an omitted lookup with a hallucination by itself.

## Offline checks

New notice regressions failed before implementation (3 failed / 6 passed) and
passed afterward (9 passed). The first full suite then exposed six exact-answer
integration expectations that omitted the newly required notice. Those assertions
were updated to explicitly require it while retaining the original price, stock,
partial-result, history and promotion checks; they were not relaxed to pass prefixes.

Final reduced implementation: **356 tests passed in 9.68s**, Ruff lint/format
passed and strict mypy passed across 91 files. Commands from repository root:

```sh
uv run --directory apps/backend --locked pytest
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests scripts
```

The offline suite ran outside the restricted sandbox because its asyncio model
integration tests otherwise stall. No offline tests make live provider calls.
The existing source-byte, pricing, isolation, corpus/index and execution-limit
regressions remain intact. Only evidence files changed after final validation.

## Budget, usage and reproducibility

[summary.json](summary.json) reconciles the two raw captures. The caller is reused
from PR #73 exactly as described in [protocol.md](protocol.md), with its stricter
US$0.50 per-batch guard. Two full worst-case reservations total **US$0.649728**,
within this goal's US$1 approval. Earlier baseline spend belonged to its separate
approval and is excluded from this goal.

| Batch | Provider responses | Input / output tokens | Estimated USD | HTTP median / max seconds |
| --- | ---: | ---: | ---: | ---: |
| Candidate | 24 | 83,362 / 2,166 | 0.0138039 | 2.2195 / 5.460 |
| Final reduced source | 24 | 83,477 / 1,956 | 0.01369515 | 1.9135 / 3.420 |

Total estimated spend: **US$0.02749905** using the same-day verified manifest's
US$0.15/M input and US$0.60/M output assumptions, not an invoice. Both batches
completed 12/12 HTTP turns. Each capture also contains seven zero-token synthetic
history response objects; they are not additional provider calls. Usage counts
must distinguish those from the 48 recorded Bedrock responses across the goal.

Latencies exclude setup and the warmed E5 preflight and do not prove a performance
improvement. No downloads, paid embeddings, new model matrix or automatic retries
were performed. Both captures include the source commit and source-file hash.
Future paid repetitions require separate approval; the remaining budget is not an
instruction to keep tuning until the sample passes.
