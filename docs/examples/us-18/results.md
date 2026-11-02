# US-18 live functional review

Run date: 2026-11-01. The owner explicitly approved the prepared four-scenario
Bedrock Qwen3 32B run in `us-east-1`, capped at US$0.25. This is a functional RAG
check, not a RAG versus Full Context comparison or a retrieval optimization study.

All four requests returned HTTP 200. Source-based review passes three cases and
fails the mixed case on remaining semantic/disclosure defects. HTTP success and
valid citation provenance do not establish answer faithfulness.

## Preserved evidence and method

[live-captures.json](live-captures.json) contains the actual final responses,
ordered model/tool messages, retry feedback, returned source records, usage and
elapsed HTTP times. Transient SDK/session identifiers are removed. Prompts are
unchanged from [US-17](../us-17/protocol.md); sessions are fresh, with fictional
customer 1 selected only for the mixed case. The other three cases are guests.

Same production HTTP application, operational tool definitions, customer-scoped
SQLite repositories, cached pinned E5/Chroma retrieval and current output validator.
Qwen3 32B, temperature 0, 1,024 output tokens per request, five model requests and
five tool calls per case, single output retry. No automatic experiment reruns.
Review was performed by Codex against the frozen rubric and source, not an
independent human or LLM-as-judge evaluation. One sample per case is descriptive.

| Case | Outcome | Actual calls and source-based assessment |
| --- | --- | --- |
| hours | Pass | One policy lookup returned section 2 plus 7.3 and 7.1. The answer explicitly closes holiday WhatsApp service, distinguishes possible Christmas extensions and prior announcements, and cites section 2, p. 2. |
| return | Pass | Policy lookup returned 4, 4.1, 4.2, 4.4 and warranty sections. The answer cites 4.1, p. 4, states the seven-day receipt condition and packaging/accessory requirements, and asks about signs of use and completeness rather than categorically rejecting a reported use. |
| money-unknown | Pass | Two policy calls retrieved shipping and warranty evidence. The answer explicitly leaves the exact R$500 outcome unspecified, does not apply the fixed fee, and describes the instrument-loan service as unspecified in the consulted evidence. The shipping citation points to current section 5.1, p. 4. The formerly failing scenario now returned an answer, but that does not retrospectively establish the historical HTTP 500's cause. |
| mixed-order-return | Fail overall; tool-selection and citation provenance pass | Calls `get_my_order(order_id=4)`, initially promises a policy lookup without doing it, receives validator feedback, then calls policy search and cites current section 4.1, p. 4. It still opens “O pedido 4 foi entregue, conforme o prazo estimado de 22/12/2025”, omits the imported-snapshot disclosure, and asks only about condition without explicitly resolving purchase channel and actual receipt date. Those gaps prevent a functional pass despite the corrected two-tool path. |

The mixed answer does not invent a new current date or repeat the old categorical
expiry denial, but its delivery-date framing remains misleading. Do not count the
whole mixed case as passed merely because both tools were used.

## Usage and accounting

| Case | Requests | Input/output tokens | HTTP seconds | Estimated US$ |
| --- | ---: | ---: | ---: | ---: |
| hours | 2 | 7,440 / 126 | 15.240 | 0.0015888 |
| mixed-order-return | 4 | 15,766 / 503 | 3.886 | 0.0035556 |
| money-unknown | 2 | 8,245 / 240 | 2.460 | 0.0018410 |
| return | 3 | 12,700 / 347 | 2.820 | 0.0028176 |

Total: 11 model requests, 44,151 input tokens, 1,216 output tokens; estimated
US$0.0098030 using the documented historical US$0.20/M input and US$0.80/M output
assumptions. This is not an invoice or a claim about current pricing. Conservative
full-budget accounting reserves US$0.147456 for all four cases, below US$0.25.
HTTP times include retrieval, model interaction and validation; the first request
also includes cold E5 initialization. They cannot establish a general latency or
cost advantage, and there is no new matched Full Context arm.

