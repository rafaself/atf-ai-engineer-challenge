# Qwen3 32B policy-uncertainty prompt check

## Scope and run

This run tested the added `Interpretação de políticas, exceções e incertezas`
section in the production `STORE_INSTRUCTIONS` against the current nine-scenario
fixture. It used Qwen3 32B through the existing `/api/chat` harness: 16 chat
turns, 39 Bedrock requests, no HTTP errors, and no missing usage records. The
estimated inference spend was US$0.01996725 under the separately approved
US$0.50 cap; this is an estimate, not invoice data. Median and maximum
end-to-end latency were 1.709 and 10.012 seconds.

| Qwen run | Provider requests | Input / output tokens | Estimated spend | Median / max latency |
| --- | ---: | ---: | ---: | ---: |
| Existing baseline | 39 | 108,798 / 2,716 | US$0.01794930 | 2.038 / 6.079 s |
| Added policy section | 39 | 123,083 / 2,508 | US$0.01996725 | 1.709 / 10.012 s |

Latency is end-to-end `/api/chat` time, including local retrieval and tool
execution. The runs are single samples; differences do not establish causation.

The local E5 policy index was ready and returned the holiday record. AWS denied
the unmetered `GetFoundationModelAvailability` preflight; the approved live run
then used its metered Qwen request as the runtime check. The earlier
network-restricted preflight capture recorded zero paid calls. Both captures
are preserved below; the earlier two-model baseline was not modified.

## Findings

| Dimension | Observation |
| --- | --- |
| Holiday tool choice | Correct. Qwen searched the policy once for the first question and reused that evidence in the follow-up. It did not issue a redundant search. |
| Holiday answer faithfulness | Failed. The follow-up says there is no service on holidays and Natal, then mentions possible extended hours but omits Natal from the exception. The retrieved section explicitly names Natal as a special date whose hours may be extended. The answer should preserve the normal closure and say the specific Christmas schedule is unconfirmed. |
| Operational topic switch | Correct. Qwen called `get_product_details` for Takamine GD20 and returned the catalog's R$ 2,199.00 price and stock of 5 with the snapshot notice. |
| Missing return-policy evidence | Qwen called order and policy tools in the initial mixed question, then reused that evidence in the follow-up. It listed packaging, use, accessories, and manuals, but still opened with “Sim, você pode devolver” before those conditions were confirmed. Partial. |
| Other observed issues | The zero-stock answer still offers to check a future availability forecast that no tool provides. The exact-threshold freight answer gives the approved free-shipping outcome but attributes equality to the original PDF, while the approved clarification is a separate source. |

Manual review by the run author, not an independent evaluator, gives the same
overall Qwen result as the previous current-harness run: **5 pass, 3 partial,
1 fail**, with the same one critical holiday error. The return follow-up now
names all listed product conditions, but still asserts eligibility before
confirming them. That is one sample and does not establish that the prompt
caused an improvement.

The holiday tool sequence and answer failure match the baseline pattern: policy
retrieval is appropriate, but the model turns the general holiday closure into a
definitive Christmas closure despite the named exception. The added section
therefore did not fix the target failure. This single run also cannot establish
that it improves policy reasoning more generally.

## Recommendation

Do not treat or retain this longer section as a verified fix for the holiday
failure. If the change is intended only to solve that failure, revert it: the
critical result and overall scenario score were unchanged, while the run used
14,285 more input tokens and about US$0.0020 more estimated inference spend than
the prior Qwen run. The improved detail in the return answer is inconclusive
because it is one sample and the answer still begins with an unsupported
definitive “yes”.

## Validation and artifacts

- Policy corpus and retrieval tests: 24 passed.
- Ruff check and format: passed for the changed persona file.
- Strict mypy: passed across 95 source files.
- Agent `FunctionModel` tests did not complete locally: a minimal injected
  function model also remained waiting for its first response and was stopped.
  No passing result is claimed for those tests.
- Earlier baseline: [current Qwen and Nova Lite report](current-harness-qwen-nova-lite-2026-11-02.md)
- Baseline capture: [Qwen and Nova Lite raw capture](capture-context-updated-2026-11-02.json)
- Candidate capture: [Qwen prompt-change raw capture](capture-qwen-policy-uncertainty-2026-11-02-retry.json)
- No-call sandbox preflight: [blocked preflight capture](capture-qwen-policy-uncertainty-2026-11-02.json)
- Scenario fixture: [current nine-scenario fixture](scenarios-current-v3.json)

## Follow-up: overlapping-scope rule

