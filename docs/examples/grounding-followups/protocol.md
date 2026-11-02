# Minimal grounding follow-up experiment

Owner approval: 2026-11-02, Qwen-only inference with a total US$1 budget for this goal.
The budget is a ceiling, not a target. Historical #40 and post-#43 captures are unchanged.

## Hypotheses and scope

- A purpose-led policy-tool description that explicitly includes follow-ups may
  improve fresh policy selection. It does not enforce it.
- Neutral citation examples for paginated and page-less sources may improve
  claim-level attribution. No business threshold is added to instructions.
- A general capability boundary replaces the narrower unsupported-action list.
  No new action, tool, router or validator is introduced.
- Current nonempty product results marked `inventory_basis=imported_snapshot`
  receive an existing-style deterministic notice. This guarantees disclosure only,
  not model factual accuracy, tool use or price calculations.

The decisive checks are unchanged from the prior sample: mixed-return follow-up
must consult policy evidence and qualify unresolved eligibility; hours follow-up
must retrieve fresh evidence; freight equality must cite the approved clarification;
zero-stock results must remain unavailable and offer no unsupported future service.
Promotion/PIX and selected-order follow-ups are passing controls. Inspect calls,
arguments, current returned evidence and customer answers. Preserve every attempted
turn, including failures. Do not rewrite verdicts or add enforcement to manufacture a pass.

## Fixed sample and accounting

Reuse all six conversation IDs and twelve Portuguese turns from the preceding
approved post-#43 sample (PR #73 / commit `3b0c3a3`), which themselves reuse #40.
Use its one-off caller and the existing US-18 recorder, not a new harness:

```sh
git show 3b0c3a3:docs/examples/issue-43-review/run_approved_probe.py \
  > /tmp/grounding-approved-probe.py
PYTHONPATH="$PWD/apps/backend" \
HF_HOME="$PWD/data/benchmark-cache/hf" HF_HUB_OFFLINE=1 \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
uv run --project apps/backend --extra policy-rag --locked \
  python /tmp/grounding-approved-probe.py --live \
  --output docs/examples/grounding-followups/qwen-after.json
```

The reused caller retains its stricter US$0.50 batch cap. It reserves US$0.324864
for all twelve turns under same-day verified pricing and unchanged 5-request,
5-tool, 1024-output limits, below the new goal's US$1 total authorization. Record
cumulative reservations/spend for any further justified batch; never exceed US$1.
No automatic reruns or model matrix. Policy retrieval is warmed on the same cached
E5 instance as before; latency is warm HTTP elapsed time, not cold-start comparison.
The prior baseline has 2 pass / 3 partial / 1 fail, with US$0.0131088 estimated spend;
that earlier separately approved spend is not part of this new goal's budget.

Before paid execution, run deterministic notice regressions and backend checks.
Afterward distinguish observed recoveries, persistent failures, regressions and
inconclusive differences. One sample per conversation cannot prove causality or
reliability. Use provider-backed response records for inference counts; synthetic
zero-token history entries in `RecordingAgent` are not additional provider calls.

## Evidence-led reduction after batch 1

Batch 1 tested all proposed edits at `8cbf8db`. Inventory disclosure was present
and freight cited the clarification, but policy follow-ups still omitted fresh
lookups; the holiday follow-up additionally asserted unsupported Christmas closure.
The capability rewording also did not stop future-stock offers. No causal claim
is made from one sample. Rather than layering on more instructions, restore the
original tool description and capability paragraph and retain only the deterministic
notice and neutral citation examples. The candidate commit and raw capture remain
reviewable. A second fixed batch validates that final reduced implementation.
Its additional full reservation is US$0.324864, so the two-batch total reservation
is US$0.649728, below the approved goal-wide US$1. No unchanged batch is rerun.
