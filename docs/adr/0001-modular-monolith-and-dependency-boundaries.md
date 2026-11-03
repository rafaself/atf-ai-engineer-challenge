# ADR-0001: Modular monolith and dependency boundaries

Status: Accepted

Related issue: [#3](https://github.com/rafaself/atf-ai-engineer-challenge/issues/3)

## Context

The local demo needs HTTP and CLI entry points that share agent behavior without coupling the core to either transport, the model provider, or storage.

## Decision

Keep a modular monolith with the API, CLI, and React frontend under apps/ and shared agent logic in packages/emporio_music. Keep domain and application code independent of transport, provider, and storage frameworks; define boundaries with focused ports and wire implementations in composition. Use direct imports from defining modules. Do not add a generic DI or repository framework, distributed services, or extra deployment layers without a concrete need.

## Consequences

The API, CLI, and tests reuse the same application and agent logic. Changes to these boundaries require a demonstrated project need.
