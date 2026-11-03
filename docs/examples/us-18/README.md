# US-18: orchestration and grounding corrections

Issue: [#59](https://github.com/rafaself/atf-ai-engineer-challenge/issues/59), parent
[#49](https://github.com/rafaself/atf-ai-engineer-challenge/issues/49).
Current behavior follows the owner's output-simplification request. Citation grammar,
free-text currency matching and Portuguese mixed-intent regexes no longer reject
answers or cause corrective model calls. The output layer appends “Fontes consultadas”
from successful current policy results, along with existing snapshot and partial-list
notices. Blank/internal-control output still receives at most one correction.

This is a deliberate change to the former acceptance boundary. The application source
list records what was consulted; it does not certify model-generated citations,
prices, tool choice or claim support. Exact price calculations, customer isolation,
read-only data access, request/tool limits and genuine failure reporting remain.

The latest approved live batch at `4f36cf5` stopped on its first turn with HTTP 500
because the citation grammar rejected Qwen's correction. Both required tools succeeded
and order status was retained, but policy applicability and missing-fact handling were
incomplete. The other five turns were not run. The exact saved candidate now replays
through HTTP with source metadata and no citation retry in a controlled regression;
no new provider call was made. See the [batch review](results.md#finding-5-authorized-current-code-grounding-batch)
and [trace](grounding-batch-qwen.json). Historical model failures remain evidence of
limitations; accepting the saved text does not repair its semantic omissions.

Three failing-before-change regressions cover the saved citation failure, a legitimate
customer budget quote, and a negated return request. Tests for the retired rejection
contracts were removed; the tools' domain tests remain. RAG need not outperform Full
Context for sprint closure. Broader optimization remains deferred and the frozen
US-15 targets remain unmet.

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
| Policy citation accepted without any policy lookup | Output-validation defect: `has_policy_evidence` previously gated the entire citation check. A nonmonetary fabricated citation therefore passed with no current evidence. | The earlier prose-validation gate was retired. Current source notices derive only from successful current-run records; model-generated references require review. |
| Both modes stopped after only the order lookup for the mixed order/return prompt | Orchestration defect, independent of ranking: neither arm retrieved policy evidence. The old mixed-tool test scripted successful tool selection. | The model is instructed to call each relevant tool. The former Portuguese keyword gate was retired after rejecting a negated return request. Successful scripted mixed-path tests verify wiring; actual tool choice remains an evaluation concern. |
| Estimated delivery treated as receipt; invented current date and definitive denial | Generation/interpretation defect: order 4 exposes an imported snapshot and an estimate, not actual receipt, purchase channel or product condition. | General instructions require evidence for customer facts; order guidance distinguishes estimates from actual receipt. The HTTP regression uses real customer-scoped SQLite data and verifies the repair path. Semantic interpretation still needs live review. |
| “Used” treated as conclusive signs of use | Generation defect: section 4.1, physical page 4, says **sem sinais de uso**, with original packaging, accessories/manuals and the online seven-day receipt condition. The customer's report does not resolve all conditions. | Source excerpts retain the exact conditions. General instructions require scope-correct application and clarification of unknown facts. Scenario-specific policy advice and lexical output guards have been removed; actual semantic behavior still needs live review. |
| Free shipping asserted at exactly R$500 | Source ambiguity plus unsupported generation: section 5.1, physical page 4, defines only above/below. Relevant evidence was present in the recorded full-policy answer. | General instructions require acknowledging source gaps without inferring an unstated rule. The source and frozen labels remain unchanged. Actual answer faithfulness remains a live-review question. |
| Instrument-loan service denied from silence | Unsupported generation: the source does not establish the service; supplying the whole corpus did not prevent the inference. | General instructions distinguish missing evidence from an affirmative or negative service claim. A partial retrieval result also cannot prove the entire manual lacks a rule. |
| Holiday closure omitted in full-context answer | Generation omission: section 2, physical page 2, explicitly closes Sundays/holidays separately from possible special-date extensions. | The source retains both facts. General instructions require respecting the applicable rule and its exceptions; no section-specific advice is injected. |
| RAG `money-unknown` returned HTTP 500 | Unresolved internal cause: two successful policy returns are captured, but there are no model messages, usage or internal exception. The sanitized HTTP response alone cannot identify retry exhaustion, generation or another execution error. | Do not claim a root cause or a historical fix. The opt-in follow-up probe captures partial SDK messages and safe exception cause types even on failure; its offline test confirms that evidence survives output-retry exhaustion. Existing API/error tests retain sanitized failures. A live rerun is needed to determine present behavior. |

## What is enforced, and what is reviewed

The “Fontes consultadas” notice records source sections/pages returned successfully
in the current run. Historical or insufficient-evidence results do not create it.
Generated citation wording is preserved. The source list is not a claim that every
sentence follows from those sources or that a policy amount applies to the customer.

The model chooses tools under the existing instructions and execution limits. A
missing lookup or unsupported model claim is a quality failure to investigate, not
an intent classification performed by the output layer. Real tool/provider/timeout
failures still use the existing error contracts. Blank or internal-control output
can still exhaust the single presentation retry; no general error-swallowing fallback
has been introduced.

## Offline validation

Run from the repository root:

```bash
uv run --project apps/api --locked pytest tests
uv run --project apps/api --locked ruff check .
uv run --project apps/api --locked ruff format --check .
make check-python
uv build --project packages/emporio_music
git diff --check
```

Historical validation after the query-contract correction on 2026-11-01 (the prose gates and their tests were subsequently retired):
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
and partial evidence and emit safe phase logs. The validator feedback at that revision also
included an exact imported-snapshot disclosure. After removing the unused
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
uv run --env-file .env --project apps/api --locked --extra policy-rag \
  python scripts/validate_us18.py --live --max-cost-usd 0.25 \
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
condition-mixing or missing-rule/citation-association defects. Those earlier citation corrections and the since-retired condition guard are
preserved chronologically in [results.md](results.md).