After the run above, the longer example block was replaced by a concise generic
instruction stating that a specific qualification may overlap with a general
category. Qwen received this wording in its system instructions during a new
run of the same fixture. That run completed 16 turns and 39 provider requests,
with estimated spend US$0.01822410 under a fresh US$0.50 cap. It used 110,970
input and 2,631 output tokens; median and maximum end-to-end latency were 2.146
and 5.205 seconds. There were no HTTP errors or missing usage records.

The answer still failed the holiday case. It said the store was closed on
holidays and Natal, then listed only Black Friday and the store anniversary as
dates whose hours might be extended. The retrieved section in that same run
explicitly named Natal in the possible-extension clause. Qwen searched the
policy for the first question, reused the evidence for the follow-up, and made
the expected fresh product lookup after the topic change. Retrieval and tool
choice remained correct; answer faithfulness did not.

This confirms that the concise overlap instruction also did not solve this
sample. The same run contained a mixed-language insertion (`收到了`) in the
return follow-up, another observed output defect. A single conversation cannot
attribute that defect to the prompt change or establish a general regression.

- Revised candidate capture: [Qwen overlapping-scope rule run](capture-qwen-overlapping-policy-scopes-2026-11-02.json)

## Follow-up: explicit answer structure

The current persona instruction asks the agent to state the general rule, the
source's qualification for the specific case, and whether that outcome is
confirmed. Qwen received this instruction in a final run of the same fixture:
16 turns, 37 provider requests, no HTTP errors or missing usage, and estimated
spend US$0.01713090 under a fresh US$0.50 cap. The run used 103,414 input and
2,698 output tokens; median and maximum end-to-end latency were 1.494 and 5.249
seconds.

The holiday answer still failed. It said the store has no service on holidays
and Natal, then mentioned possible extensions only for Black Friday and the
store anniversary. The section 2 record returned by RAG names Natal in the
possible-extension clause. The tool sequence was appropriate: one policy
search, no redundant policy call on the follow-up, and a fresh product lookup
after the topic changed. Retrieval and tool choice were correct for this
scenario; faithfulness was not.

Manual review of all nine scenarios found **5 pass, 2 partial, 2 fail**. In
addition to the holiday error, the order-details follow-up skipped
`get_my_order`, substituted a Yamaha FG800 for the imported Giannini GF-3D, and
claimed there was no tracking code despite the returned fixture data. A
separate product-detail follow-up also answered price and stock without the
required fresh lookup. These are observations from one sample and are not
attributed to the prompt revision.

The earlier answer beginning “A loja Empório da Música está fechada nos
feriados e no Natal” was from the pre-experiment baseline. The later prompt
variants changed the wording but retained the same categorical Christmas
conclusion. The evidence shows that the added guidance has not fixed this
failure. Do not claim a reliability improvement from these runs.

- Final candidate capture: [Qwen explicit-answer-structure run](capture-qwen-policy-answer-structure-2026-11-02.json)

## Follow-up: named-case prompt and rationale probe

The persona was then tested with a concise instruction to repeat the exact
source-named case and its qualification. A fourth conversational turn asked
Qwen to briefly summarize the policy information behind its answer. This was an
evidence-summary request, not a request for private chain-of-thought. The
focused sequence used the existing `/api/chat` application, local policy index,
and product tool: four chat turns, six provider requests, no HTTP errors, and
estimated spend US$0.00350070 under a fresh US$0.15 cap. The maximum reservation
was US$0.108288.

The first answer was accurate and said Natal hours may be extended. The holiday
follow-up still stated categorically that the store is closed on Natal. The
post-answer summary then claimed that section 2 “indica claramente que a loja
está fechada nos feriados e no Natal,” which the retrieved record does not say;
it again omitted the record's Natal qualification. The rationale is a
generated self-report, not access to the model's private reasoning. It was
useful here because it reproduced the same source misreading, not because it
explained the model's internal process.

Tool use was appropriate: policy retrieval ran on the first turn, the evidence
summary reused the existing context without a redundant search, and the
Takamine topic switch triggered a fresh product lookup with the expected price
and stock. This isolates the remaining holiday defect to answer interpretation
and faithful reporting of the evidence.

The named-case prompt instruction was reverted after this run because it did
not fix the target failure. The prior concise persona wording is restored; the
focused fixture, runner and capture remain as evaluation evidence.

- Focused fixture: [Natal rationale scenario](scenarios-qwen-natal-reasoning-v1.json)
- Focused runner: [Qwen rationale evaluation script](../../../apps/backend/scripts/evaluate_qwen_natal_reasoning.py)
- Focused capture: [Qwen answer and rationale](capture-qwen-natal-reasoning-2026-11-02.json)
