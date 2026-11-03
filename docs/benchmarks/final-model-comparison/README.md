# Final Bedrock Runtime Converse model benchmark

**Status (2026-11-03): protocol and fixtures frozen for review; runner adaptation, preflight, paid execution and human verdicts have not occurred.**

This is the **dedicated, prominently documented final model-selection experiment** for Empório da Música. It compares the same production-like agent stack across **ten** Bedrock models, all using **non-streaming Bedrock Runtime Converse**. It is distinct from [RAG versus embedded policies (#78)](https://github.com/rafaself/atf-ai-engineer-challenge/issues/78): the retrieval architecture remains fixed here.

The benchmark is independent of all previous runs: this directory owns its fixture, current-application rubric, budget, captures and selection rule. Historical question text is provenance only; old expectations, approvals, verdicts and resume state are not inputs to this experiment.

## Fixed workload

| Property | Frozen value |
| --- | --- |
| Candidates | 10 (including Qwen and incumbent GPT-6 Luna) |
| Scenarios | 16 Portuguese conversations |
| Turns per candidate | 26 |
| Total planned | 160 conversations / 260 HTTP chat turns |
| Source | 16 locally frozen scenarios; 12 reuse historical question text with independently defined expectations |
| Interface | `POST /api/chat` → `ChatService` → Pydantic AI → Bedrock Runtime Converse → local tools |
| Data | Frozen effective policies, E5/Chroma index and fictional SQLite snapshots |
| Evaluation | Manual Pass/Partial/Fail + grounding, critical errors, tools, reliability, tokens, cost, latency |
| Selection | Zero critical errors; ≥14/16 Pass; 26/26 successful turns; deterministic tiebreak rules |
| Budget | Hard proposed maximum US$10.00 **subject to separate explicit paid-run approval** |

## Primary artifacts

- [Protocol and precommitted selection rule](protocol.md)
- [Exact questions, conversation turns and expected behavior](scenarios.json)
- [Exact ten model routes and rate assumptions](models.json)
- [Historical question provenance](../../examples/model-comparison/scenarios-current-v7.json) — not this experiment's rubric
- [Existing comparison runner](../../../scripts/compare_models.py) — needs bounded adaptation for the ten-model final run, seeded interleaving and this dedicated result location

The results artifacts `preflight.json`, `capture.json`, `review.json` and `results.md` **do not exist yet** and must not be fabricated. The implementing runner must write sanitized immutable captures under this directory and keep previous reports untouched.

## Execution checklist

1. Implement only the necessary benchmark-runner extensions and offline tests. Reusable runner helpers currently recognize eight candidates; the final run needs its own ten-model configuration and accounting, without historical experiment restrictions or resume state.
2. Validate the clean code revision and input/index hashes, exact dataset counts, current model routes, price assumptions, model/provider request parameters, and budget guard **without inference**.
3. Obtain fresh explicit user approval for a paid cap not exceeding US$10.00. Run the fixed tool-using Converse preflight for all candidates and record preflight costs.
4. Run one model-interleaved, seeded pass of all 16 scenarios, capturing every attempt/failure and preserving all model/operational tool evidence.
5. Blind model names for manual review, obtain the stipulated second review for all Partial/Fail/critical cases, reconcile reported spend and publish the model comparison using the **already-frozen** decision rule.

This is a **bounded engineering regression benchmark**, not proof of statistical superiority. A candidate with an inaccessible route is marked blocked rather than silently replaced. A missing review/turn cannot be counted as a pass. The benchmark does not change the production default model.