Before model execution, automatic review initially rejected the egress request;
verified fictional-fixture provenance in `data/README.md` resolved that rejection.
Local setup then found a missing operational database and an incompatible old
generated catalog. The old catalog was preserved as the ignored
`data/catalog.pre-us18.sqlite3`, and the README preparation command rebuilt the
local snapshots from unchanged source bytes. An additional launch refused the
existing empty output path before agent setup. These setup attempts made zero
provider requests; see [setup-failure.json](setup-failure.json). No failed live
attempts were discarded or silently retried.

## Correction after this batch

The failed mixed response is now a failing-before-fix offline trace regression.
It demonstrates that current-run provenance and both tools alone were insufficient.
The output validator now requires an explicit imported-snapshot disclosure on
covered mixed order/return answers backed by an actual order snapshot. Missing
disclosure receives the existing bounded correction opportunity; it cannot finish
as a successful response if left uncorrected.

Order-tool guidance now explicitly distinguishes the estimated date from receipt,
and both order and section-4.1 policy guidance request purchase channel, actual
receipt date and condition before determining eligibility. This strengthens the
information at the evidence boundary without changing source rules or retrieval.
The snapshot marker check is not a semantic correctness proof; the revised model
behavior still needs a focused live rerun. No additional provider calls have been made.

After this correction: 329 offline tests passed in 8.76 seconds; Ruff lint/format,
strict mypy across 89 files, source distribution/wheel build and whitespace checks
passed. All seven supplied source checksums match; frozen evaluation and US-17
captures remain unchanged. The new trace regression failed before the snapshot
disclosure check and passes afterward. These checks do not establish post-correction
model reasoning.

The owner subsequently approved the following single-case rerun, executed once:

```bash
export HF_HOME="$PWD/data/benchmark-cache/hf"
export HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
uv run --env-file .env --project apps/backend --locked --extra policy-rag \
  python apps/backend/scripts/validate_us18.py --live --case mixed-order-return \
  --max-cost-usd 0.05 --output docs/examples/us-18/mixed-followup.json
```

Same model, region, frozen prompt, fictional customer and per-case limits; maximum
reservation US$0.036864 under the separately approved US$0.05 ceiling. Both the
first batch and this follow-up are preserved unchanged.

## Focused follow-up: partial, with a query-contract failure

[mixed-followup.json](mixed-followup.json) returned HTTP 200 in 16.604 seconds,
including cold E5 loading. Four model requests used 15,857 input and 427 output
tokens, estimated US$0.0035130 under the same historical accounting assumptions.
Cumulative observed estimate is US$0.0133160, with US$0.184320 conservatively
reserved across the two separately approved batches.

The response now accurately describes delivered status as an imported snapshot,
explicitly states that actual receipt date and purchase channel are unavailable,
asks for those facts and product condition, and avoids a definitive eligibility
decision. It still does not satisfy the frozen rubric: the model searched for
`devolução de instrumentos` rather than the actual question. That query returned
sections 4, 4.4, 4.2 and 8.1–8.3, missing section 4.1. The final answer cited generic
section 4 and warranty section 8.1, omitted the applicable online-withdrawal rule,
and asked about an unused product as though that condition were established by
the returned evidence. This is a partial result, not a functional pass.

The exact original question already retrieved section 4.1 in the local preflight.
Investigation attributes the new miss to violation of the tool's existing query
contract: model-controlled paraphrasing discarded the customer question's context.
The correction makes `search_store_policies` a no-argument tool; the application
passes the exact current prompt from `RunContext`, excluding history, customer
identity and labels. The model still chooses whether to call the tool. No embedding,
ranking, filter, expansion, corpus or frozen benchmark changes were made. This is
an orchestration/input-contract fix for a confirmed functional failure, not deferred
retrieval optimization.

