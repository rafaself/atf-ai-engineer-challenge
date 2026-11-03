# Final Bedrock Runtime Converse model benchmark

**Status (2026-11-03): standalone runner and human-review tooling implemented under [#82](https://github.com/rafaself/atf-ai-engineer-challenge/issues/82); paid preflight, main execution and human verdicts have not occurred.**

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
- [Standalone measurement runner](../../../scripts/final_model_comparison.py)
- [Blinded review and reporting tool](../../../scripts/final_model_review.py)

The results artifacts `preflight.json`, `capture.json`, `review.json` and `results.md` **do not exist yet** and must not be fabricated. The implementing runner must write sanitized immutable captures under this directory and keep previous reports untouched.

## Execution checklist

1. Run the offline checks and commit a clean source revision. This runner owns the ten-model configuration and accounting, without historical restrictions or resume state.
2. Validate the clean code revision and input/index hashes, exact dataset counts, current model routes, price assumptions, model/provider request parameters, and budget guard **without inference**.
3. Obtain fresh explicit user approval for a paid cap not exceeding US$10.00. Run the fixed tool-using Converse preflight for all candidates and record preflight costs.
4. Run one model-interleaved, seeded pass of all 16 scenarios, capturing every attempt/failure and preserving all model/operational tool evidence.
5. Blind model names for manual review, obtain the stipulated second review for all Partial/Fail/critical cases, reconcile reported spend and publish the model comparison using the **already-frozen** decision rule.

This is a **bounded engineering regression benchmark**, not proof of statistical superiority. A candidate with an inaccessible route is marked blocked rather than silently replaced. A missing review/turn cannot be counted as a pass. The benchmark does not change the production default model.

## Commands from the repository root

Run `make check` first. Readiness uses the existing local E5 cache and a temporary copy of the policy index; it does not download weights or invoke a model. Keep working output outside the checkout so the selected revision stays clean:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_comparison --work-dir /tmp/emporio-final-82
```

`readiness.json` records source/data/index/weight hashes, effective limits, cold initialization and the **US$9.81175456** conservative full-run envelope. The same 2,000,000-token aggregate input ceiling is enforced for every candidate, including preflight; the request guard rejects higher-cost tiers and stops globally on accounting faults.

Only after separate explicit approval of the proposed US$10 cap, run:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_comparison --work-dir /tmp/emporio-final-82 \
  --live --max-cost-usd 10.00 --approval-note '<exact user approval and date>'
```

The checkpoint reserves each request before transmission and retains missing-usage bounds. `--resume` accepts only this experiment's checkpoint, the same approval/cap and exact frozen inputs; it skips every attempted conversation. Final `capture.json` and `preflight.json` are created exclusively and never overwritten. Preserve the original run directory for interruptions; a fresh directory is a new experiment, requiring a new approval.

Prepare human forms and a preliminary operational report after capture:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_review --run-dir /tmp/emporio-final-82 --prepare
```

Give reviewers `review-worksheet.json` and the frozen rubric; keep `review-aliases.json` and raw model identities with the operator until primary judgments are frozen. `review.json` starts with empty assessments. Each assessment identifies `reviewer_type: human` and `reviewer`, a `verdict` (`pass`, `partial` or `fail`), evidence-linked `critical_errors` and `unsupported_claims` lists, integer `missing_reads`, `incorrect_arguments` and `redundant_calls` counts, and `evidence`/`notes`. Every Partial/Fail/critical case needs a different human's `second` assessment; disagreements require an evidence-linked `resolution` preserving both originals.

After actual human judgments are supplied, render into a fresh report directory:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_review --run-dir /tmp/emporio-final-82 \
  --output-dir /tmp/emporio-final-82-reviewed
```

The tool reports `pending_human_review` while required judgments are missing. It never invents scores or presents unreviewed models as having no critical errors. Publish the sanitized capture/preflight, frozen human review, summary and report here after reconciling spend; never commit the temporary policy index or conversation databases.
