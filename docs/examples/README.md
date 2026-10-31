# Live interaction evidence — deferred

**No real model conversations have been captured yet.** The user deferred AWS
profile confirmation. Default tests use controlled models and must never be
presented as live examples or evidence of Bedrock reasoning/tool selection.

After configuring a project profile, import the supplied CSVs with the README
command and run the opt-in tool probe in [bedrock.md](../bedrock.md). Then capture
five independent conversations from the repository root:

```bash
uv run --project apps/backend --locked python -m emporio_music_backend.agent.examples \
  --live --database data/catalog.sqlite3 --output-dir docs/examples/live
```

This incurs real model calls (up to five requests and five tool calls per scenario
by default). The directory must be absent or empty; previous evidence is never
overwritten. Each scenario has a 60-second deadline. The recorder validates that
the database is readable, records its SHA-256, model, region, SDK versions, UTC
capture time, request count, actual tool arguments/results and the actual answer.
A changed database invalidates the batch. Captures are pending review, not passes.
No paid command has been run as part of the current deferred implementation.

Use the supplied [snapshot identity](../../data/SHA256SUMS), copied on 2026-10-31;
these dates describe the supplied snapshot, not current stock. The capture's
database hash identifies the imported artifact. Record any alternate source or
model explicitly rather than presenting it as the default snapshot/model.

Review each generated file and add observations before committing:

| Scenario | Required evidence and review |
| --- | --- |
| Budget | search_products called with category violões and maximum R$1,000; available-only; 12 total matches before default limit 10; all recommendations active with stock and within budget; disclose truncation. |
| Named GD20 | Relevant name filter; returned price 219900 centavos and stock five; final answer consistent with those facts. |
| Unavailable GF-3D | Named search disables available_only; active stock zero; answer must not recommend immediate availability. |
| No matches | Relevant literal name query returns zero; acknowledge no matches without inventing alternatives or implying a provider failure. |
| Out of scope | Politely redirect the weather question to the store scope without claiming unsupported access or inventing facts. |

For each tool-based case, correlate tool-call IDs with results, check relevant
arguments and actual returned data, and review the final prose for unsupported
claims. Do not compare exact generated sentences. Mark failures honestly and
preserve the failing output. The recorder intentionally does not infer semantic
correctness from a successful request. Also evaluate unsupported policy/accessory
questions before final submission. The existing fresh-code probe proves a tool
round trip; it does not replace these catalog/grounding checks or an API live run.

The final challenge needs 3–5 reviewed real conversations; this README is only a
pending-evidence checklist and does not count as one. Confirm live API behavior
with [the curl example](../api.md) after importing the same snapshot.