An offline regression failed before the initial correction because the schema exposed
a model-selected `query` argument. That earlier check covered the no-argument schema
and a standalone question; the separate context-dependent correction below adds a
two-turn HTTP regression for the latest prior user question. Existing callers still
use the no-argument tool schema. All **330 offline tests** passed at the initial
correction (7.00 seconds), and strict mypy passed across 89 files. Prior live passes
are historical observations at their recorded revision, not proof of final-revision
generation behavior. The context correction below has offline retrieval and HTTP
evidence; it has not had a live model check.

The owner approved that next single-case check, executed once with output
`docs/examples/us-18/mixed-current-question.json`, capped at US$0.05.

## Current-question check: safe failure before policy lookup

[mixed-current-question.json](mixed-current-question.json) returned sanitized HTTP
500 after three model responses in 3.240 seconds. It called only `get_my_order`.
The initial answer and the answer after correction both deferred policy lookup
until the customer supplied eligibility facts. Output validation rejected the
missing tool twice and exhausted the existing single correction opportunity.
Captured safe cause chain: `AgentExecutionError` → `UnexpectedModelBehavior` →
`ToolRetryError` → `ModelRetry`. Unlike the historical US-17 HTTP 500, this failure
has sufficient trace evidence to attribute it to output-retry exhaustion.

The new query contract was not exercised by this live attempt: do not claim a
successful policy lookup or a retrieval failure from it. The response was not
delivered as success, and the application preserved customer-safe error behavior.
Recorded usage is 10,976 input and 355 output tokens, estimated US$0.0024792 under
the same accounting assumptions. Across all six authorized scenario calls,
recorded usage-based estimates total US$0.0157952, and conservative reservations
total US$0.221184. The three separately authorized ceilings were US$0.25, US$0.05
and US$0.05; no additional provider calls have been made.

The previous combined output-correction message mixed unrelated price checks with
tool and eligibility instructions. Missing-tool errors now receive a focused
instruction identifying the missing tool and requiring its call **now**, without
waiting for customer clarification. The persona and order guidance make the
sequence explicit: retrieve the policy first, then explain the rule and ask the
missing customer facts. The agent's output-retry and request/tool budgets are
unchanged. Other output constraints are checked again after any tool use; this
does not authorize an unsupported answer.

The trace-based feedback regression failed before this correction and passes
afterward. All **331 offline tests** pass (8.71 seconds), strict mypy passes across
89 files, and lint, formatting, build and whitespace checks pass. This verifies
the correction payload and bounded failure path, not that Qwen will follow it.

The owner approved up to **two** focused
mixed-case runs, same model/region/prompt/customer and per-case limits, total
ceiling **US$0.10** (at most US$0.073728 reserved). Stop after the first source-based
functional pass; if it fails, inspect and correct the confirmed defect before
using the second run. Preserve separate outputs
`mixed-targeted-feedback-1.json` and, only if needed, `mixed-targeted-feedback-2.json`.
No broad benchmark, extra model, ranking optimization or Full Context comparison.
Both approved checks were used as documented below; no additional calls were made.

## Focused two-check batch: orchestration passes, answer quality remains partial

| Capture | HTTP; requests; input/output tokens | Seconds | Review |
| --- | --- | ---: | --- |
| [mixed-targeted-feedback-1.json](mixed-targeted-feedback-1.json) | 200; 3; 11,643 / 283 | 17.698 | Both tools run, the no-argument policy tool retrieves section 4.1 using the original question, snapshot and estimate semantics are correct, and all missing eligibility facts are requested. The answer states the seven-day online-withdrawal rule but imports “perfeito estado” from section 4.3 into the section-4.1 conditions. Partial, because that is a stronger source condition. |
| [mixed-targeted-feedback-2.json](mixed-targeted-feedback-2.json) | 200; 4; 16,965 / 352 | 15.046 | After adding source-specific guidance distinguishing “sem sinais de uso” from “sem uso” and section 4.3's “perfeito estado”, the answer asks about the correct condition and missing facts. Both tools run and section 4.1 is present, but the first candidate omits the rule and citation. Generic citation feedback produces a final policy citation attached to order facts without explaining the applicable seven-day rule. Partial, not a complete grounding pass. |

