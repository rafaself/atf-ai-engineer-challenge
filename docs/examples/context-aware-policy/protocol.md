# Context reuse and conditional reasoning — fixed evaluation

Owner separately approved Qwen3 32B inference up to US$0.75 on 2026-11-02.
Previous budget approvals do not apply. No further inference beyond this sample
is planned. Use the same model/limits/repositories/retrieval and US-18 recorder.

Four instruction variants are frozen in variants.json: unchanged baseline,
context-only, conditional-only and combined. Only persona text varies; production
reads its single STORE_INSTRUCTIONS as before. The evaluation caller substitutes
that instruction constant before constructing each fresh agent, solely for this
controlled comparison. It does not change tools, history or returned evidence.
No extra production prompt loader is introduced.

Two fresh guest conversations per variant, in the same order:

1. Exact baseline hours sequence from ../grounding-followups/qwen-final.json:
   - Qual é o horário normal de funcionamento da loja?
   - E nos feriados e no Natal, há atendimento?
   - O Takamine GD20 está disponível? Qual é o preço e o estoque?
2. Missing policy evidence after an operational question:
   - O Takamine GD20 está disponível? Qual é o preço e o estoque?
   - E qual é o prazo de arrependimento para uma compra online?

The first hours retrieval must deliver section2 containing both normal closure
and possible special hours. On its follow-up, context is sufficient if the first
answer preserved both: reuse is appropriate and a repeated identical retrieval is
unnecessary. If earlier evidence/answer is insufficient, a new search is appropriate;
do not penalize justified retrieval solely to minimize call counts. The topic
switch and first product question require fresh operational lookup. The return
follow-up has no earlier policy evidence, so it requires policy retrieval.

Score tool-use appropriateness separately from answer faithfulness. Note where
old baseline/conditional-only fresh-turn instructions differ from the requested
context-aware behavior. Holiday faithfulness requires normal closure, possible
special Christmas hours, and no definitive Christmas opening/closure without a
confirmed schedule. Return answers must ground the online/receipt interval and
conditions; product answers must match current tool values. History interpretations
must not override source qualifications. No actual Christmas business rule is added.

Reserve all 20 potential turns up front, each at the existing worst-case allowance
of US$0.027072: total US$0.541440, below the newly approved US$0.75. No provider calls
before that check. Stop a failed conversation without retry; retain partial/error
records. Existing application limits/retries remain unchanged. Record usage/cost,
actual calls, sources, answers and warm HTTP latency. Policy E5 is preflighted once
on each variant's search instance, consistent with the prior sample.

Use the preserved old capture as historical comparison and the freshly repeated
baseline as a same-session control. One sample per cell cannot establish causality
or reliability. Evaluate each change independently and its combination; retain or
revert based on the evidence with uncertainty stated. Do not alter old verdicts.
