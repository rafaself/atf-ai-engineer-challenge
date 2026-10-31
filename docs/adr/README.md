# Architecture decisions

Use sequential four-digit numbers and descriptive English filenames. Each ADR
records **Context**, **Decision**, and **Consequences**, plus its status and related
issue. Status is `Proposed`, `Accepted`, or `Superseded`. Accept a decision only
after implementation evidence validates it; reference the successor when superseded.

Record significant boundaries and tradeoffs rather than trivial implementation
choices. Keep numbering stable. Link decisions from the corresponding story.

- [ADR-0001: Modular monolith and dependency boundaries](0001-modular-monolith-and-dependency-boundaries.md)

- [ADR-0002: LLM provider boundary](0002-llm-provider-boundary.md) records the
  offline-validated adapter boundary; live model compatibility remains deferred.