The first call required no output retry: the two-tool flow worked with the current
instructions and evidence guidance, but this alone does not isolate the effect of
the targeted retry text. The second call exposes a separate correction-message
defect: requesting a citation without explicitly requiring a supported policy
explanation can encourage a decorative reference. It cannot be counted as faithful
grounding merely because the section/page exists in current evidence.

The two checks used estimated US$0.0025550 and US$0.0036746 respectively, under the
same historical rate assumptions, with US$0.073728 conservatively reserved within
their US$0.10 approval. All eight scenario calls together have 25 recorded model
responses, 99,592 input tokens and 2,633 output tokens; usage-based estimate
US$0.0220248, conservative reservations US$0.294912 within separately approved
ceilings totaling US$0.45. These are not invoice prices or efficiency comparisons.

The output validator now gives a focused correction for missing/wrong citations
when current evidence exists: explain the supported rule, put the citation next
to that rule, and do not use policy citations for order status, estimates, products
or totals. For mixed requests it explicitly requires explaining the retrieved
online-withdrawal rule before asking missing customer facts. The section-4.1 tool
guidance reinforces that incomplete eligibility facts do not prevent explaining
the general rule. Citation provenance and monetary checks remain enforced; this
feedback is not a semantic entailment validator or a proof that the model follows it.

The captured citation-feedback regression failed before the correction and passes
afterward. **332 offline tests pass** (9.39 seconds), strict mypy passes across 89
files, and lint, formatting, source/wheel build and whitespace checks pass. Source,
corpus, rankings, labels and all previous captures are unchanged. No new live calls
have been made after the latest correction, so US-18 remains incomplete.

The owner approved a bounded Qwen follow-up; its trace and ensuing parser
correction are recorded below.

## Citation-format validation and Qwen trace replay

The Qwen follow-up in [mixed-rule-feedback-1.json](mixed-rule-feedback-1.json)
used four model responses (16,995 input / 544 output tokens) and 20.288 seconds.
The final generated answer followed both tool lookups, described the order as an
imported snapshot, said actual receipt was unknown, explained the seven-day
online withdrawal rule with section 4.1, p. 4, stated the source conditions and
refund handling, and asked for purchase channel, actual receipt date and product
condition. It still asked whether the instrument was in “perfeito estado,” which
is stronger wording than the source's “sem sinais de uso.” The application
returned HTTP 500 because the validator recognized only `[política ...]`, not the
equivalent `(seção 4.1, p. 4)` syntax the model used. This is a citation-format
validation defect: the current-run section/page provenance itself was present.

The citation parser now accepts both formats while requiring matching delimiters,
the current run, and an actually returned section/page. Regression cases verify
that parenthesized citations do not create their own provenance and that historical
or absent evidence remains invalid. This closes a deterministic parser gap; it
does not convert the failed HTTP capture into a successful response. The generated
answer is substantively close but retains the noted phrasing weakness; the trace
replay assessment appears below. Alternative-model evaluation is deferred, so the
available evidence supports no model-comparison claim. RAG vs Full Context,
retrieval optimization, and broader model benchmarking remain outside this
functional check.

The current validator was also replayed offline against the captured final Qwen
answer. Its parenthesized section 4.1 citation passes provenance against the
captured current-run policy return, but the answer's “perfeito estado” wording is
stronger than the manual's “sem sinais de uso.” The evidence-scoped guard rejects
that answer and requests a targeted correction. The regression then supplies a
corrected answer asking about visible signs of use, packaging, accessories and
manuals; it passes with the same current-run evidence. This demonstrates the
correction path, not a new HTTP success or an additional model call. Faithfulness
still requires reviewing the generated answer against the source.

## Restricted-sandbox stall

