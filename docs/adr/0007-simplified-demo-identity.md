# ADR-0007: Fixed demo identity for local evaluation

> Historical storage note: this decision originally used a fixed project-root
> path. Issue #76 now selects source and runtime data through
> `EMPORIO_MUSIC_DATA_DIR`; see [current architecture](../architecture.md).
> Stop the server and move an older history database aside before creating its
> replacement; earlier configurable-path guidance below is historical.

Status: Accepted — updated for issue #87 on 2026-11-03.

Related: [#33](https://github.com/rafaself/atf-ai-engineer-challenge/issues/33),
[#87](https://github.com/rafaself/atf-ai-engineer-challenge/issues/87).

## Context

Earlier ADRs proposed mandatory customer sessions and bearer-token mapping. Issue
#33 removed those mechanisms as disproportionate for a local challenge with finite
fictional data and temporarily used optional customer selection. Issue #87
supersedes that selector for the demo: all public demo entry points now share one
fixed fictional customer. LLM integration, factual tools, conversation context and
UX remain the evaluation focus.

## Decision

Use fixed imported customer ID `1` for HTTP, React chat and CLI. Shared composition
resolves the identity server-side and validates it against the current operational
snapshot for each incoming turn. A missing fixed customer is a configuration
failure. `ChatRequest` has no `customer_id` field; clients that send the removed
field receive 422. Immutable `ExecutionContext` carries the fixed scope separately
from model messages. The model has no customer-selection tool argument.

Keep the existing history schema and owner checks. New demo sessions are owned by
customer `1`; sessions owned by a guest or another customer fail the same inaccessible
session response as an unknown ID. Do not reassign their conversation history.
Conversation schema v2 still represents null owners so pre-existing guest rows can
be rejected without a migration or rewrite. Keep bounded complete pairs,
transactions, same-session overlap protection, deadlines, cancellation and safe
diagnostics. Order tools use per-run identity, and repositories enforce owner scope
in SQL. Tracking lookup binds customer ID and exact tracking code in the same query.

The chosen fictional customer owns order `4` with tracking code `BRQM7890123BR`,
providing a reproducible tracking demonstration. Catalog and order source bytes
remain unchanged. No tokens, dynamic identity configuration, authentication
replacement or production dependencies are added.

## Consequences

This is a fixed fictional demo identity, **not authentication**. Every local demo
user sees the same fictional customer account; session IDs are not user credentials.
Anyone who obtains a session ID can continue that session. Run on loopback with
fictional data, not a public service with real customer information. The React
client sends no identity field, and the CLI has no identity selector. No dynamic
customer switching, JWT/OAuth or distributed identity is provided.

The old optional-selector behavior recorded earlier in #33 is superseded by this
decision. App-owned context, history integrity, customer-scoped reads and the
historical rationale remain valid. Controlled models and temporary SQLite verify
the implementation; live model answer quality remains opt-in.
