# Sprint 3 integration and delivery

[Issue #49](https://github.com/rafaself/atf-ai-engineer-challenge/issues/49)
is the Sprint 3 planning/tracking issue. US-14–US-17 are delivered in #50, #52,
#55 and #57; follow-up US-18 is #59. The owner has authorized closure and integration
into `main` under the revised scope below. The integration PR records the merge.

## Approved closure and evidence

Sprint 3 delivers the implemented policy path and its evaluation, with an honest
assessment of remaining limits. RAG superiority over Full Context and broader
retrieval/model optimization are not closure requirements. The later owner-approved
output simplification supersedes the earlier prose-based monetary, citation and
mixed-intent gates; their removal is documented in the [US-18 report](examples/us-18/results.md#owner-approved-output-simplification-after-the-failed-batch).

| Closure item | Evidence and limit |
| --- | --- |
| Policy corpus and reproducible embedded Chroma RAG | US-14/US-16; 29 source records, 26 indexable; pinned local E5, explicit index preparation and source/index fingerprints |
| E5/Titan retrieval comparison | US-15; frozen metrics, labels and targets preserved; no tested configuration met every target; E5 remains provisional |
| Actual policy and mixed operational/policy paths | US-17 and approved US-18 captures contain real calls/results; both tools succeeded in the latest attempted mixed turn |
| Confirmed output-delivery defects | Saved Qwen candidate now returns HTTP 200 in a controlled HTTP/SQLite replay without citation correction; legitimate budget quotes and negated return requests no longer trigger output errors |
| Simple output/provenance handling | Current-run sources-consulted, snapshot and truncation notices; exact pricing and customer isolation remain in the tools |
| Quality checks at implementation tip `9f5309c` | 318 backend tests, Ruff lint/format, strict mypy across 89 files, source/wheel build and diff checks passed; closure changes are documentation only |
| Evaluation honesty | Original US-17 and subsequent failed captures preserved; scripted models and offline retrieval are distinguished from live model behavior |

The latest approved six-turn live batch stopped after its first HTTP 500 at revision
`4f36cf5`, before the output simplification. The failure was citation-format retry
exhaustion; the candidate also omitted online-purchase applicability and missing-fact
questions. The other five turns were not executed. There has been no post-simplification
live model run. The passing HTTP replay establishes delivery, not semantic correctness
or general tool-selection reliability. See the [preserved batch review](examples/us-18/results.md#finding-5-authorized-current-code-grounding-batch).

Remaining retrieval targets, multi-turn/topic-switch retrieval noise, policy
applicability, missing-fact handling, unsupported model claims and missed tool calls
belong to the existing evidence-driven follow-up [#43](https://github.com/rafaself/atf-ai-engineer-challenge/issues/43).
Cost/model comparisons remain in [#40](https://github.com/rafaself/atf-ai-engineer-challenge/issues/40).
No new evaluation framework or provider call is required for this closure. Paid runs
still require separate approval. Sprint 4 and final submission/public-repository
requirements remain separate; this closure does not claim full challenge acceptance.

Hosted check runs were absent on the implementation tip. GitHub's protection/ruleset
endpoints reported that these features require a different plan or public repository;
normal PR merge rules must still be honored, without an administrator bypass.

## Integration base

After US-14 was delivered directly to `main`, `integration/sprint-3` was
fast-forwarded to include it and US-15. At the start of US-16 it matched `main`
at `1dc4d09611b85cdae5ea72618b4dff61c8400b83`. Create each story branch from the
latest reviewed integration tip and target its PR at `integration/sprint-3`.
Suggested names:

| Order | Branch | Reviewable delivery |
| --- | --- | --- |
| US-14 | `feat/us-14-policy-corpus` | Verified corpus, ambiguity notes, frozen labels/split/scoring/targets |
| US-15 | `feat/us-15-retrieval-benchmark` | Reproducible comparison, errors and justified configuration |
| US-16 | `feat/us-16-policy-tool` | Existing-agent integration and preserved safeguards/contracts |
| US-17 | `feat/us-17-policy-validation` | Real conversations, full-context comparison and closing checks |

Review each delivery before starting its dependent story. Reference `Refs #49`
in every commit body, link published commits from #49, and record actual checks
in PRs. Story PRs must not close the epic. Final integration into `main` is a
separate delivery decision. The owner authorized delivery of US-14 directly into
`main` on 2026-11-01; its PR therefore targeted `main`. The integration branch was
refreshed before US-15 and US-16.

## Approved scope and current state

Use embedded ChromaDB without a server for policy retrieval; retain SQLite for
operational snapshots and history. Benchmark E5 Base and Titan V2 against identical chunks and Portuguese questions. This evaluates
Portuguese retrieval with multilingual models, not cross-language quality.
US-14 implements offline policy extraction, a reviewed versionable corpus and a
frozen 25-question evaluation set. US-15 adds the local E5/Titan benchmark,
controlled Chroma index and measurement reports; its measurements and methodology have been reviewed.
US-16, US-17 and US-18 are delivered on the integration branch. The policy tool uses
provisional E5 filtering and bounded condition expansion, with one prior user question
for short contextual queries. The reviewed captures and limitations above define the
closure boundary; no general answer-quality claim is made.

Before tuning, US-14 freezes evidence groups/alternative chunks, a held-out
subset, metric definitions, numerical selection targets and critical cases.
The epic defines multi-section coverage, zero-relevance cases, filter fairness,
index fingerprints, explicit rebuilds, failure semantics and fair generation
comparison. Do not weaken targets after seeing results. Monetary source membership
and correct policy applicability must be evaluated separately.

The original PDF is already tracked at `data/store_policies.pdf`; provenance and
its checksum are in `data/README.md` and `data/SHA256SUMS`. Preserve its bytes.
The owner confirmed on 2026-11-01 that the manual is fictional and approved
versioning its normalized corpus (US-14 #50), superseding the earlier distribution
gate for that artifact. External provider processing remains a separate decision. Paid calls also
require explicit opt-in, confirmed access/region and a bounded cost estimate.

Keep model downloads, indexing and paid evaluation explicit. Application startup
and default tests must not trigger embeddings, downloads or provider requests.
Do not add a default Chroma embedder implicitly. Generated indexes stay ignored.
No extra search service, framework, agent graph, UI, deployment, order mutation or
operational-data rewrite belongs to this sprint.
