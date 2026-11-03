# ADR-0001: Modular monolith and dependency boundaries

Status: Accepted

Related issue: [US-02 #3](https://github.com/rafaself/atf-ai-engineer-challenge/issues/3)

## Context

The first sprint needs a product-support agent that can later run behind HTTP or another consumer. Catalog retrieval and model execution must be replaceable in tests, without starting a server, creating a database, or resolving AWS credentials. The foundation currently has one Python package; distributed services and a broad abstraction framework would add work without supporting this small slice.

## Decision

Keep one deployable Python package with these responsibilities:

| Module | Responsibility | Current status |
| --- | --- | --- |
| `contracts` | Validated chat/catalog values and transport-neutral errors | Implemented |
| `ports` | Agent execution and product retrieval protocols | Implemented |
| `application` | ChatService orchestration and entry-point protocol | Implemented (US-06) |
| API | Translate HTTP input/output and errors; composition root | Implemented (US-07) |
| Agent | Prompts, tool registration, SDK execution translation | Implemented (US-04/US-05); live validation deferred |
| Infrastructure | SQLite import/retrieval (provider factory belongs to Agent) | Implemented (US-03) |

Contracts depend only on Python and Pydantic 2. Ports depend on contracts, and the application may depend on contracts and ports. Future adapters depend inward; neither provider-specific model objects nor FastAPI objects belong in these interfaces. The API composition root constructs adapters and injects dependencies. No service locator, generic repository framework, or custom DI container is introduced.

Pydantic validates the shared values directly. This adds a deliberate dependency at the core, avoids parallel dataclass/validation representations, and supports future API/tool schemas. Models are frozen and forbid unknown inputs. Product collections use tuples so nested results are also immutable. `available` and `truncated` are derived output fields, never independent input flags. Exclude computed fields when constructing input from serialized output.

Money crosses the core boundary as integer centavos. Future CSV/tool adapters convert BRL amounts exactly; no float conversion or currency arithmetic is added here. The repository owns normalized filtering, inclusive bounds, availability, stable price/product-ID ordering, counts before limiting, and bounded results. Unknown filters return no matches. Partial names can return multiple matches.

Agent execution and ChatService are asynchronous to fit later network calls. The small SQLite repository port is synchronous. The future API/composition layer must choose an appropriate execution path for synchronous database work without sharing unsafe cross-thread connections.

Validation raises Pydantic ValidationError. Adapters translate operational faults to ConfigurationError, ProviderUnavailableError, AgentTimeoutError, ProductRetrievalError, or AgentExecutionError, preserving causes internally. HTTP mappings and concrete orchestration were subsequently implemented in US-06/US-07. A zero-match result is successful data, not a retrieval failure.

## Consequences

Typed fakes can replace real providers and repositories without inheritance or runtime protocol registration. Protocols are checked structurally by strict mypy; they do not execute workflows or enforce repository filtering themselves.

US-02 implements no concrete ChatService, persistence, provider factory, or server. The search semantics documented here become adapter acceptance criteria in later stories. The application is independent of HTTP/provider SDKs but intentionally depends on Pydantic; replacing that library would require changing the contracts.

The decision is accepted after offline contract tests, isolated import tests, dependency-direction checks, and strict mypy validation of independent fakes pass. Future changes to these boundaries require updating this ADR or superseding it.

US-08 status update: the table reflects the implemented slice. The original US-02 contract decision remains accepted; implementation evidence is in the story PRs.
