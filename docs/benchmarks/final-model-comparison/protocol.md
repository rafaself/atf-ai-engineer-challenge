# Final model-selection benchmark — frozen protocol v1.2

**Status:** measurement protocol v1.2 frozen on 2026-11-03 and executed under issue #82. Post-capture review amendment v1.3 below authorizes an explicitly labeled AI assessment; human forms remain blank.
**Scope:** Empório da Música customer-support agent, application-level Bedrock Runtime Converse.
**Source fixtures:** `scenarios.json` and `models.json` in this directory.
**Baseline:** the current runtime architecture, not a model-only prompt exercise.

## 1. Question and experiment boundary

Determine which of the **ten named Bedrock models** is best suited for the **unchanged current application**, considering answer correctness, grounding, tool use, execution reliability, cost, and end-to-end latency. The result supports a bounded engineering choice, **not** a general model ranking or statistical reliability assertion.

**Every candidate must use the same integration:** `Pydantic AI → BedrockConverseModel → bedrock-runtime Converse`, via the existing FastAPI `POST /api/chat` / `ChatService` / typed local tools / SQLite / E5-Chroma policy retrieval. **No Mantle, Responses API, different agents, per-model prompt or tool-schema variants, or additional LLM stages.** Inference IDs may be foundation model IDs or regional inference profiles, but the endpoint and API must stay identical.