The owner approved one more live run of the frozen mixed order/return case with
Qwen 3 32B in `us-east-1`, fictional customer 1, at most five model requests and
tool calls, 1,024 output tokens per request, no experiment rerun, and a US$0.05
ceiling. Its reserved upper estimate was US$0.036864 using historical Qwen rates.
The first launch stopped before the script because uv's default cache was
read-only. The run was relaunched with `UV_CACHE_DIR` under `/tmp` inside the
restricted sandbox. The instrumented probe completed agent and HTTP-client setup,
then stalled after `http.request.started`; it emitted no application `http.request`
or `agent.started` event. The process was interrupted with SIGINT (exit code 130).
The preserved checkpoint is [mixed-final-qwen-sandbox-stall.json](mixed-final-qwen-sandbox-stall.json).

The checkpoint contains no response or usage. Because the route handler and agent
never started, the trace shows no Bedrock model invocation. A separate local fake-
service reproduction confirmed that the in-process ASGI request hangs inside the
restricted sandbox and returns HTTP 200 outside it. This identified the stall as a
sandbox thread-pool issue, not Qwen latency. The original interrupted attempt had
no provider model usage recorded.

## Stall investigation

A provider-free local retrieval check ran the same frozen mixed-case query with
`HF_HUB_OFFLINE=1`. Pinned E5 initialization plus the existing Chroma search took
14.473 seconds and returned `evidence_found` for sections 4.3, 4.1, 5.2 and 4.4.
This confirms the local retrieval path can complete in this environment; it cannot
show whether the interrupted run reached that stage.

A separate provider-free construction check built the same Qwen Bedrock model
adapter and SQLite tool adapters in 0.258 seconds without invoking Bedrock. This
rules out a reproducible multi-minute setup stall in the current environment.

The fake-service reproduction used the same `httpx.ASGITransport` and app route
without constructing a model. Inside the restricted sandbox it stalled before the
route's first `http.request` event. Outside the sandbox it returned HTTP 200 in
0.158 seconds and emitted `http.request`, `chat.started`, and `http.response`.
Combined with the Qwen run's phase trace, this localizes the stall to the sandbox's
in-process ASGI/thread-pool path before the route handler. The 60-second
`ChatService` timeout begins inside that handler; the 15-second Bedrock timeout
never applied because the agent did not start.

The probe now enables the existing safe phase logs automatically, writes a
checkpoint before agent setup and before each HTTP request, and prints flushed
phase events to stderr. It records a run as `in_progress` before waiting for the
response. On cancellation or failure, it checkpoints the safe exception summary
and any messages/usage retained by `RecordingAgent`, then re-raises so the command
still exits unsuccessfully. A regression verifies that cancellation preserves the
partial trace without exposing the exception message. No provider call was made
while validating this change.

After the initial probe update, **343 offline tests passed** in 11.75 seconds. Ruff
lint and format checks passed, strict mypy passed across 89 files, and
`git diff --check` passed. The later out-of-sandbox Qwen run is reported below.

## Qwen run outside the sandbox

The authorized mixed case then ran outside the restricted sandbox using the
instrumented probe. It completed in 17.115 seconds with HTTP 500 after four model
requests, using 16,942 input and 394 output tokens. The historical-rate estimate is
US$0.0037036; the conservative reservation was US$0.036864 under the US$0.05
ceiling. The full sanitized trace is [mixed-final-qwen.json](mixed-final-qwen.json).

Both `get_my_order` and `search_store_policies` ran, and the policy result included
current section 4.1, page 4. The first answer lacked the applicable rule/citation.
After feedback, Qwen gave the seven-day online-withdrawal rule with a current
citation, asked for purchase channel, actual receipt date and product condition,
and correctly used “sem sinais visíveis de uso.” It still said the order was
listed as delivered in the database without explicitly calling it an imported
snapshot. The validator rejected that final disclosure gap after its one allowed
output retry, so the API returned 500 safely.

