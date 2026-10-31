# Agent configuration and Bedrock validation

The agent factory uses Pydantic AI 2.64.0 with boto3 1.43.123. Preferred model:
amazon.nova-micro-v1:0 in us-east-1. **Live access/tool calling is unverified**:
the user deferred AWS profile confirmation. No Towelbooks profile is selected.

Configure a project profile through the usual AWS CLI/SSO flow, then export:

```bash
export AWS_PROFILE=your-project-profile
export AWS_DEFAULT_REGION=us-east-1
export BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
```

Do not send or commit keys. The environment example is documentation, not a dotenv
loader. Omit AWS_PROFILE to use the standard default credential chain intentionally.
AgentSettings.from_environment reads only configuration, not credentials. Invalid
configuration produces ConfigurationError. Provider construction is explicit.

The opt-in probe incurs real model requests:

```bash
uv run --project backend --locked python -m emporio_music_backend.agent.smoke --live
```

It must observe a fresh verification tool call/result and that code in the final
answer before printing JSON evidence with model, region, SDK versions, arguments,
result, answer, and request count. A text-only response is not accepted as proof.
Save verified output only after it succeeds. Re-run it with another low-cost feasible
model if Nova Micro is unavailable, documenting the reason. Never replace live
evidence with a fake; the current status is deferred, not passed.

Defaults: max 5 requests, 5 tool calls, 1024 output tokens per response, 15-second
request/read timeout, 5-second connection timeout, one total SDK attempt, no agent
validation retries. Tune AGENT_MAX_REQUESTS, AGENT_MAX_TOOL_CALLS,
AGENT_MAX_OUTPUT_TOKENS, and AGENT_REQUEST_TIMEOUT_SECONDS as needed. These bounds
limit work, not a guaranteed monetary budget. ChatService owns the overall deadline.

Offline checks use controlled Pydantic AI models and forbid real model requests;
credentials are not needed. In the Codex restricted sandbox SDK worker-thread tests
stalled; the same offline suite runs outside that sandbox with the model-call guard
still enabled. No network/model request is needed for those checks.

## Product search (US-05)

`agent.catalog.create_catalog_agent(settings, repository, model=...)` registers
`search_products` against any ProductRepository. The optional model argument is
for alternate providers or controlled tests; omit it for the configured Bedrock model.

Tool filters are category, partial product_name, inclusive min_price_brl and
max_price_brl (reais, not centavos), available_only, and limit (1–20). Prices must
be finite, nonnegative, and have exact cents within the SQLite range. Conversion
is independent of the caller's Decimal precision. Boolean limits and nonboolean
availability flags are rejected at the SDK boundary.

The tool delegates filtering and ordering to the repository and returns product
IDs, names, category information, status, stock, availability, integer-centavo
prices and exact two-decimal price_brl strings, total_matches and truncated. It
also identifies catalog pricing and imported-snapshot inventory. Operational
retrieval errors propagate; they do not become zero results or invented answers.
The persona instructs the model to disclose truncation and consult the tool first.

Controlled-model tests verify registration, arguments, results and failures against
the real temporary SQLite catalog. They do not establish live Nova tool selection
or answer quality; those checks remain deferred pending AWS profile confirmation.

## Conversation orchestration (US-06)

`application.ChatService(agent, timeout_seconds=60)` accepts the transport-neutral
AgentExecutor port and exposes async chat(ChatRequest) -> ChatResponse. The
structural interface is ChatServicePort. Request validation occurs before invoking
the agent. The service preserves typed configuration, provider, retrieval, and
agent errors, sanitizes unexpected execution failures while preserving their cause,
and translates the overall deadline into AgentTimeoutError. Caller cancellation
propagates. It adds no retries, session state, database, HTTP, or provider initialization.
Individual model request limits/timeouts belong to the adapter; the service owns
one deadline for the complete conversation, including tool execution.
