# Documentation map

Start with the [root README](../README.md) for setup, the evaluator path and
links into the current application. The guides below describe current behavior;
dated validation reports, ADRs and conversation captures preserve evidence for
their recorded revisions. Check their stated limits before applying results to
the current checkout.

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

## Validation and evaluation evidence

- [Validation record](validation.md): current output behavior followed by
  revision-specific implementation checks.
- [Sprint 4 validation](archive/sprints/sprint-4-validation.md): recorded package checks, runtime
  evidence and environment limits for that delivery.
- [Representative conversations and evaluation index](examples/README.md):
  curated transcripts, failures and replay guidance.
- [Bedrock model comparisons](examples/model-comparison/README.md): dated,
  manually reviewed live runs and their source-revision/cost limits.
- [Policy retrieval benchmark](benchmarks/README.md): opt-in setup, methodology,
  local hardware and provider access.
- [Retrieval results](benchmarks/results.md): frozen-metric comparison and observed failures.

## Decisions and delivery history

- [ADRs](adr/README.md): accepted architecture and provider decisions.
- [Sprint 3](archive/sprints/sprint-3.md): integration branch, story sequence and approved scope.
- [Follow-up](follow-up.md): policy routing and submission-related notes.
