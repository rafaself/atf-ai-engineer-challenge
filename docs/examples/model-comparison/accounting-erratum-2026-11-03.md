# Historical call-count correction

The old recorder counted reconstructed assistant history as new model responses.
Accounting version 2 preserves history in traces but counts current-run responses
only. Provider HTTP attempts are reported separately, including failed attempts.

| Evaluation | Previously reported calls | Observed evaluation attempts |
| --- | ---: | ---: |
| Prompt/harness Qwen + GPT-OSS | 77 | 61 |
| Structured-return Qwen + GPT-OSS | 80 | 64 |
| Effective-data Qwen + GPT-OSS | 82 | 66 |
| Original Qwen + Nova Micro + Nova Lite | 111 | 90 |

These counts exclude separately recorded access probes. Synthetic history had
zero usage. Provider-only token totals reconcile for every model with recorded
model runs, so their recorded token costs are unchanged. Semantic verdicts and
raw captures remain unchanged. Older formats without model runs are not assigned
an inferred correction.

The [machine-readable erratum](accounting-erratum-2026-11-03.json) includes capture
hashes, per-model counts, counter completeness and token reconciliation. Generate
with `python -m scripts.review_call_accounting --help` from `apps/backend`; use a
new output path to preserve the existing evidence.