The validator's retry now gives an exact, model-neutral sentence for the snapshot
disclosure. A regression replays this actual Qwen answer, verifies the targeted
retry, and accepts a corrected answer with current-run evidence. No live call has
been made after this correction; the live mixed case remains partial until a later
authorized check.

After this correction, **344 offline tests passed** in 10.09 seconds. Ruff lint
and format checks passed, strict mypy passed across 89 files, the source distribution
and wheel built, and `git diff --check` passed. No additional provider call was made.

## Follow-up implementation after the last Qwen capture

The recorded final answer in [mixed-final-qwen.json](mixed-final-qwen.json) used
both tools, retrieved section 4.1, cited it, preserved the imported “delivered”
status without inferring an actual receipt date, and asked for the missing eligibility
facts. Its HTTP 500 came from the output validator requiring a specific snapshot
phrase. That phrase requirement is removed. When a current-run `get_my_order` or
`list_my_orders` result identifies a nonempty imported snapshot, the application
appends one deterministic note that the order data is imported and that an estimated
delivery does not confirm actual receipt. It does not rewrite the generated status
or dates. Exact duplicate notices are suppressed; empty results and historical tool
returns do not trigger the notice.

The recorded Qwen answer now replays through the output validator and returns the
answer with the appended notice in an offline regression. Separate order-API tests
verify that the notice survives the HTTP path and persisted history. The output
validator no longer rejects claims based on the phrases “conforme o prazo estimado”
or “perfeito estado”: those checks incorrectly rejected a correct explanation that
quoted and qualified both phrases. A scripted HTTP regression now verifies that this
correct answer preserves the order status, includes current policy citations, and
receives the deterministic snapshot notice. The original Qwen captures remain as
evidence of semantic failures, but the validator does not establish whether claims
are supported by their evidence. That distinction requires representative model
evaluation; no live model call was made for this change.

The exact snapshot phrase was also removed from the persona and order-tool guidance,
and the general output correction now includes only feedback for the failed checks.
Current-run citation and monetary provenance checks, mixed-tool enforcement,
customer-scoped order access, the single retry and execution limits remain unchanged.

A bounded provider-free E5/Chroma check used the existing index. The standalone
follow-up “E se eu já usei o instrumento?” returned 1.1, 10, 8.3, 4.2, 8.1 and 8.2,
missing section 4.1. Adding the preceding user question returned sections 4.4, 4.1
and 4. Runtime search now uses the current question plus the latest previous user
question when their combined text is at most 256 characters. Assistant responses,
tool results, identity and evaluation labels are excluded. A topic-switch check with
a prior hours question returned section 2 alongside sections 4.3, 4.1 and 4; limited
context can add irrelevant evidence. This is a retrieval-only correction, not an
answer-quality result or new US-15 metric. Ranking, expansion, corpus, frozen labels
and US-15 targets are unchanged.

The complete offline suite passes **351 tests**. Ruff lint and format, strict mypy
across 89 files, package build and `git diff --check` pass. In addition to saved-trace
replay, one post-change live mixed-case now received a Qwen response. This single
case is descriptive evidence, not a reliability estimate. No RAG-versus-Full-Context
superiority claim is needed for sprint closure, and the unmet US-15 retrieval targets
remain unchanged.

## Authorized post-change Qwen attempts

The first frozen `mixed-order-return` attempt ran in `us-east-1` with five maximum
model requests/tool calls, 1,024 output tokens per request, and a US$0.05 reservation
cap. It returned HTTP 503 before inference, with **zero model requests and zero
input/output tokens**. That command explicitly selected the SSO profile and did not
load the repo-root `.env`; a read-only STS call later confirmed the profile identity,
but did not test Bedrock invocation or the access keys in `.env`. This failed attempt
provides no evidence about model tool selection or answer quality.

The sanitized capture preserves the `TokenRetrievalError` class but omits Botocore's
raw provider error. Diagnostics add a fixed, non-sensitive hint; they do not claim
to identify the underlying cause. The later env-based success distinguishes the
working credential path but does not diagnose why the SSO invocation failed.

