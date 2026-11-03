# Luna policy-context A/B protocol

**Issue:** [#78](https://github.com/rafaself/atf-ai-engineer-challenge/issues/78)
**Protocol:** v1.0, frozen before paid inference, 2026-11-03
**Generator:** GPT-6 Luna only (`us.openai.gpt-6-luna`, us-east-1 Runtime Converse)
**Budget:** explicit US$1.00 total approval, including both arms' preflight

## Question and comparison

Do the answer quality and operational savings of current policy RAG justify its local E5/Chroma complexity compared with embedding the entire current, reviewed policy corpus in Luna's system instructions? The current reviewed corpus, structured return conditions, provenance, and approved freight clarification are used in both arms. The original PDF is provenance, not the embedded input.

| Arm | Policy access |
| --- | --- |
| A — RAG | Existing `search_store_policies`: deterministic scopes for returns, exchanges and defects; three E5-ranked seeds plus existing expansion for `general`. |
| B — Embedded | Entire validated `data/policies/corpus.json` included as policy data in system instructions on every request; no policy-search tool. |

Only policy-access instructions and exposure of the policy tool change. Catalog and order tools, selected fictional customer, output validation, history, timeouts, retries, maximum requests/output, model route, persona, temperature, and operational snapshots are held constant. Arm B's order-lookup tool help removes its RAG-only direction to call the policy tool. Both arms retain the same read-only operational boundaries. No production source is changed.

The embedded data is the exact canonical JSON serialization of the validated current corpus chunks, with page/section/source provenance, prepared text, structured online-return rule, and overlay metadata. The serialized bytes and SHA256 are recorded. The source corpus/freight overlay hashes are frozen and rechecked before each provider request. No extra policy facts are written into the embedded arm.

## Workload and schedule

The exact 12-conversation / 18-turn fixture and source references are in `scenarios.json`. C01–C08 reuse the exact user turns from current v7; C09, C10, C11 and C12 reuse expansion questions n01, n04, n06 and n12. Expected facts, critical errors, effective-corpus evidence groups and applicable policy scopes were checked against the current corpus before inference. Superseded rubric claims are corrected in the frozen fixture; historical files remain untouched. This is a regression comparison, not an independent holdout.

Each conversation runs once per arm with an isolated chat session and identical customer context. Execution order alternates A/B then B/A by conversation index. The user-turn order within each conversation is unchanged. There is no prompt tuning, benchmark-only model retry, fallback or substitution. SDK transmission retries are disabled; the application's existing one output-validation retry remains enabled and counted. Tool retries remain zero, as in the current agent.

Both arms receive one non-scored live tool roundtrip preflight. The RAG/index readiness check uses local cached E5 and is measured separately; it makes no Bedrock request. It records index validation and cold E5 initialization. Main RAG timings then show warmed retrieval behavior. All times are end-to-end HTTP request elapsed time; provider requests and local retrieval are separately logged when observable.

## Scoring and evidence

Each completed conversation is manually scored Pass/Partial/Fail against the frozen facts and critical-error rubric. Explain every Partial/Fail/critical finding using the actual answer and effective policy/operational evidence. The same evidence authority applies to both arms. The allowed previous-turn assistant answer can support a follow-up; a source-footer alone does not prove grounding. Arm B is not penalized for lacking the intentionally removed policy tool. User/model answers are never used to create retrieval relevance labels. No LLM-as-judge or phrase-only scoring is used.

Report these measures per arm and per conversation:

| Measure | Denominator / handling |
| --- | --- |
| Pass / Partial / Fail, critical errors, unsupported claims | Completed conversations; failed execution is separate and receives no semantic verdict. |
| Tool correctness and grounding | Required current operational reads, arguments/results, missed calls; policy results are judged by actual claims, not appended source names. |
| Turns, model requests and tool calls | Per turn/conversation; include validation retries and every failed call. |
| Tokens / cost | Actual provider input/output and cache details where reported. Price using verified Luna short-context rates; include unknown-usage reservations. Estimates are not invoices. |
| Latency | Per attempted HTTP turn, median and maximum; include request/tool time. Report failures and not-executed separately. |
| Policy context | Actual returned RAG records per call and whether every required evidence group was present. Embedded availability is corpus-wide, not answer evidence. |

Retrieval ranking metrics apply only to eligible, answerable `general`/E5 queries in Arm A. After the paired call, a separate top-five diagnostic uses that query and the same index/metadata filters; it never changes the runtime three-seed context. Scoped policy paths are deterministic and get context coverage but no ranking metric. For each labeled query report binary Recall@5, Precision@5 (fixed denominator five, missing ranks count nonrelevant), MRR@5 and binary NDCG@5. Alternative sufficient groups are alternatives for a relevance hit but all required evidence groups must be present for context-coverage success. Queries with no relevant evidence are excluded from ranking averages and scored separately for correct abstention. Expanded contexts may exceed five records; their coverage is never Recall@5.

Primary aggregate comparisons include absolute differences and denominators. Retrieval metrics explain RAG evidence availability; answer correctness and total cost/latency determine the architecture tradeoff. One small paired pass does not establish statistical superiority.

## Cost guard and approvals

Current verified us-east-1 Luna rates from the same-day official Bedrock model card are US$0.11/1M input and US$0.55/1M output, with US$0.1375/1M used as the conservative implicit-cache-write input rate. Every provider request is reserved before transmission at `UTF-8 serialized request bytes + 2,048` input tokens and the full 1,024-token output allowance, using the higher applicable input/cache-write rate. Missing usage keeps that entire reservation; cache reads are charged at uncached input rates. Each request must stay below the 272,000-token short-context tier. Across preflight and main, the enforced aggregate serialized input bound is 4,500,000 tokens and the request ceiling is 240; the request-level US$1 cap stops further transmission before overspend.

There is no paid inference without the recorded explicit issue #78 approval. The approval cannot be carried to another run. Model pricing assumptions were checked 2026-11-03. No credentials are written to reports.

## Frozen sources and deliverables

Freeze the commit, app source hash, scenario file, original seven supplied CSV/PDF bytes, generated SQLite snapshots, corpus, freeze manifest, freight overlay, E5 weights and Chroma index before preflight. Recheck the freeze before each request. Generated databases/indexes and credentials are not committed. Historical benchmark files/captures remain unchanged.

Artifacts in this directory: `protocol.md`, `scenarios.json`, `embedded-policy.json`, `readiness.json`, `preflight.json`, immutable `capture.json`, `cost-reconciliation.json`, `operational-reconciliation.json`, `retrieval-metrics.json`, empty human `review.json`, blinded `review-worksheet-primary.json`, `review-worksheet-second.json` for required independent second reviews, `results.md`, and `SHA256SUMS`. The human candidate-arm map is private until reviews are frozen. Selection/recommendation waits for actual human review; no unreviewed AI recommendation is emitted.

### Post-run accounting amendment — 2026-11-03

The live capture is preserved unchanged. Auditing the returned token fields showed that Converse reports uncached `inputTokens` separately from `cacheReadInputTokens` and `cacheWriteInputTokens`; the in-run formula omitted cache-read input and the cache-write base rate. Its provisional input-token and cost fields therefore undercounted usage. [cost-reconciliation.json](cost-reconciliation.json) recalculates all requests from raw usage and records both the AWS model-card estimate and the protocol-conservative estimate. AWS documents the separate token categories and GPT-6 Luna short-context prices in its [Converse usage documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html) and [GPT-6 Luna model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-luna.html).

The initial operational summary also treated the RAG-only `search_store_policies` call as required in the embedded arm. [operational-reconciliation.json](operational-reconciliation.json) recalculates required-tool misses against each arm's actual tool set. Its per-turn operational checks are deterministic; semantic answer review remains human-only.

All 66 provider requests remained within their serialized input and output bounds. The sum of worst-case pre-transmission reservations was US$0.26700768, below the approved US$1.00 cap. The AWS-rate estimate is US$0.02122740; the protocol-conservative estimate is US$0.04014324. This amendment corrects cost reporting only; prompts, execution order, and human review gates are unchanged.

## Acceptance gates

Each arm must score at least 10/12 Pass, with zero critical errors, materially invented operational claims, or unauthorized customer-data disclosures. Account for 24 conversation executions and 36 planned turns across both arms, including errors and unexecuted cases. Recommend retain RAG, prefer embedded, or inconclusive based on reviewed quality first and measured efficiency second. If neither interpretation is stable from this small set, report inconclusive.
