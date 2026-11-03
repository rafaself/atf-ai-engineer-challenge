# Documentation map

Start with the [root README](../README.md) for setup, the evaluator path and
links into the current application. The guides below describe current behavior;
dated benchmark reports and ADRs preserve evidence for their recorded revisions.
Check their stated limits before applying results to the current checkout.

## Run and understand the current application

- [Root README](../README.md): recommended Docker setup, model configuration, checks and entry points.
- [Architecture](architecture.md): implemented boundaries, storage and runtime behavior.
- [Local API](guides/api.md): startup, curl, dependency injection and HTTP failures.
- [Interactive CLI](guides/cli.md): direct local conversations without an HTTP server.
- [Catalog](guides/catalog.md): validation, atomic replacement, snapshot and search semantics.
- [Orders](guides/orders.md): import, fictional provenance, customer scoping and snapshot limits.
- [Bedrock](guides/bedrock.md): configuration, request limits and opt-in provider probe.
- [Policy corpus and retrieval](guides/policy-retrieval.md): provenance, runtime setup,
  retrieval behavior and measured limits.
- [Data processing](guides/data-processing.md): source handling, derived policy evidence
  and simulation semantics.

## Evaluation evidence

- [Final Bedrock Runtime model comparison](benchmarks/final-model-comparison/README.md):
  ten-model capture, assessments, cost and execution limits.
- [RAG versus embedded policies](benchmarks/policy-context-ab-78/README.md):
  Luna A/B capture, cost, retrieval diagnostics and pending human review.

## Decisions and delivery history

- [ADRs](adr/README.md): accepted architecture and provider decisions.
