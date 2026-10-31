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
limit work, not a guaranteed monetary budget. The application deadline comes in US-06.

Offline checks use controlled Pydantic AI models and forbid real model requests;
credentials are not needed. In the Codex restricted sandbox SDK worker-thread tests
stalled; the same offline suite runs outside that sandbox with the model-call guard
still enabled. No network/model request is needed for those checks.
