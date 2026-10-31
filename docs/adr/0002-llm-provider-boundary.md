# ADR-0002: LLM provider boundary

Status: Accepted (adapter boundary); live model compatibility remains unverified

Related issue: US-04 #5

## Context

The application must execute a stateless store conversation without depending on
AWS or the agent SDK. The initial low-cost preference is Nova Micro in us-east-1.
The user has deferred AWS profile confirmation and all live Bedrock evidence.

## Decision

Use Pydantic AI's Bedrock-only package and one explicit create_agent factory.
PydanticAgentExecutor implements AgentExecutor, translating SDK results/errors
into ChatResponse and transport-neutral failures. The core imports no agent SDK.
Tests and alternate providers can supply a Model directly, bypassing AWS setup.
No SDK client is created by module import. Standard AWS credentials/profile
resolution happens only when explicitly constructing the Bedrock agent.

Use boto3 directly to bound connections (5 seconds), reads (15 seconds by default),
and total SDK attempts (one). Agent validation retries are zero. Request, tool-call,
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
Live model validation is explicitly deferred by the user; no live success is claimed.
