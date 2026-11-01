# Live interaction evidence

Start with the [Sprint 2 conversations](sprint-2/README.md): catalog/context,
promotions/PIX and customer orders, including failed attempts and their corrections.
Policy retrieval/evaluation remains later-sprint work.

The later [simplification review](simplification-review.md) records live regressions
and the new price check, which has offline verification only.

## Repeating a conversation

After an explicit paid-run opt-in, prepare/start the API using the root README and
replay the documented prompts through `/api/chat`, preserving the returned session
ID and fictional-customer selection. Review tool choices, returned facts and final
answers together; HTTP success alone does not establish correctness. The Sprint 2
index explains SDK trace capture. No separate recorder framework is required.

The old catalog-only recorder has been retired. The small opt-in
[provider probe](../bedrock.md) remains available for diagnosing Bedrock tool calling;
it does not establish customer conversation quality.

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