The first capture is [mixed-postchange-qwen.json](mixed-postchange-qwen.json). The
probe initially marked any completed HTTP exchange as a completed case; after review,
the capture labels the probe `completed_with_failures` and the case `failed`. The
harness now preserves that distinction for future runs.

A second attempt was separately approved and loaded the repo-root `.env` with
`AWS_PROFILE` unset, following the documented invocation. It returned HTTP 200 in
20.877 seconds and used `get_my_order(order_id=4)` plus `search_store_policies`.
The initial generated answer stated that order 4 was marked delivered. Its citation
was rejected; the retry explained and cited current-run section 4.1, did not infer a
receipt date from the estimate, and asked for purchase channel, actual receipt date,
and product condition, but omitted the requested order status. The application
appended the deterministic snapshot notice, which describes provenance but does not
repeat operational status. The final answer returned HTTP 200 after four model
requests total, 16,591 input tokens and 510 output tokens. At the historical
accounting rates, the estimated cost was US$0.0037262; this is not invoice pricing
and was under the approved US$0.05 cap.

The final answer also said the condition “must be verified visually” and offered
examples such as string use. Those details were not in the retrieved policy or tool
evidence. Citation provenance was correct, but that does not prove every claim is
faithful to the evidence. This is a concrete semantic-generation limitation. The
capture is [mixed-postchange-qwen-attempt-2.json](mixed-postchange-qwen-attempt-2.json).
This single case demonstrated both tools and policy grounding, but exposed the
retry-status omission described above.

The citation-retry feedback now instructs the model to retain relevant operational
facts already returned by tools while correcting the policy explanation. A scripted
HTTP regression forces a citation retry after both tools have run and verifies the
corrected response retains the order status and current-run citation; it adds no
production requirement for a particular status word. The focused regression module
passes. This change has not been re-evaluated with a live Qwen call, so post-fix live
behavior remains unverified.

## Instruction simplification after Finding 4

The saved mixed-case request did not report instrument use. After citation retry,
Qwen introduced that hypothetical, required visual inspection, and supplied wear
examples absent from the evidence. The persona, policy advice and retry feedback
repeated related historical scenarios. This supports investigating instruction
influence; the trace alone does not establish causation.

Policy tools now return only status and source records. Their section-specific
advice branches and optional advice field were removed. The persona states general
principles about relevance, source scope, unknown customer facts and source gaps.
Citation feedback corrects source attribution and preserves relevant order facts
without restating return rules or requesting visual inspection. Order-tool advice
retains snapshot semantics and the required mixed-policy lookup.

The obsolete test that asserted scenario-specific advice text was removed. Existing
scripted source-scenario, two-turn policy, provenance, order and citation-retry
regressions remain. The full offline suite passes 350 tests; Ruff, format, strict
mypy, package build and diff checks pass. These checks establish application
contracts. No live provider call was made, so the effect on Qwen answer quality
remains unverified. Historical captures and the policy source remain unchanged.

## Finding 5: authorized current-code grounding batch

The owner approved one Qwen3 32B batch in `us-east-1` at revision `4f36cf5`,
using repo-root environment keys, four conversations/six turns, and a US$0.25
ceiling. Each turn allowed five model requests, five tool calls and 1,024 output
tokens per request. The frozen protocol and full sanitized trace are preserved in
[grounding-batch-qwen.json](grounding-batch-qwen.json). The protocol required
stopping at the first HTTP/provider failure, with no external retry.

The first mixed order/return turn returned HTTP 500 after 15.657 seconds, so the
remaining five turns were not executed. The recorded failure chain is
`AgentExecutionError → UnexpectedModelBehavior → ToolRetryError → ModelRetry`.
Both `get_my_order(order_id=4)` and `search_store_policies` succeeded; the policy
result contained sections 4.3, 4.1, 5.2 and 4.4.

