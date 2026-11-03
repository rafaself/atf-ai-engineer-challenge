# Documentation map

Start with the [root README](../README.md). Architecture and API guides describe
the current demo. ADRs, validation logs and live captures preserve historical
evidence; issue #32 retires their cross-instance coordination/provenance details.
Issue #33 replaces token identity with guests and direct fictional-customer selection.

- [Root README](../README.md): installation, import and quality commands.
- [Architecture](architecture.md): implemented boundaries and retrieval/prompt rationale.
- [Catalog](catalog.md): validation, atomic replacement, snapshot and search semantics.
- [Orders](orders.md): required import, fictional provenance, customer scoping and snapshot limits.
- [Bedrock](bedrock.md): explicit configuration, limits and opt-in live probe.
- [Local API](api.md): startup, curl, dependency injection and HTTP failures.
- [Interactive CLI](cli.md): direct local conversations without an HTTP server.
- [ADRs](adr/README.md): accepted architecture/provider boundaries.
- [Validation](validation.md): reproducibility results and remaining live checks.
- [Sprint 4 validation](sprint-4-validation.md): final package checks, runtime evidence and limits.
- [Examples](examples/README.md): reviewed real conversations, failures and replay guidance.
- [Sprint 3](sprint-3.md): integration branch, story sequence and approved scope.
- [Follow-up](follow-up.md): policy routing and final submission requirements.
- [Policy corpus and retrieval](policy-retrieval.md): provenance, runtime setup,
  evaluation and measured limitations.
- [Data processing decisions](data-processing.md): existing transformations,
  planned canonical policy evidence, simulation semantics, and their justification.

- [US-15 benchmark](benchmarks/README.md): opt-in setup, methodology, local hardware and provider access.
- [Retrieval results](benchmarks/results.md): frozen-metric comparison and observed failures.
