# Documentation map

Start with the [root README](../README.md) for setup, the evaluator path and links into the current application. Guides describe current behavior, ADRs record decisions still in force, and dated evaluation reports retain revision-specific evidence with their stated limits.

## Run and understand the current application

- [Root README](../README.md): recommended Docker setup, model configuration, checks and entry points.
- [Architecture](architecture.md): implemented boundaries, storage and runtime behavior.
- [Local API](guides/api.md): startup, curl, dependency injection and HTTP failures.
- [Interactive CLI](guides/cli.md): direct local conversations without an HTTP server.
- [Catalog](guides/catalog.md): validation, atomic replacement, snapshot and search semantics.
- [Orders](guides/orders.md): import, fictional provenance, customer scoping and snapshot limits.
- [Bedrock](guides/bedrock.md): configuration, request limits and opt-in provider probe.
- [Policy corpus and retrieval](guides/policy-retrieval.md): provenance, runtime setup, retrieval behavior and measured limits.
- [Data processing](guides/data-processing.md): source handling, derived policy evidence and simulation semantics.

## Evaluation records

- [Final Bedrock Runtime model selection](evaluations/model-selection/README.md): ten-model capture, assessments, cost and execution limits.
- [Policy-context comparison](evaluations/policy-context/README.md): Luna A/B capture, cost, retrieval diagnostics and pending human review.

## Architecture decisions

- [ADRs](adr/README.md): accepted architecture and provider decisions.
