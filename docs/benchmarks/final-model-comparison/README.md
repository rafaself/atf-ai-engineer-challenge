# Final Bedrock Runtime Converse model benchmark

**Completed 2026-11-03 under [#82](https://github.com/rafaself/atf-ai-engineer-challenge/issues/82): ten live tool preflights passed; all 260 main HTTP turns attempted, 255 completed; 155 completed conversations assessed. Estimated total US$0.5954445075, including preflight and missing-usage reservations, within the explicitly approved US$10 cap.**

The [AI-assessed results](results.md) provisionally select **GPT-6 Luna**:
Luna and Sol each have 16/16 Pass and zero observed critical errors, with Luna
winning the unchanged cost tiebreak. The runtime default remains unchanged.
This is one **unblinded Codex AI assessment**, authorized by the owner **after
capture**. No independent human review has occurred. The owner amended the
human-review requirement in [protocol §11](protocol.md#11-owner-amendment-v13--after-capture-2026-11-03);
the original blank human worksheets are ready for later use.

This is the dedicated final model-selection experiment for Empório da Música.
All ten candidates use the same unchanged application and non-streaming Bedrock
Runtime Converse integration. The experiment owns its fixture, rubric, budget,
captures and selection rule, independently of previous runs and
[RAG versus embedded policies (#78)](https://github.com/rafaself/atf-ai-engineer-challenge/issues/78).

## Read the delivery

| Artifact | Purpose |
| --- | --- |
| [Results](results.md) | All-model scores, cost/latency and complete scenario matrix |
| [Analysis and execution notes](analysis.md) | Provisional recommendation, grounding/tool diagnostics, five execution failures, spend and resume reconciliation, judgment limits |
| [Summary JSON](summary.json) | Reproducible aggregate metrics and selection |
| [AI assessments](ai-review.json) | 155 evidence-linked AI judgments; five execution failures left unscored |
| [Final capture](capture.json) | Immutable answers, source/tool results, usage, settings, latency, failures and source freeze |
| [Interrupted capture](capture-interrupted.json) | Original partial capture retained without alteration |
| [Preflight](preflight.json) / [readiness](readiness.json) | Actual routes/tool roundtrips and source/data/index/E5 controls |
| [Human form](review.json) / [blinded evidence worksheet](review-worksheet.json) | 160 blank primary/second/resolution rows, including failed cases marked separately |
| [Checksums](SHA256SUMS) | Published JSON/evidence checksums |
| [Protocol](protocol.md) / [scenarios](scenarios.json) / [models](models.json) | Frozen v1.2 measurement design and separate v1.3 owner review amendment |

The operator's human candidate map is excluded from Git. Supply reviewers only
the blinded worksheet and frozen rubric, and freeze primary judgments before
revealing identities. Published raw answers and AI results can permit deblinding;
do not claim a blind review if a later reviewer has seen them. `review.json`
remains entirely blank; AI findings are never attributed to humans.

## Fixed workload and limits

| Property | Value |
| --- | --- |
| Candidates | 10, including Qwen and incumbent GPT-6 Luna |
| Scenarios / turns | 16 Portuguese conversations / 26 HTTP turns per candidate |
| Planned / completed | 160 / 155 conversations; 260 / 255 HTTP turns |
| Interface | POST /api/chat → ChatService → Pydantic AI → Runtime Converse → local tools |
| Measurement commit | `fb13623b6e0b161db05c671044705c9b6b4ff891` |
| Selection gates | Zero critical errors; ≥14/16 Pass; 26/26 successful turns |
| Approved / estimated spend | US$10.00 / US$0.5954445075 |
| Bounded full-run envelope | US$9.81175456 |

One targeted engineering regression pass does not establish statistical
superiority. Five failed conversations have no semantic verdict. One was a
source-guard interruption caused by the owner's concurrent README edit, not a
model failure. The isolated resume preserved all previous attempts and spending;
no failed conversation was retried. No prompts, production code, model defaults
or dependencies changed as a result of the findings.

## Reproduce reporting without inference

From the repository root, render the published AI assessments to a **fresh**
directory; this neither invokes a model nor alters the human worksheet:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_review \
  --run-dir docs/benchmarks/final-model-comparison \
  --review-file docs/benchmarks/final-model-comparison/ai-review.json \
  --aliases-file docs/benchmarks/final-model-comparison/ai-review-aliases.json \
  --allow-ai-review --output-dir /tmp/emporio-final-82-report
```

Human review remains the default. Once actual human judgments are supplied in a
copy of `review.json`, use `--review-file` with that copy and `--aliases-file`
with the private operator map, without `--allow-ai-review`. Every human
Partial/Fail/critical case still needs an independent second assessment;
disagreements require an evidence-linked resolution preserving both originals.

## Measurement commands

The completed run used the standalone runner, cached E5 and an explicitly
rebuilt, reviewed policy index. Readiness does not invoke a model or download
weights. Keep working output outside the checkout and use a clean source commit:

```bash
make check
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.final_model_comparison --work-dir /tmp/new-final-run
```

A new live experiment requires its own approval; the completed run's approval
does not authorize rerunning this workload. With explicit approval, the live
command additionally takes `--live --max-cost-usd 10.00` and
`--approval-note '<exact owner approval and date>'`. Source/input hashes,
bounded request reservations and serialized settings are captured. `--resume`
requires matching inputs, cap and approval, and skips attempted conversations.
Final captures are created exclusively, without overwriting existing evidence.

For a future capture, `python -m scripts.final_model_review --run-dir <run> --prepare`
creates blank human forms and an operational report. It never generates semantic
scores automatically. AI aggregation is an explicit, separately labeled opt-in
requiring recorded owner authorization.
