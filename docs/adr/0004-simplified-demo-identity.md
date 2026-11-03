# ADR-0004: Fixed demo identity

Status: Accepted

Related issue: [#87](https://github.com/rafaself/atf-ai-engineer-challenge/issues/87)

## Context

Order tools need a fixed, trusted customer scope for the local fictional demo. Production authentication is outside the project scope.

## Decision

Use imported fictional customer ID 1 for HTTP, React chat, and CLI. Validate it against the current operational snapshot on each incoming turn and fail safely if it is missing. Carry identity in server-created ExecutionContext, never in the client request, model prompt, or tool arguments. Reject ownerless sessions and sessions owned by another customer. Scope order, item, count, and tracking-code queries in SQL.

## Consequences

Every demo user sees the same fictional account. This is not authentication; run with fictional data on loopback, not as a public service.
