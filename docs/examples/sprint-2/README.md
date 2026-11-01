# Sprint 2 real-agent validation

Three representative conversations passed review against actual Bedrock/tool
results. Two earlier failed conversations remain intact alongside their corrections.
This is US-13's Sprint 2 functional evidence, not complete challenge acceptance or a
claim that the model is always correct. Policy retrieval/evaluation belongs to the
later retrieval sprint and was neither implemented nor evaluated here.

These captures predate the subsequent [simplification review](../simplification-review.md).
They do not establish the current price check's live behavior.

| Curated conversation | Observed result |
| --- | --- |
| [Catalog and context](01-catalog-context.md) | Budget/stock retrieval, “second option” resolution with a fresh lookup, and out-of-scope redirection |
| [Promotions and PIX](02-promotions-pix.md) | Correct original/final prices, a fresh non-stacking PIX quote, and guest order denial |
| [Customer orders](03-customer-orders.md) | Order-list/detail follow-up, preserved historical total and honest snapshot/carrier limits |

The [original PIX failure](04-promotions-before-correction.md) invented a stacked
price without retrieval. The [original order failure](05-orders-before-correction.md)
refused available detail instead of calling the tool. Neither is a passing example.
The corrective conversations use the same prompts and unchanged data after a small
instruction clarification. No answer wording or numeric value was edited into a passing result. Transcript
formatting only normalizes trailing whitespace for Markdown.

## Batch context

- Date: 2026-11-01. Model: `amazon.nova-micro-v1:0`, region: `us-east-1`.
- Original batch started at 10:32 UTC on base `1fccd852512993eccb06247035626284d72a8308`.
  The catalog example and both failed attempts use that baseline.
- Corrective examples use the same application plus the exact instruction changes
  subsequently committed as `90f6249e5782ebd40f337a97afe5ca54c582a130`.
  They were captured before that commit, with those changes in the working tree.
- The owner explicitly opted into bounded paid runs. Five conversations / 15 HTTP
  turns were executed; all returned HTTP 200, but two conversations failed semantic
  review. No additional paid evaluation was run after the corrective batch.
- Existing per-turn limits: five model requests, five tool calls, 1,024 output tokens,
  15-second provider read timeout and 60-second chat deadline. These are execution
  bounds, not a monetary guarantee.

## Path and reproduction

The calls used the existing `create_app()` composition through FastAPI TestClient:
HTTP → ChatService → real Pydantic AI/Bedrock → existing tools → real SQLite.
Temporary databases were imported from the unchanged supplied CSVs; runtime path
constants were redirected only inside that disposable capture process. Existing
local databases/history and source CSV/PDF bytes were untouched. There were no
model or repository doubles in the live runs.

Each follow-up reused its returned session ID; the customer conversation repeated
`customer_id: 1`, while guests supplied no customer ID. SDK messages were captured
per request using `pydantic_ai.capture_run_messages`; the attached traces retain
actual tool arguments, call IDs and results. Answers include the application-owned
output notices. System instructions, credentials and ephemeral session IDs are not
published.

To reproduce after an explicit paid-run opt-in, follow the root README to prepare
and start the API, then replay each file's user turns using `/api/chat` and the same
selection/session rules. For SDK evidence in a local script, wrap each request in
its own `capture_run_messages()` context and inspect ToolCallPart/ToolReturnPart;
see [the SDK documentation](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/#pydantic_ai.agent.capture_run_messages).
The historical catalog-only `agent.examples` recorder was subsequently retired;
replay through HTTP to exercise persisted order/guest conversations. No new
recorder framework or production dependency was added.

## Automated evidence and limits

The existing 246 offline tests, Ruff lint/format, strict mypy (71 source/test files)
and source/wheel builds pass from the repository root. Offline tests prohibit real
model calls. Relevant reusable checks include:

- [Guest sessions and selection](../../../apps/backend/tests/test_guest_demo.py): mode/customer matching, restart continuity, unknown customers, order guards.
- [Order integration](../../../apps/backend/tests/test_order_api.py): scoped results, forged arguments, refreshed snapshots, independent customers and storage failures.
- [Promotion integration](../../../apps/backend/tests/test_promotion_api.py): guest/customer follow-ups, exact non-stacking quotes and failed-turn integrity.
- [Persistence failures](../../../apps/backend/tests/test_persistent_chat.py), [safe HTTP errors](../../../apps/backend/tests/test_api.py) and [diagnostics](../../../apps/backend/tests/test_pipeline_logging.py).

The instruction changes were motivated by observed real failures; controlled
models cannot prove real tool selection. No prompt-text assertions or duplicate
security/concurrency matrix was added. Codex reviewed these traces; no independent
human review or hosted-CI pass is claimed. The catalog example predates the focused
instruction correction; it is labeled with its actual baseline, not recaptured on
the corrected prompt. Prices and order states remain supplied snapshots. Price
notices repeat some model prose, and natural-language behavior can vary. Policy
answers, live inventory/carriers and production identity are outside this evidence.
