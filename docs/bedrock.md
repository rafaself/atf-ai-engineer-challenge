# Agent configuration and Bedrock validation

The agent factory uses Pydantic AI 2.64.0 with boto3 1.43.123. The default is
`qwen.qwen3-32b-v1:0` in `us-east-1`. Three [closing conversations](examples/sprint-2/closure/README.md)
passed review on the final application code. Nova Micro/Lite produced incorrect
PIX answers in the bounded comparison, so they were not retained as the default.
Historical probes/captures remain available; no model is claimed universally correct.

The supplied [IAM policy reference](aws/bedrock-invoke-policy.json) lists five model
ARNs, including Qwen. It is preserved as supplied, not applied by the repository.
Only Qwen, Nova Micro and Nova Lite have observed project runs; the other listed
models' availability/quality is not established. No extra permissions were added.

Use a configured profile (including SSO), or the access-key option in .env.example.
For profile authentication, export:

```bash
export AWS_PROFILE=your-project-profile
export AWS_DEFAULT_REGION=us-east-1
export BEDROCK_MODEL_ID=qwen.qwen3-32b-v1:0
```

Do not send or commit keys. The environment example is documentation, not a dotenv
loader. Omit AWS_PROFILE to use the standard default credential chain intentionally.
`AgentSettings` uses Pydantic Settings to read and validate configuration from the
environment. `AWS_DEFAULT_REGION` takes precedence over `AWS_REGION`; explicit
constructor values override environment values. `load_agent_settings()` translates
invalid configuration into a sanitized `ConfigurationError`. Credentials remain
in boto3's default credential chain, and provider construction is explicit.

The opt-in probe incurs real model requests:

```bash
uv run --env-file .env --project apps/backend --locked python -m emporio_music_backend.agent.smoke --live
```

It must observe a fresh verification tool call/result and that code in the final
answer before printing JSON evidence with model, `aws_region`, SDK versions, arguments,
result, answer, and request count. A text-only response is not accepted as proof.
Save verified output only after it succeeds. Re-run it with another low-cost feasible
model if the configured model is unavailable, documenting the reason. Never replace live
evidence with a fake. A passing capture establishes that execution, not all behavior.

Defaults: max 5 requests, 5 tool calls, 1024 output tokens per response, 15-second
request/read timeout, 5-second connection timeout, one total SDK attempt, zero tool
validation retries and at most one corrective output retry. Tune AGENT_MAX_REQUESTS, AGENT_MAX_TOOL_CALLS,
AGENT_MAX_OUTPUT_TOKENS, and AGENT_REQUEST_TIMEOUT_SECONDS as needed. These bounds
limit work, not a guaranteed monetary budget. ChatService owns the overall deadline.

Offline checks use controlled Pydantic AI models and forbid real model requests;
credentials are not needed. In the Codex restricted sandbox SDK worker-thread tests
stalled; the same offline suite runs outside that sandbox with the model-call guard
still enabled. No network/model request is needed for those checks.

## Product search (US-05)

`agent.catalog.create_catalog_agent(settings, repository, model=...)` registers
`search_available_products` and `get_product_details` against any ProductRepository. The optional model argument is
for alternate providers or controlled tests; omit it for the configured Bedrock model.
This factory remains an isolated catalog probe. HTTP uses
`agent.orders.create_store_agent(settings, products, orders)`, sharing those same
product tools and adding `list_my_orders`/`get_my_order`; it requires operational
storage and a valid selected fictional customer for orders. Guests may use catalog
tools. See [orders](orders.md).

Recommendation filters are category, partial product_name, inclusive min_price_brl
and max_price_brl (reais, not centavos), and limit (1–20). Recommendations always
use active/positive-stock availability. get_product_details requires product_name
and accepts limit; it includes all statuses/stock levels for named inspection. Prices must
be finite, nonnegative, and have exact cents within the SQLite range. Conversion
is independent of the caller's Decimal precision. Boolean limits are rejected at the SDK boundary. Availability is owned by each
tool rather than exposed as a model-controlled flag.

The tool delegates filtering and ordering to the repository and returns product
IDs, names, category information, status, stock, availability, integer-centavo
prices and exact two-decimal price_brl strings, total_matches and truncated. It
also identifies computed snapshot pricing and imported-snapshot inventory. Operational
retrieval errors propagate; they do not become zero results or invented answers.
The persona requires retrieval before facts. Output validation appends a selection
notice from actual per-run truncated results, independent of model wording. Known
internal/control markup is rejected with one corrective retry, never silently stripped.

Controlled-model tests verify registration, arguments, results and failures against
the real temporary SQLite catalog. They do not establish live tool selection
or answer quality; the separate reviewed live captures provide scenario evidence.

US-12 extends both product tools with `payment_method="standard"|"pix"` and
search with `promotions_only`. Original prices remain in `price_centavos/price_brl`;
typed `pricing` supplies the exact final price, applied percentage and offer source.
Budget filters use payable prices. The model presents returned price details once;
the application adds a concise snapshot notice for current-run discounted products.
An explicit `R$` amount absent from current-run quotes/totals, search bounds and
customer messages triggers the existing output retry; exhaustion fails safely.
Customer amounts can be echoed as context, not used as confirmed tool prices.
The correction request combines formatting and price feedback and asks for retrieval
when facts are missing. This is numeric checking, not proof of correct price labels
or complete grounding. See the [closing review](examples/sprint-2/closure/README.md).
Re-import the generated catalog with `--promotions` before use;
see [pricing rules and source limits](catalog.md). The Sprint 2 evidence includes
a real non-stacking PIX follow-up and preserves its earlier failed attempt.
Further provider evaluation remains opt-in.

## Conversation orchestration (US-06–US-10)

`application.chat.ChatService(agent, conversation_repository, timeout_seconds=60)`
requires an AgentExecutor and a ConversationRepository. The public async
`chat(request, *, context: ExecutionContext)` entry point receives resolved
identity only, loads owned bounded history, and commits the completed turn before
returning ChatResponse with a session ID. The structural interface remains
`ports.chat.ChatServicePort`; HTTP and provider objects do not enter the application layer.

AgentExecutor.run also requires context, but returns AgentResponse without a
persistence claim. The adapter translates application-owned user/assistant text
into fresh SDK messages. Identity/session metadata and old tool returns are not
sent as messages. ExecutionContext is passed as per-run SDK dependencies; order
tools derive customer scope there. SDK direct calls require `deps=ExecutionContext()`
for stateless probes, or a trusted owned context for order execution. Current-run message IDs select the output validator's tool evidence, so
historical results cannot add new selection notices; corrective retries are still
included. The service preserves typed errors, timeout, and caller cancellation.
No persistence write runs in a background worker after cancellation. The short
SQLite commit cannot be interrupted asynchronously; the current single-process
and response-loss limits are in [architecture](architecture.md).

Guests use empty identity context and can persist catalog conversations. Non-null
HTTP customer selection is registry-validated before session/model access; it is
local fictional selection, not authentication. SDK dependencies carry selected
scope separately from model messages. The smoke module remains an independent
provider probe; the historical catalog-only recorder is retired. US-13's reviewed
conversations used the full HTTP composition and persisted sessions; see
[the evidence index](examples/sprint-2/README.md)
and [API setup](api.md). Store-policy retrieval/evaluation belongs to the later
retrieval sprint and is not part of Sprint 2 acceptance.

For access keys in .env, remove AWS_PROFILE from the file and unset profile
selection in the shell; include AWS_SESSION_TOKEN for temporary credentials. The
application does not load .env; uv --env-file does. Existing shell variables take
precedence. Tests cleared profile selection only in their own processes.
