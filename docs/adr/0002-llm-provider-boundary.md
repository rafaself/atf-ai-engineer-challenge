# ADR-0002: LLM provider boundary

Status: Accepted

Related issue: [#5](https://github.com/rafaself/atf-ai-engineer-challenge/issues/5)

## Context

The runtime uses Bedrock, while application orchestration and offline tests must remain independent of AWS and Pydantic AI.

## Decision

Construct the Bedrock client only through the explicit agent factory. The Pydantic AI adapter implements the agent port and accepts an injected model for offline use. Bound calls with a 5-second connection timeout, a configurable read timeout defaulting to 15 seconds, and one SDK attempt. Default to six model requests, five tool calls, and 1,024 output tokens; these limits are configurable. Disable tool retries and allow one output correction. Reject blank or internal-markup answers; derive factual notices only from the current run’s tool results.

## Consequences

The application can use injected models without AWS setup, and provider failures map to application errors. Offline wiring checks do not prove live tool selection or answer grounding; those require conversation review.