This is a standalone experiment with its own fixture, rubric, budget, captures and selection rule. Earlier benchmarks supply neither scoring requirements nor reusable spending approval, results or resume state. Reusing question text or runner helpers does not create an experimental dependency. This experiment holds RAG fixed; results from **RAG versus embedded-policy** [#78](https://github.com/rafaself/atf-ai-engineer-challenge/issues/78) must not be pooled into this model ranking either.

## 2. Candidates (fixed)

Use all entries of `models.json`, in this canonical order for registration, reporting and tie-breaking:

1. `nova_micro` — `amazon.nova-micro-v1:0`
2. `nova_lite` — `amazon.nova-lite-v1:0`
3. `nemotron_nano_3_30b` — `nvidia.nemotron-nano-3-30b`
4. `nemotron_super_3_120b` — `nvidia.nemotron-super-3-120b`
5. `gpt_oss_20b` — `openai.gpt-oss-20b-1:0`
6. `gpt_oss_120b` — `openai.gpt-oss-120b-1:0`
7. `qwen3_32b` — `qwen.qwen3-32b-v1:0`
8. `claude_haiku_5_5` — `us.anthropic.claude-haiku-5-5`
9. `gpt6_luna` — `us.openai.gpt-6-luna` (incumbent)
10. `gpt6_1_sol` — `us.openai.gpt-6.1-sol`

No candidate pruning based on past results. Verify actual account authorization and a tool-call round-trip for every candidate before the main run. Documentation of Converse support is not a guarantee that a particular account/SDK invocation succeeds; record that distinction. If a candidate is unavailable, preserve its excluded/failed status and missing turns; do **not** replace it with another model. Report a partial comparison honestly if fewer than ten run.

Official NVIDIA model cards: [Nano](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-nvidia-nemotron-nano-3-30b.html), [Super](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-nvidia-nemotron-super-3-120b.html). Both specify `bedrock-runtime` and `Converse`.

## 3. Fixed workload and source freeze

`scenarios.json` contains **16 Portuguese conversations and 26 turns per model**, hence **160 planned conversations / 260 planned HTTP turns** for ten models:
- 12 question sequences (20 turns) originally used in `docs/examples/model-comparison/scenarios-current-v7.json`, with expected behavior defined independently in this benchmark's local fixture against the current application.
- Four explicitly authored **new scenario probes** (six turns total), targeting online return/procedure claims, two-product follow-up references, historical order total versus unit price, and holiday-hour uncertainty.

These are **targeted regression probes**, not independently collected blind holdouts. Do not claim generalization from their outcomes.

Freeze before inference: one clean git commit SHA; `uv.lock`; all application Python source, evaluation scripts, persona/tools/validator, policy corpus/freeze/approved clarifications, operational CSVs and imported SQLite snapshots, E5 weights and index configuration, model list/IDs, the fixture, rubric and budget logic. Capture SHA-256 for individual files and a deterministic tree hash for generated index contents, plus the full git SHA and dirty-tree check. Abort if the selected source revision is dirty, an index is stale, or a required file/configuration hash changes. Old captures and fixtures stay unchanged.

Use **only the current effective policy corpus** and its reviewed source-specific guidance. Do not silently substitute original PDF wording or older freight/holiday interpretation.

For each scenario: create a fresh session with zero previous turns, use its exact question sequence and selected fictional customer (only if `customer_id` exists in the fixture), and keep the same session through follow-ups. Each model gets a separate conversation repository; snapshots and policy index are read-only during inference. No concurrent requests; no cross-model history or answer leakage.

## 4. Runtime settings and fairness

Use the **same frozen live application** for all candidates:

| Setting | Value |
| --- | --- |
| AWS entry region | `us-east-1` |
| Bedrock endpoint/API | `bedrock-runtime` / non-streaming `Converse` |
| Service tier | standard/on-demand |
| Agent instructions, tool definitions, output validator | identical repository revision |
| Temperature requested | `0` (only where supported; **record actual serialized setting**) |
| Top-p, reasoning-effort override, explicit prompt caching | none |
| Max output tokens/model request | `1024` |
| Aggregate input upper bound per candidate | `2,000,000`, including preflight; identical for all ten candidates |
| Input bound per provider request | serialized UTF-8 request bytes + `2048`; at most the smaller of the model context and short-context tier limit |
| Agent request limit / tool-call limit per chat turn | `6` / `5` |
| Provider read timeout | `15 seconds` |
| Chat-service timeout | `60 seconds` |
| SDK retries | disabled (`total_max_attempts=1`); retain existing application output-validation retry |
| User request / locale | exact fixture text, Brazilian Portuguese |
| History window | current default `HistoryLimits` (capture effective values) |

No model-specific safety instructions, better tools for one candidate, custom decoding experiments, prompt shortening, or special reasoning budgets. When the installed SDK drops unsupported inference settings (as previously observed for Luna/Haiku), **do not compensate with a different endpoint**. Record both requested and actually transmitted settings. Comparison is of the production-compatible integration, not matched decoding distributions.

**Order and timing:** after completing all readiness checks, initialize/warm the policy index once outside measured chat turns and log the cold-start time separately. Do not perform an unrecorded generative warm-up. Run scenarios in fixture order, but for scenario index `i` (zero-based), shuffle all ten candidate keys using Python `random.Random(20261103 + i).shuffle(keys)`. Execute those candidates sequentially for the scenario. This interleaving limits candidate-order drift; include actual order in the capture. Do not change the seed after viewing outputs. Persist each candidate's state only within the same conversation.

The primary latency is **client wall time of each POST /api/chat**, including model calls, local tool execution, and response validation; report per turn, median and maximum over attempted turns. Report separate E5 cold setup/lookup diagnostics when available. Do not compare this latency with model-only latency or claim p95 from 26 turns.

## 5. Paid-call gate, spend cap and failure behavior

Set a **hard experiment budget ceiling of US$10.00, including preflight inference, main run, failed attempts and retried/resumed attempts**. This number defines the maximum envelope; **the user has not yet approved spending US$10.00 or any other new amount**. No paid request may occur until a separate explicit approval records an allowed cap (at most US$10.00) and the harness has verified that its *conservative full-run cost envelope* fits that approval.

Before the first paid request:
1. Verify AWS access path, candidate model routes, price sources/rates/tier and context/output limits for the date of the run. The frozen model roster never changes; save a dated pricing snapshot with the capture, not fabricated "verified" values.
2. Check source hashes, local SQLite, verified effective policy index and E5 cache, dependencies, runtime config and unique output path **without inference**.
3. Simulate maximum accounting for **26 turns/model × up to six model requests/turn** plus one bounded tool-call preflight per model. Reserve conservatively using actual request bounds, provider-supported rate tiers, cache-write premiums and full output ceilings; block before any call that could exceed the approved cap. Never treat reserved spend as an invoice.
4. Preflight all candidates using the same short, predeclared **catalog tool-use prompt**: `Confira no catálogo o preço e o estoque do Yamaha C40 Nylon Natural.` Check at least one actual local tool call, successful tool result, follow-up Converse response, usage capture and correct response shape. Preflight responses are **not** scored as benchmark cases; include their costs in global spend accounting.

The implementation freezes the same aggregate input bound of **2,000,000 tokens per candidate**, including preflight, and at most **162 provider requests per candidate** (27 chat turns × 6 requests). Each request stays in the standard short-context tier. At the manifest rates, reserving all input at the greater of the uncached-input and cache-write rates plus all 162 × 1,024 output tokens gives a combined maximum of **US$9.81175456**. This is an enforced envelope, not expected spend. Exceeding an input bound or encountering usage above a reservation stops all inference; bounds are never silently raised. Before-call reservations are checkpointed durably before transmission; missing usage retains the reservation. An interrupted attempted conversation is not replayed on resume.

A confirmed incompatible or inaccessible candidate is `excluded_preflight` with exact error category and 26 `not_executed` main turns; proceed to the other candidates if safe. If any live chat turn fails, capture the HTTP response and sanitized exception category, stop that scenario for that candidate and preserve subsequent turns as `not_executed`; do not assign a semantic quality verdict. Continue independent scenarios for that candidate unless its model route is unavailable or a budget safety condition requires a stop. A global budget/accounting fault stops **all** further inference immediately. No automatic benchmark-level retries or prompt repair. A resumed run must skip previously attempted turns and carry forward their entire cost.

Cost accounting: count current model responses separately from SDK/HTTP provider attempts and local data-tool calls. Include all actual reported input/output tokens (including reasoning where included), cache reads/writes, and unknown-usage bounded reservations. Record missing usage. Calculate total USD and USD per completed Pass using real per-model applicable rates; input/output token totals must not double-count historical synthetic assistant messages. A failed HTTP turn remains part of attempted-turn and spend denominators.

## 6. Human review: frozen rubric

Review **the full completed conversation**, including all user questions, all final customer-visible answers, operational-tool results, policy evidence and run traces. Keep raw captures immutable. Randomized model aliases (not names) should be provided in the review worksheet; reveal the alias map only after the primary verdicts are frozen. Provider-specific phrasing may make full blinding impossible; report this limitation.

The `expected.facts` and `expected.critical_errors` fields in this directory's `scenarios.json` are the mandatory scenario-specific criteria. Historical rubric entries and verdicts do not override them. In particular, SAC/label questions require `return_contact`; its included return sections satisfy eligibility-evidence needs in the same turn without a duplicate `online_return` call. For every completed conversation, score these **independent dimensions**:

- **Answer quality (Pass / Partial / Fail):**
  - `Pass`: all materially requested facts/conditions answered correctly; no material unsupported factual claim, misleading definitive decision or needed clarification omitted.
  - `Partial`: useful but a material noncritical requirement is missing or ambiguous; **no critical error**.
  - `Fail`: materially wrong answer, unusable response, unsupported definitive business decision, or any critical error.
- **Grounding:** enumerate supported and unsupported material claims, distinguishing absent retrieval, retrieved-but-misapplied evidence, and invented actions/procedures. An appended `Fontes consultadas` footer does **not** validate assertions.
- **Tool correctness:** verify tool names, freshness, arguments, product IDs, customer scope and necessary reads **per turn** using both the fixture and actual previous answer. Missing tools are recorded separately; a missing source read that causes a baseless material answer also affects answer quality.
- **Critical errors:** flag incorrect authoritative price/stock/order data, ungrounded return/refund eligibility, invented actionable SAC/contact/label/procedure, privacy boundary violations, unsupported action promises or similarly consequential mistakes. Any critical error implies `Fail`.
- **Efficiency/UX diagnostics:** redundant current-turn tool calls, unnecessary repeated questions, excessive verbosity, failure to answer despite sufficient evidence, and unclear order-total/unit-price labeling. A harmless redundant call alone does not downgrade answer quality.

Count required operational tool opportunities at the **turn level** against fixture text and observed context; do not interpret `required_tools` as an excuse to skip follow-up refresh requirements. At least one valid tool result must support each claim that the application requires a current read for. Duplicate calls with no intervening new facts count as redundant; a justified refresh after new user facts does not. Do not compare answer word-count against a fixed target.

All conversations get one independent manual primary review; every `Partial`, `Fail` or critical-error candidate must receive a second, independently performed manual review **before publishing a final selection**. Record both assessments and resolve differences by citing exact tool and policy evidence, not by majority vote or a model-based judge. No LLM-as-judge, keyword/phrase-only scoring or artificial composite score.

## 7. Metrics and denominators

**Primary end-to-end comparison, per model:**

| Dimension | Report |
| --- | --- |
| Semantic quality | Pass / Partial / Fail counts and **evaluated completed conversations / 16 planned**, plus a scenario-by-model outcome matrix |
| Safety and grounding | critical-error conversations; unsupported material claim count; customer-boundary violations and case-level evidence |
| Tool use | missing required current reads, wrong tool/arguments/product IDs, correct scoped reads and redundant calls |
| Reliability | successful / attempted / 26 planned HTTP turns, provider failures, local infrastructure/transport errors, and not-executed counts |
| Model execution | current model responses, provider attempts, output validation retries, input/output tokens, cache read/write tokens and missing usage |
| Cost | model-run estimated USD, experiment total, estimated USD/Pass; preflight and failure reservations reported separately |
| Latency | per HTTP turn; median and maximum among attempted turns (plus completed-only distribution where useful) |
| Presentation | concise, clear answers and needless extra clarifications, reviewed separately |

A semantic verdict exists **only when all planned turns in the conversation complete**; execution failure has its own column, not an invented `Fail` or `Pass`. For a model with zero passes, USD/Pass is **N/A**, not zero. Report absolute differences and percentages only with nonzero denominators. Show token and cost results even for models with poor quality; do not normalize away failures.

**No retrieval Recall, Precision, MRR or NDCG in this model-comparison scorecard.** The fixed RAG system is common to all candidates; isolated retrieval diagnostics belong to #78 or the historical retrieval benchmark. The end-to-end result is the metric that can differentiate generators here.

## 8. Eligibility and model-selection rule (precommitted)

A candidate is **eligible for a final default-model recommendation** if it meets every gate:

1. **Zero critical errors and zero customer-scope violations** in the 16 completed evaluated conversations.
2. **At least 14/16 Pass** (87.5%) under the frozen answer-quality rubric.
3. All **26/26 planned HTTP turns completed successfully**, with no missing scenarios and no unreviewed Partial/Fail.

Among eligible candidates, rank lexicographically by:
1. More Pass conversations.
2. Fewer Fail conversations (then fewer Partial conversations).
3. Fewer missing mandatory tool reads/incorrect tool arguments.
4. Lower **estimated main-run USD per Pass** (excluding preflight cost, but including any failed/extra calls in main-run accounting).
5. Lower median end-to-end latency.
6. Prefer the current incumbent `gpt6_luna` if still tied; otherwise use canonical candidate order in `models.json`.

This is an **engineering selection rule**, not statistical evidence that one model is generally superior. If none satisfies all gates, the report must say `no eligible winner` and recommend **no automatic runtime switch**; do not loosen criteria after viewing scores. Blocked/unavailable candidates are ineligible, not assigned quality Fail verdicts. Even if a model ranks first, the runtime default does **not** change as part of this benchmark.

## 9. Implementation contract and deliverables

Keep implementation in `scripts/` and tests in `tests/`. `scripts/final_model_comparison.py` is the standalone entry point; it reuses accounting/capture helpers from `scripts/compare_models.py` and `scripts/evaluation_support.py` without inheriting historical runner restrictions. `scripts/final_model_review.py` prepares blinded human worksheets and aggregates submitted judgments. **Do not change production agent code, add providers/adapters or create a generic benchmark framework.** The final run uses this directory's fixture, model manifest, fresh approval, accounting and resume identity. Historical artifacts remain untouched. Offline tests cover the ten frozen candidates, schedule, sanitized captures, spending guard, resume, actual SDK serialization with stubbed network I/O, review gates and selection aggregation.

Deliver under this **exclusive highlighted directory**, without overwriting old benchmark results:

- `README.md` — scope, status, links and how to read results.
- `protocol.md` — this frozen contract.
- `scenarios.json` — exact 16 conversations, 26 turns and rubrics.
- `models.json` — exact 10 models, endpoints, pricing assumptions and proposed spending ceiling.
- `preflight.json` — actual account/endpoint/tool readiness and cost checks, created at execution.
- `capture.json` — immutable sanitized primary-run conversation/turn/tool/usage/latency evidence.
- `review.json` — blinded human judgments and independent second-review deltas.
- `results.md` — all-model comparison, per-scenario matrix, observed failure evidence, limits, spend reconciliation and precommitted selection-rule outcome.

**Completion criteria:** all static controls validated offline; all ten attempted through the same Runtime Converse integration; full turn/usage accounting; reviewed scenario matrix; explicit selection result or `no eligible winner`; validated report links and accurate limitations. Never claim readiness based only on documentation: the harness, AWS entitlement, spending approval and real measurements must each be verified separately.

## 10. Non-goals

No RAG-vs-embedded comparison, prompt/model tuning, new embedding methods, vendor API differences, alternate decoding configurations, long-context stress test, statistical hypothesis test, production default change, hidden retries or synthetic "perfect" scores. Preserve all historical benchmarks and discuss them only as non-comparable context.

**Frozen design changes require a new protocol version and new capture names before another main run.**

## 11. Owner amendment v1.3 — after capture, 2026-11-03

After all 260 main HTTP turns had been attempted, the owner explicitly changed
the review requirement:

> Skip human review by now, give only what your evaluation generated. But let the worksheet ready at the end. I change the protocol you can judge.

This supersedes §6's human-primary, independent-human-second and no-LLM-judge
requirements **for the present report only**. The published semantic evaluation
is one **unblinded Codex AI assessment**, authorized after seeing the operational
capture, without independent human review. It is not a preregistered human or
blinded evaluation. No additional paid inference is used for judging.

The 16 scenarios, source authority, critical-error definitions, Pass/Partial/Fail
rubric, execution-failure separation and §8 eligibility/tiebreak rules are
unchanged. `ai-review.json` preserves evidence-linked assessments separately
from the original, blank `review.json` and `review-worksheet.json`. The reporting
tool requires both recorded owner authorization and `--allow-ai-review` to apply
AI assessments and labels the result `ai_review_complete`. Its default human
workflow still requires independent second reviews. The resulting selection is
a provisional AI finding, available for later human verification.

No measurement was repeated after this amendment. `capture.json` remains the
byte-identical completed v1.2 capture; its source manifest points to the original
measurement commit, not the later reporting edits. Original v1.2 text is available
at that commit, recorded in the capture.

Separately, the owner waived a clean-tree interruption caused by their concurrent
README edit: “Ignore this clean-tree guard, it was me. Just keep going!” The run
continued from the identical clean measurement commit in an isolated checkout
after exact source/data/index/E5 equality checks. Every attempted case remained
untouched, including the interrupted case. The original capture and carried
spend are preserved in `capture-interrupted.json` and
`capture.json.resolved_control_stops`; this was a resume, not a new experiment.
