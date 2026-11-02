# US-18: orchestration and grounding corrections

Issue: [#59](https://github.com/rafaself/atf-ai-engineer-challenge/issues/59), parent
[#49](https://github.com/rafaself/atf-ai-engineer-challenge/issues/49).
Status: the orchestration, grounding, and citation-format fixes are in place. The
latest saved live Qwen mixed-case answer used both tools, retrieved section 4.1,
gave its rule and citation, preserved the “delivered” status, and asked for the
actual receipt date. The API nevertheless returned HTTP 500 because the answer
omitted one prescribed snapshot phrase. The output validator no longer requires
that wording: it appends a deterministic notice when current order-tool results
contain imported order records. Replaying that exact Qwen response now produces
the answer plus notice offline. The first post-change live attempt selected the
SSO profile path and failed before model inference. A later approved attempt loaded
the repo-root `.env` and completed this mixed case with HTTP 200, both tools and a
section 4.1 citation. Its initial answer preserved the requested order status, but
the citation-correction retry omitted that fact. Retry feedback now tells the model
to preserve relevant operational facts; a scripted regression covers this path.
This fix has not had another live Qwen run. The captured answer also included one
unsupported suggestion about visual inspection; see the [live review](results.md).
One live case does not establish general Qwen reliability or complete faithfulness.

The output validator no longer tries to infer answer meaning from phrases such as
“conforme o prazo estimado” or “perfeito estado.” Captures showed both unsupported
claims, but the lexical guards also rejected a correct answer explaining why those
phrases were unsupported. A scripted HTTP regression now verifies that the answer
can quote and qualify both phrases while retaining order status and policy citations.
This does not establish that a live model will consistently make those distinctions;
the historical failures remain evaluation evidence, and semantic claim support still
needs representative live review. The earlier sandbox stall was reproduced by a
fake-service ASGI request and disappeared outside the restricted sandbox.
Alternative-model comparison is deferred; no comparative performance claim is made.
See [actual results and follow-up](results.md).

The owner's clarified completion criterion is required functional behavior, confirmed
defect fixes, and an honest limitations assessment. RAG need not outperform Full
Context to complete this story or close the sprint. Retrieval optimization and
broader architecture comparisons are deferred. US-15's failed adequacy gates remain
reported, without lowering them or making optimization a prerequisite for these fixes.

## Bounded context-dependent retrieval check

The policy tool originally searched only the exact current question. With the same
cached E5 model and Chroma index, the full mixed order/return question retrieved
sections 4.3, 4.1, 5.2 and 4.4. The follow-up “E se eu já usei o instrumento?” alone
returned 1.1, 10, 8.3, 4.2, 8.1 and 8.2, missing section 4.1. Combining it with the
preceding user question returned sections 4.4, 4.1 and 4. The runtime now includes
only the latest prior user question when the combined query is at most 256 characters;
assistant answers and tool results are excluded. A topic-switch check added unrelated
section 2 while retaining section 4.1, so this bounded context can add retrieval noise.
These are local retrieval checks, not answer-quality tests or new US-15 metrics. The
corpus, filter rules, ranking and expansion remain unchanged.

Returning all 29 policy records would make section 4.1 available whenever the policy
tool is called. US-17 already exercised that Full Policy arm, but its generated answer
still treated “used” as conclusive proof of visible use and it also missed the policy
tool call in the mixed case. Full context removes this retrieval selection miss; it
does not guarantee the needed tool call or a correct answer. The bounded prior-user
query retains the existing RAG setup and makes no general quality comparison claim.

## Investigation and changes

The unchanged [US-17 captures](../us-17/captures.json) and
[review](../us-17/results.md) are the historical baseline, not a matched control for
this changed implementation. Source verification used Poppler layout extraction,
the original PDF checksum, and existing corpus regeneration/freeze tests. No source,
corpus, chunks, labels, ranking, expansion rules, or historical results were changed.

| Observed failure | Attribution and evidence | Correction and validation boundary |
| --- | --- | --- |
| Policy citation accepted without any policy lookup | Output-validation defect: `has_policy_evidence` previously gated the entire citation check. A nonmonetary fabricated citation therefore passed with no current evidence. | Check every citation against current-run section/page evidence, even if none exists. Six failing-before-fix cases cover absent, historical and insufficient evidence, with valid-looking and malformed citations. Existing tests cover wrong sections and monetary provenance. |
| Both modes stopped after only the order lookup for the mixed order/return prompt | Orchestration defect, independent of ranking: neither arm retrieved policy evidence. The old mixed-tool test scripted successful tool selection. | A bounded output guard rejects missing current `get_my_order` or `search_store_policies` returns for explicit Portuguese order/return requests. Two failing-before-fix regressions cover either omitted tool. The HTTP/SQLite regression replays the exact wrong RAG answer, observes rejection, supplies the missing policy lookup and completes within four model requests. The model and policy ranking are controlled in this regression. |
| Estimated delivery treated as receipt; invented current date and definitive denial | Generation/interpretation defect: order 4 exposes an imported snapshot and an estimate, not actual receipt, purchase channel or product condition. | Strengthened instructions and current tool guidance require missing facts and prohibit invented dates. The HTTP regression uses real customer-scoped SQLite data and verifies the repair path. Semantic interpretation still needs live review. |
| “Used” treated as conclusive signs of use | Generation defect: section 4.1, physical page 4, says **sem sinais de uso**, with original packaging, accessories/manuals and the online seven-day receipt condition. The customer's report does not resolve all conditions. | Instructions and section-specific tool guidance request the unresolved facts. An evidence-scoped output guard rejects “perfeito estado” for this covered mixed request and asks a targeted retry; the recorded-answer regression checks both rejection and a corrected response. This is a narrow guard, not a general entailment checker. |
| Free shipping asserted at exactly R$500 | Source ambiguity plus unsupported generation: section 5.1, physical page 4, defines only above/below. Relevant evidence was present in the recorded full-policy answer. | Put the equality caution beside section 5.1 evidence and strengthen instructions against a leading “yes” or automatic fixed fee. Do not invent a source rule or change frozen labels. Actual answer faithfulness remains a live-review question. |
| Instrument-loan service denied from silence | Unsupported generation: the source does not establish the service; supplying the whole corpus did not prevent the inference. | Instructions/tool guidance distinguish unspecified service from a positive or negative service claim. A partial retrieval result also cannot prove the entire manual lacks a rule. |
| Holiday closure omitted in full-context answer | Generation omission: section 2, physical page 2, explicitly closes Sundays/holidays separately from possible special-date extensions. | Tool guidance highlights both facts when section 2 is returned. No ranking change. |
| RAG `money-unknown` returned HTTP 500 | Unresolved internal cause: two successful policy returns are captured, but there are no model messages, usage or internal exception. The sanitized HTTP response alone cannot identify retry exhaustion, generation or another execution error. | Do not claim a root cause or a historical fix. The opt-in follow-up probe captures partial SDK messages and safe exception cause types even on failure; its offline test confirms that evidence survives output-retry exhaustion. Existing API/error tests retain sanitized failures. A live rerun is needed to determine present behavior. |

## What is enforced, and what is reviewed

Citation provenance means a section/page was returned successfully in this run.
The validator enforces that and current monetary membership/source citation. It does
**not** prove that an adjacent sentence follows from the cited text or that a source
amount applies to the customer. A false claim can have a valid citation. Claim support,
source ambiguity, completeness and eligibility reasoning must be reviewed separately.
Application `answer_guidance` is interpretation advice, not additional policy evidence:
it does not authorize citations or amounts, modify excerpts, or establish confidence.

The mixed-output guard covers explicit `pedido` identifiers with return/exchange/
refund/withdrawal wording, and order references resolved by a current detail lookup.
It requests correction rather than calling tools on the model's behalf. It permits
clarification when no order ID has been resolved and keeps guest selection behavior.
It is deliberately not a general semantic intent classifier: indirect paraphrases,
negated requests and broader multilingual behavior are not established by this guard.
Tool execution and correction remain subject to the existing five-request/five-tool
limits and single output retry. An uncorrected omission fails safely; it does not
become evidence that the model reliably selects tools.

## Offline validation

Run from the repository root:

```bash
uv run --directory apps/backend --locked pytest
uv run --directory apps/backend --locked ruff check .
uv run --directory apps/backend --locked ruff format --check .
uv run --directory apps/backend --locked mypy src tests scripts
uv build --project apps/backend
git diff --check
```

Validation after the live-derived query-contract correction on 2026-11-01:
**342 offline tests passed** (11.44 seconds), Ruff lint and
format checks passed, strict mypy passed across 89 source/test/script files, the
source distribution and wheel built, and `git diff --check` passed. The probe's
`--help` command also ran without provider setup. The initial focused baseline
reproduced eight failures and 26 passes before the validator changes.
The restricted execution environment hung on an existing asynchronous FunctionModel
test; running the same offline command outside that sandbox completed normally.
`UV_CACHE_DIR=/tmp/us18-uv-cache` was used because the ordinary uv cache was read-only.
Default test fixtures prohibit live model requests, including when credentials exist.

After the interrupted Qwen attempt, the probe was updated to persist in-progress
and partial evidence and emit safe phase logs. The latest validator feedback also
includes an exact imported-snapshot disclosure. After removing the unused
alternative-model probe path, validation passed **342 offline tests** (8.96
seconds), Ruff lint/format, strict mypy across 89 files, package build, and
`git diff --check`; see the [stall investigation](results.md#stall-investigation).

A subsequent local preflight used the cached pinned E5 model and existing Chroma
collection, with `HF_HUB_OFFLINE=1`, on the four exact US-17 RAG prompts. No model
downloads or provider requests occurred. All searches returned evidence:

| Case | Returned sections |
| --- | --- |
| hours | 2, 7.1, 7.3 |
| mixed-order-return | 4.3, 4.1, 5.2, 4.4 |
| money-unknown | 5.1, 5.2, 4.4 |
| return | 4.1, 4.2, 4.3, 4.4, 8.1, 8.2, 8.3 |

This confirms local retrieval prerequisites and the presence of the implicated
sections for these prompts. It does not evaluate generated answers or autonomous
tool selection. The initial attempt used the default home cache and correctly
failed with `LocalEntryNotFoundError`; selecting the documented benchmark cache
resolved that setup issue without changing or rebuilding retrieval.

## First-batch live protocol — executed after owner approval

Use only the four unchanged RAG prompts from US-17, once each, with fresh sessions.
Only `mixed-order-return` selects fictional customer 1. Traverse the normal HTTP
application, real operational repositories, existing E5/Chroma retrieval and generator.
No Oracle/Full Context arms or retrieval optimization are required.

The prepared command, **only after separate owner opt-in**, is:

```bash
export HF_HOME="$PWD/data/benchmark-cache/hf"
export HF_HUB_OFFLINE=1
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
uv run --env-file .env --project apps/backend --locked --extra policy-rag \
  python apps/backend/scripts/validate_us18.py --live --max-cost-usd 0.25 \
  --output docs/examples/us-18/live-captures.json
```

The script refuses output overwrites. Model: Bedrock `qwen.qwen3-32b-v1:0`, region
`us-east-1`, temperature 0, at most five model requests/five tool calls per case,
1,024 output tokens per request, existing single output retry and no experiment-level
reruns. Existing cached E5 weights and a compatible prepared index are prerequisites;
this probe neither downloads weights nor rebuilds retrieval. The cache exports
match the [benchmark setup](../../benchmarks/README.md); the pinned model is stored
there rather than in the default home cache. History is temporary;
the supplied operational snapshots remain read-only.

Reserve US$0.036864 per case, US$0.147456 total, using the historical conservative
accounting assumptions of US$0.20/M input and US$0.80/M output, with every allowed
request charged at a 32K input window and the output cap. These are estimates, not
current invoice prices. Requested authorization ceiling: US$0.25 for these four
calls only. New calls or reruns require their own authorization. Prior benchmark
permissions do not apply. Failed calls retain their full reservation.

Review actual final answers, ordered calls/results, citations and retries against the
unchanged [US-17 rubric](../us-17/protocol.md) and original source. Record each criterion
and explain any partial/fail. In particular, require both tools for the mixed case,
conditional eligibility and missing facts, no estimate-to-receipt conversion, no
invented current date, no threshold-equality inference and no service denial from silence.
Retain failures and partial messages; safe cause types/code must not expose raw exception
bodies or credentials. Record tokens, elapsed time and cost accounting descriptively.
One observation per case cannot establish general reliability or efficiency superiority.

The owner approved this batch, which completed once with all responses preserved
in [live-captures.json](live-captures.json). Three cases pass source-based review;
the mixed case initially mishandled delivery evidence and omitted snapshot qualification.
An approved focused rerun corrected those facts but missed section 4.1 after the model
broadened the search query. The tool now takes no query arguments and uses the exact
current question from the application. The next approved check stopped before policy
lookup and failed safely after output-retry exhaustion. The subsequent two approved
checks ran both tools with the exact question and retrieved section 4.1, but retained
condition-mixing or missing-rule/citation-association defects. Citation feedback now
requires explaining the supported rule, not merely appending a reference. The later
Qwen trace replay and narrow condition guard are described in [results.md](results.md).
