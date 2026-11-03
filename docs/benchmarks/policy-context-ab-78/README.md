# Luna policy-context A/B benchmark

Issue #78 compares the current policy-RAG path with the same Luna agent given the entire reviewed policy corpus in its system instructions. It runs 12 paired Portuguese conversations (24 executions, 36 planned chat turns) against frozen local catalog/order snapshots. No other generator is included.

The final recommendation follows manual review under [protocol.md](protocol.md). The live capture includes full customer-facing answers, model/tool messages, actual policy evidence, errors, request usage, cost reservations, and HTTP latencies. [retrieval-metrics.json](retrieval-metrics.json) records independent RAG top-five diagnostics and evidence coverage of the context actually returned at runtime. Review forms are shuffled and blinded by arm until primary scores are frozen.

The paid run is capped at US$1.00, including preflight. The runner reserves serialized request bytes plus a fixed token margin before every Runtime Converse request, limits output to 1,024 tokens and turns to six requests, retains unknown-usage reservations, and stops before a request that would exceed the cap. The $1 cap was explicitly approved for issue #78. Production source, prompts and model defaults are not modified by the benchmark.

Live capture completed on 2026-11-03: 24/24 conversation executions, 66 Luna requests, and no failed executions. Cost results are in [results.md](results.md) and [cost-reconciliation.json](cost-reconciliation.json); arm-specific operational checks are in [operational-reconciliation.json](operational-reconciliation.json). Primary human review remains pending; no semantic verdict or architecture recommendation is included.

Run readiness from the repository root:

```bash
uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.compare_policy_context --work-dir /tmp/policy-context-ab-78
```

After checking readiness and confirming the frozen inputs, the authorized run is:

```bash
AWS_PROFILE=your-authorized-profile uv run --extra policy-rag --project apps/api --locked \
  python -m scripts.compare_policy_context --work-dir /tmp/policy-context-ab-78 \
  --live --max-cost-usd 1.00 \
  --approval-note '2026-11-03: owner approved issue #78 paid inference, US$1.00 cap'
```

Set `AWS_PROFILE` to the account explicitly authorized for Bedrock inference; the runner does not select among configured profiles. A current SSO login or equivalent credentials must be available before the live command.

A separate work directory is required for a new run. Final captures are exclusive and never overwritten. The runner does not retry failed calls.
