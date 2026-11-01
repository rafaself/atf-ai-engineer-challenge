# Sprint 3 integration and delivery

[Issue #49](https://github.com/rafaself/atf-ai-engineer-challenge/issues/49)
is the single authoritative planning/tracking issue, including the hardened
acceptance contract. US-14, US-15 and US-16 are tracked as sub-issues #50, #52
and #55. US-17 remains in the epic unless separately requested.

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
US-16 is being delivered on its focused branch; the policy tool uses provisional
E5 filtering and bounded condition expansion. US-17 still owns reviewed answer-quality
evidence; this implementation makes no answer-quality claim.

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
