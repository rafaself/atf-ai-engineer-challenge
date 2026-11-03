# Conversation and evaluation evidence

Start with the [four curated Portuguese conversations](submission.md) linked from
the root README. Their transcripts identify the recorded model, application
revision and review limits. For offline application checks, see the
[validation record](../validation.md); for dated real-model results, see the
[model-comparison index](model-comparison/README.md). Neither historical transcripts
nor one-off model runs establish answer quality on every later checkout.

The [Sprint 2 closing conversations](sprint-2/closure/README.md) cover
budget/context, promotions/PIX and customer orders, including failed attempts.
The [US-17 paired policy review](us-17/results.md) adds four real Portuguese
scenarios through `/api/chat`, comparing provisional RAG with full-policy context.
It preserves actual tool results and model responses, including an HTTP 500 and
incorrect answers. These examples are limited qualitative evidence; they do not
establish general answer quality or that retrieval meets the frozen targets.

The [original Sprint 2 evidence](sprint-2/README.md) and
[simplification review](simplification-review.md) preserve earlier versions and
failures. Their offline-only statements describe those earlier delivery stages.

## Repeating a conversation

After an explicit paid-run opt-in, prepare/start the API using the root README and
replay the documented prompts through `/api/chat`, preserving the returned session
ID and fictional-customer selection. Review tool choices, returned facts and final
answers together; HTTP success alone does not establish correctness. The Sprint 2
index explains SDK trace capture. No separate recorder framework is required.

The old catalog-only recorder has been retired. The small opt-in
[provider probe](../bedrock.md) remains available for diagnosing Bedrock tool calling;
it does not establish customer conversation quality.
Completed one-off evaluation runners are retained in the
[scripts archive](../../scripts/archive/README.md).

## Earlier model and policy experiments

The [Nemotron holiday follow-up evaluation](grounding-followups/nemotron-benchmark-2026-11-02.md)
records a two-model smoke comparison through the chat/RAG harness used at that
time. It separates policy-tool selection from answer faithfulness and includes
its bounded cost accounting and limitations.

The [Nova 2 Lite holiday follow-up](grounding-followups/nova2-benchmark-2026-11-02.md)
records the bounded, owner-approved retry after an initial IAM denial. It likewise
separates retrieval choice from answer faithfulness and preserves the actual traces.

The [Qwen3 32B and Nova Lite comparison](model-comparison/current-harness-qwen-nova-lite-2026-11-02.md)
refreshes the nine-scenario comparison after the persona, policy and deterministic
inventory-notice updates, while preserving the earlier #40 capture.

The [post-implementation #43 review](issue-43-review/README.md) preserves its
approved Qwen sample and 12-query local E5 retrieval check. Sprint 4 setup and
integration checks are recorded in the
[US-23 validation report](../sprint-4-validation.md).

## Historical Sprint 1 evidence

The original [captures](live/) preserve failures involving truncation disclosure,
unavailable-item filtering and internal markup. The five [remediation captures](live-recheck/)
passed review against their tool results. The [provider probe result](live-probe-2026-10-31.json)
records a separate tool round trip. These records use Nova Micro in us-east-1 on
2026-10-31, predate promotions and persisted customer conversations, and remain unchanged.
Their recorded database hashes are historical metadata, not a current runtime requirement.

All captures are scenario evidence, not a guarantee of future model behavior.
Preserve actual failures and disclose the model, prompts, data and limitations;
never edit an incorrect answer into a passing example or publish credentials.
