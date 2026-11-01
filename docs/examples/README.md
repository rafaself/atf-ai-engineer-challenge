# Reviewed live interaction evidence

The original [live captures](live/) preserve three failed behaviors: missing
truncation disclosure, unavailable-item filtering, and internal/control markup.
After remediation, the five [rerun captures](live-recheck/) passed manual review
against actual tool results. The [fresh-code probe](live-probe-2026-10-31.json)
proves Bedrock tool calling separately. The GD20 HTTP request also passed with
correct facts and clean output. Tests used Nova Micro in us-east-1 on 2026-10-31.
These are scenario-level observations, not a universal model-quality guarantee.
They predate US-12 promotion/PIX pricing and do not establish its live behavior.
Original captures remain unchanged; new pricing/multi-turn evidence belongs to US-13.

After configuring a profile or local environment access keys, import the supplied CSVs with the README
command and run the opt-in tool probe in [bedrock.md](../bedrock.md). Then capture
five independent conversations from the repository root:

```bash
uv run --env-file .env --project apps/backend --locked python -m emporio_music_backend.agent.examples \
  --live --output-dir docs/examples/live-next
```

This incurs real model calls (up to five requests and five tool calls per scenario
by default). The directory must be absent or empty; previous evidence is never
overwritten. Each scenario has a 60-second deadline. The recorder validates that
the database is readable, records its SHA-256, model, region, SDK versions, UTC
capture time, request count, actual tool arguments/results and the actual answer.
A changed database invalidates the batch. New captures start pending review, not passed. Use a fresh directory for each batch.
The probe, original scenarios, remediation rerun and HTTP checks incurred real requests.

Use the supplied [snapshot identity](../../data/SHA256SUMS), copied on 2026-10-31;
these dates describe the supplied snapshot, not current stock. The capture's
database hash identifies the imported artifact. Record any alternate source or
model explicitly rather than presenting it as the default snapshot/model.

Review each generated file and add observations before committing:

| Scenario | Required evidence and review |
| --- | --- |
| Budget | search_available_products called with category violões and maximum R$1,000; available-only; 12 total matches before default limit 10; all recommendations active with stock and within budget; disclose truncation. |
| Named GD20 | Relevant name filter; returned price 219900 centavos and stock five; final answer consistent with those facts. |
| Unavailable GF-3D | get_product_details includes unavailable items; active stock zero; answer must not recommend immediate availability. |
| No matches | Relevant literal name query returns zero; acknowledge no matches without inventing alternatives or implying a provider failure. |
| Out of scope | Politely redirect the weather question to the store scope without claiming unsupported access or inventing facts. |

For each tool-based case, correlate tool-call IDs with results, check relevant
arguments and actual returned data, and review the final prose for unsupported
claims. Do not compare exact generated sentences. Mark failures honestly and
preserve the failing output. The recorder intentionally does not infer semantic
correctness from a successful request. Also evaluate unsupported policy/accessory
questions before final submission. The existing fresh-code probe proves a tool
round trip; it does not replace these catalog/grounding checks or an API live run.

The original five files retain failures; live-recheck contains the five reviewed
passing remediation examples. This README does not count as a conversation. Confirm live API behavior
with [the curl example](../api.md) after importing the same snapshot.

The partial-selection footer is application-owned output derived from tool totals;
recorded answers are the actual SDK output after validation. Known markup is
rejected rather than removed. One corrective output retry is allowed; exhaustion
fails safely within request limits. For access-key mode remove AWS_PROFILE from
.env and the shell. Credentials and unrelated profiles must never appear in evidence.
