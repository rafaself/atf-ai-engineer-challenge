# Sprint 2 closing evidence

Three representative conversations on the final application code passed review
against actual Bedrock tool results: **10 HTTP turns, all 200**. These are Codex-reviewed
scenario observations, not a guarantee of future model behavior or full challenge completion.

- Date: 2026-11-01; final batch started 2026-11-01T15:30:29.550571+00:00.
- Model: `qwen.qwen3-32b-v1:0`, region: `us-east-1`.
- Evaluated application commit: `8b9c321dad002b8cc9c44463269f1a35ff960ca3`. Subsequent evidence changes are documentation only.
- [Catalog/budget/context](01-guest-catalog-context.md): correct budget comparison, category filter, fresh ordinal lookup and scope redirection.
- [Promotions/PIX](02-guest-promotions-pix.md): original/discount/final prices, no stacking and guest-selection guidance.
- [Customer orders](03-customer-orders-context.md): correct list/detail and snapshot limits; source caveat is explicit on the final follow-up, not repeated in every answer.

## Execution and reproduction

The owner authorized final evaluation and sprint closure. Requests used the existing
HTTP composition via FastAPI TestClient → ChatService → real Pydantic AI/Bedrock →
actual tools → real temporary SQLite. Sources were imported unchanged. Follow-ups
reused session IDs; only the order conversation selected fictional customer 1.
No model/repository doubles or new recorder framework were used. Existing local
history and supplied CSV/PDF bytes remain unchanged.

Limits remained five model requests/five tool calls per turn, 1,024 output tokens,
15-second provider read timeout and a 60-second chat deadline. One output correction
is allowed. SDK capture retained actual tool arguments/results and final answers;
only Markdown trailing whitespace is normalized. Credentials, ephemeral session IDs
and rejected internal reasoning drafts are excluded from published transcripts.

For a future opt-in replay, prepare/start the API using the root README, select
this model with BEDROCK_MODEL_ID, and send the linked prompts in order using the
returned session ID and same customer selection. No extra acceptance harness is needed.

## Failed attempts and model choice

The final passing set was preceded by failures; they are not hidden or counted as passes.
The full closing exercise made **53 HTTP requests**, including **6 HTTP 500s**.
Diagnostic replays reconstructed the successful first promotion turn in temporary
storage before replaying the failed follow-up and guest request. Those are included below.

| Batch, including diagnostic replay | Application ref | HTTP turns | Non-200 turns |
| --- | --- | ---: | ---: |
| Micro baseline | `c9ef059` | 11 | 2 |
| Micro combined correction | `29730c8` | 9 | 1 |
| Lite comparison | `29730c8` | 11 | 2 |
| Qwen promotion probe | `29730c8` | 3 | 0 |
| Qwen before missing-facts feedback | `47474a2` | 9 | 1 |
| Qwen final acceptance | `8b9c321` | 10 | 0 |

Nova Micro repeatedly retrieved the correct R$439.20 PIX quote but generated an
unsupported price and internal markup. Reporting only markup wasted the single
correction; combined feedback now includes current monetary facts without raising
retry limits. Micro still failed the price case. Nova Lite also stacked the PIX
discount (R$417.24 instead of R$439.20) and omitted the requested category in one
catalog search, presenting ukuleles as violões. It was not selected.

Qwen's promotion probe passed. Its first full batch skipped fresh retrieval on the
catalog follow-up and failed safely. The existing correction message now explicitly
asks for a tool consultation when facts are missing. The final full batch above
then passed. This observation does not isolate each change's effect statistically.

Qwen is the default through the existing settings; no provider abstraction,
dependency, authentication, permissions or retry-budget expansion was introduced.
The supplied IAM reference already lists its model ARN. Other providers/models
can be selected explicitly; their quality is not established by these examples.

The failed HTTP response was the sanitized `{"detail":"Conversation failed"}`;
unsupported prices/internal drafts were not delivered as successful customer answers.
[Earlier failures](../../simplification-review.md) and [original Sprint 2 captures](../README.md)
remain intact. This record does not claim that every attempted conversation passed.

[Actual failed HTTP turns and the category failure](failed-attempts.md) preserve the evidence.

## Offline verification and remaining scope

258 offline tests, Ruff lint/format, strict mypy (69 files), source/wheel builds and
byte/link/diff checks passed. The new deterministic regression verifies that one
correction carries current prices even when markup is also invalid. Existing tests
protect retry exhaustion, budgets, ownership, persistence and source integrity;
no duplicate production-security or concurrency campaign was added.

The monetary check is numeric provenance, not semantic proof. A supported amount
can still be mislabeled; percentages and amounts without R$ are not fully checked.
Order source disclaimers depend partly on wording and were explicit when asked.
Policies remain outside Sprint 2 and are still pending for the full challenge.
