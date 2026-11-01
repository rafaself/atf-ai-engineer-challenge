# Architecture decisions

Use sequential four-digit numbers and descriptive English filenames. Each ADR
records **Context**, **Decision**, and **Consequences**, plus its status and related
issue. Status is `Proposed`, `Accepted`, or `Superseded`. Accept a decision only
after implementation evidence validates it; reference the successor when superseded.

Record significant boundaries and tradeoffs rather than trivial implementation
choices. Keep numbering stable. Link decisions from the corresponding story.

- [ADR-0001: Modular monolith and dependency boundaries](0001-modular-monolith-and-dependency-boundaries.md)

- [ADR-0002: LLM provider boundary](0002-llm-provider-boundary.md) records the
  adapter boundary and bounded customer-output policy, with Sprint 1 live evidence.
- [ADR-0003: Owned conversation execution context](0003-owned-conversation-execution-context.md)
  records trusted identity/session/history contracts, direct execution, and the
  US-10 persistence/identity-resolution handoff.
- [ADR-0004: Persistent conversation turns](0004-persistent-conversation-turns.md)
  records demo identity, SQLite ownership, bounded history, commit/cancellation,
  concurrency, diagnostics, and API behavior.
- [ADR-0005: Authorized operational snapshots](0005-authorized-operational-snapshots.md)
  records minimal operational import, trusted per-run scope, token validation,
  bounded order tools, snapshot limitations and safe diagnostics.
- [ADR-0006: Immutable promotion sources and exact pricing](0006-immutable-promotion-pricing.md)
  records unchanged promotion data, atomic catalog ingestion, exact non-stacking
  pricing, payable-price filtering and the offline/live evidence boundary.

- [ADR-0007: Simplified demo identity for local evaluation](0007-simplified-demo-identity.md)
  accepts guest sessions and direct fictional-customer selection, superseding
  token authentication and mandatory customer ownership in ADR-0003/0004/0005.
