# Scoped policy and harness review — 2026-11-03

## Result

The run used the same 12 conversations and 20 HTTP turns for Qwen3 32B and
GPT-OSS 120B. Both completed all turns with HTTP 200 and no missing usage. The
earlier 8/1/0 comparison had nine conversations; on those same prompts, this run
scored Qwen 7/0/2 and GPT-OSS 6/3/0. Three added holdouts scored Qwen 2/0/1 and
GPT-OSS 1/1/1, yielding the final totals below. Manual review found continued
answer-quality failures despite successful execution:

| Model | Pass / partial / fail | High-severity errors | Missed required tool calls | Provider attempts / responses | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 9 / 0 / 3 | 4 | 2 | 39 / 39 | US$0.02074680 |
| GPT-OSS 120B | 7 / 4 / 1 | 4 | 1 | 42 / 42 | US$0.01841145 |

I scored GPT-OSS’s demo-customer-selection turn as Pass, consistent with its prior capture: both answers ask the user to identify the fictional customer and neither reveals an order.

Both models followed the explicit payment argument and product-name/code tools in
most catalog turns. The remaining catalog failure was a model-selected wrong
product ID: Qwen treated “second item” as product ID 2, then said product 121 was
unavailable for PIX. The API cannot infer which prior list item the model meant
when it submits a valid but incorrect ID.

Scoped policy retrieval returned only sections 4.1/4.4 for online returns and
4.3/4.4 for preference exchanges. The eight-day Qwen holdout applied the correct
seven-day limit. The final mixed Qwen follow-up returned an unrelated hotel claim.
Qwen and GPT both invented SAC emails and return-label procedures in the used-item
follow-up. Scoped source excerpts and prompt wording did not prevent that behavior.
Some initial eligibility answers added unsupported “perfect condition” or
proof-of-purchase conditions. These are semantic failures, separate from HTTP
reliability.

## What changed

- Policy preparation is versioned `poppler-scoped-policies-v7`. It identifies
  applicability, refund method/deadline, freight payer, exclusions and documented
  next steps; the steps are empty because the supplied rule gives none. The
  prepared corpus and freeze were rebuilt without modifying the source PDF, CSVs,
  or freight approval. Named scopes select prepared sections directly.
- The policy tool requires an explicit scope. Instructions require a fresh policy
  read after new eligibility facts. Assistant prose is not presented as current
  source evidence. This remains an instruction to the model; free-form answers can
  bypass it, as the evaluation demonstrates.
- Named product lookup and ID detail lookup are separate tools. Every catalog read,
  including alternatives, requires `payment_method`. The application still cannot
  tell that a model confused an ordinal with a valid but unrelated ID.
- The recorder counts current-run model responses, not synthetic assistant history,
  and reports provider attempts separately. The historical erratum reports 77→61,
  80→64, 82→66 and 111→90 evaluation attempts where counters reconcile. Zero-usage
  synthetic history did not change token totals or estimated costs. Original capture
  bytes and verdicts are unchanged; SHA-256 checks pass.
- The frozen v7 review criteria treat invented contacts, operational capabilities,
  eligibility conditions and authoritative prices/availability as high severity.
  Tool use, answer quality, efficiency and presentation remain distinct fields.

## Rejected return-output experiment

A structured output function was tested in four successive paired runs, followed
by a four-conversation focused holdout. The models repeatedly omitted evidence,
used unsupported schema keys, reused stale order IDs, or copied example facts. The
correction path produced HTTP 500s and repeated questions. When unsupported facts
were discarded safely, Qwen sometimes ignored facts the customer had just given.
The focused holdout exposed further schema errors and a GPT-OSS HTTP 500. These
captures are retained; their scores are not combined with v7 because the fixtures
and runtime differ.

The function is removed from the delivered runtime. The rejected code excerpt is
preserved in [the experiment patch](rejected-return-output-2026-11-03.patch), and
all trial captures are linked from the [comparison index](README.md). No
prompt-only claim is made that invented return contacts have been solved. A
reliable deterministic return workflow needs a simpler input contract with
application-owned fact collection and responses; this experiment did not produce
one that both models could use reliably.

## Accounting and spend

The v7 capture records 81 provider attempts and 81 current model responses over 40
HTTP turns. The paired run cost US$0.03915825. Including the five scoped-return
trial captures, this goal used US$0.21641670. With the US$0.08283015 spent on the
preceding approved experiments, cumulative spend is US$0.29924685 of the approved
US$1.00. No call exceeded the per-run cap.

- [Final capture](capture-scoped-harness-v7-2026-11-03.json)
- [Frozen 12-scenario fixture](scenarios-current-v7.json)
- [Read-only accounting erratum](accounting-erratum-2026-11-03.md)
- [Earlier scoped-output captures](capture-scoped-return-qwen32-gptoss120-2026-11-03.json), [v2](capture-scoped-return-v2-qwen32-gptoss120-2026-11-03.json), [v3](capture-scoped-return-final-qwen32-gptoss120-2026-11-03.json), [v4](capture-scoped-return-settled-qwen32-gptoss120-2026-11-03.json), and [focused v6](capture-return-focused-v6-2026-11-03.json)

The system instructions and manual severity criteria also changed from the prior
run, so the score shift does not establish that GPT-OSS became less capable. On
the shared nine scenarios, the concrete new problems were an unsupported item
unit price and return-initiation offer, plus a less cautious Natal conclusion;
the older and current customer-selection answers are substantively the same.
These remain single-pass samples, not a reliability estimate. The zero-HTTP v7
result shows that the harness completed the workload; manual review shows that
grounded customer answers remain unresolved.
