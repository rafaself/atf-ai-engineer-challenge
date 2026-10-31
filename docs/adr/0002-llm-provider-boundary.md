# ADR-0002: LLM provider boundary

Status: Accepted (adapter boundary and bounded customer-output policy)

Related issue: US-04 #5

## Context

The application must execute a stateless store conversation without depending on
AWS or the agent SDK. The initial low-cost preference is Nova Micro in us-east-1.
Initial live checks were deferred. After key activation, the tool probe and HTTP
lookup succeeded, while live scenarios exposed ambiguous availability selection,
missing truncation disclosure and internal/control markup in final answers.

## Decision

Use Pydantic AI's Bedrock-only package and one explicit create_agent factory.
PydanticAgentExecutor implements AgentExecutor, translating SDK results/errors
into ChatResponse and transport-neutral failures. The core imports no agent SDK.
Tests and alternate providers can supply a Model directly, bypassing AWS setup.
No SDK client is created by module import. Standard AWS credentials/profile
resolution happens only when explicitly constructing the Bedrock agent.

Use boto3 directly to bound connections (5 seconds), reads (15 seconds by default),
and total SDK attempts (one). Tool validation retries are zero. Output validation permits one corrective retry,
within the existing request/tool limits and ChatService deadline. Request, tool-call,
and per-response output-token limits are configurable. Request timeout is also
passed to Pydantic AI. ChatService owns the end-to-end conversation deadline (US-06).

Portuguese instructions require grounded catalog facts and polite redirection for
accessories, unsupported policies/orders, and unrelated questions. No price/stock
facts are embedded in the prompt. Tools remain outside the provider factory.

## Consequences

Offline tests prove tool round trips, statelessness, request limits, failure mapping,
and configuration handling with controlled models. Default tests forbid real model
requests. They do not establish Nova Micro's availability, natural-language tool
selection, or answer quality. The opt-in smoke module verifies an actual fresh-code
tool invocation/result/final-answer chain when a real profile is configured.

The SDK/boto3 dependencies are isolated, with targeted missing-stub import annotations.
Changing providers requires a different Model construction, not an application rewrite.
Live Nova Micro evidence is stored under docs/examples/: original failures in
live/, a passing fresh-code probe, and reviewed remediation runs in live-recheck/.

## Live-evidence revision — 2026-10-31

Keep customer-output policy in the agent adapter, outside transport-neutral core
contracts. Reject known internal/control markup or blank output with a constant
corrective instruction; do not strip tags and accidentally return the internal
text. Permit one output retry, then map failure to AgentExecutionError. SDK/network
retries and request/tool budgets remain independent bounds.

Expose two narrow tools: search_available_products always requires active positive
stock; get_product_details always includes unavailable named products. Both reuse
the same repository and integer-centavo contracts. The model no longer chooses an
availability flag. This intentionally replaces the ambiguous previous tool API;
no compatibility alias is retained in this preproduction project.

For actual truncated catalog results in the current run, append a deterministic
Portuguese partial-selection notice using returned total matches. Store no shared
mutable result metadata on the cached executor; per-run SDK context provides the
facts. This adds no extra model request and does not rely on prose matching.

The markup check is a targeted presentation guard, not a semantic grounding or
prompt-injection guarantee. Tool choice and factual wording still require live
evaluation. Original failures remain unchanged; passing reruns do not prove all
future model outputs are correct. No additional service, dependency or public HTTP
contract is introduced; this revision extends the existing accepted boundary.

## US-09 execution-context extension

AgentExecutor.run now requires an explicit application-owned ExecutionContext.
The adapter revalidates it and translates only completed user/assistant text pairs
into a fresh SDK history list. It does not send identity/session metadata or replay
historical tool calls/returns. Current-run tool returns still drive output notices.
Empty context retains stateless execution; HTTP supplies it until US-10. See
[ADR-0003](0003-owned-conversation-execution-context.md) for ownership, trust,
scope, and offline evidence. No new multi-turn Bedrock validation is claimed here.