Both generated candidates preserved the order status and product. The correction
also described the order as imported snapshot data. The initial citation omitted
page information. After feedback, Qwen used `(4.1 Direito de Arrependimento, p. 4)`;
a reader can identify the returned source, but this syntax does not match the
current citation parser. The single output retry was exhausted. Neither candidate
was delivered as a successful customer answer. A provider-free replay reproduced the
rejection. Changing only the citation to `[política 4.1, p. 4]` made the candidate
pass the existing validator. That edited text is a diagnostic variant, not a new
Qwen answer, and it retains the semantic shortcomings described below.

The seven-day receipt-based rule and product conditions agree with section 4.1,
but the candidate omitted that this rule applies to online purchases and did not
ask for the missing purchase channel, receipt date or product condition. Its offer
to initiate the process did not resolve eligibility. Neither candidate repeated
the historical instrument-use hypothetical, visual-inspection requirement or wear
examples. This one observation does not establish a causal effect of simplifying
instructions or reliable grounding.

| Dimension | Observed outcome |
| --- | --- |
| Required mixed-path tools | Both succeeded in the attempted turn |
| Relevant evidence | Section 4.1 was available |
| Operational fact preservation | Status and product retained through retry |
| Citation output contract | Failed after one correction |
| Claim scope and missing facts | Partial: online condition and clarification omitted |
| Overall HTTP outcome | Failed, 500 |
| Other five planned turns | Not executed; tool use and grounding remain untested |

Usage was four model requests, 15,094 input tokens and 358 output tokens. The
historical accounting estimate is US$0.0033052 at US$0.20/M input and US$0.80/M
output; this is not an AWS invoice measurement. The attempted turn reserved
US$0.036864. No remaining turn or rerun was invoked. Source/corpus and operational
snapshot hashes still matched the frozen protocol after execution.

The next investigation should distinguish citation-format brittleness from policy
applicability and missing-fact handling. This batch supplies no new evidence about
the unguarded standalone no-tool workflows. No production rules were changed from
this result, and no semantic validator or additional orchestration was introduced.

## Owner-approved output simplification after the failed batch

The owner rejected citation formatting as a reason for HTTP failure and requested
simple output handling, including a review of similar cases. Three focused regressions
failed on the former implementation: the saved Qwen citation candidate returned HTTP
500, a legitimate customer-budget quote was rejected as an unsupported price, and
“Não quero devolver o pedido 4; só confira o status” was classified as a return request
requiring a policy lookup.

The output layer no longer parses generated citations, matches currency mentions to
a set of tool values, or classifies mixed intent from Portuguese keywords. It appends
“Fontes consultadas” from successful current policy records, and retains snapshot,
partial-result and promotion notices. It still protects blank/internal-control output.
Exact pricing, scoped reads, input validation, persistence and execution limits remain
in their existing tool/application boundaries. Historical captures are unchanged.

This intentionally retires the former output-provenance/amount/intent gates and their
rejection tests. The application-generated source list is trustworthy provenance of
consulted records; generated references and prices are not automatically certified.
Unsupported claims and missed tool calls remain possible and must be reviewed as
model behavior. There is no new semantic parser, judge model, router or fallback layer.
The offline benchmark's optional numeric audit stays in benchmark code and does not
reject application answers.

The exact last Qwen candidate now returns HTTP 200 through a scripted HTTP/real SQLite
regression after both tools, with no citation correction, without editing the generated
text. Its missing applicability conditions are still recorded as a model-quality gap.
Other tests cover source-notice deduplication, current versus historical/insufficient
evidence, readable or missing model citations, budget quotes and negated return text.
No live provider call was made; the exhausted batch was not rerun. Current live model
quality remains unverified.

Validation for this simplification: all 318 backend tests passed, Ruff lint/format
passed, strict mypy passed across 89 files, source/wheel builds passed and
`git diff --check` passed. The lower test count reflects removal of tests asserting
the superseded prose-rejection contract; pricing arithmetic, customer scoping,
persistence, sanitized operational errors and execution-limit coverage remain.
