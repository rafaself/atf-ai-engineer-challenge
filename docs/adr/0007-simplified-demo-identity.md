# ADR-0007: Simplified demo identity for local evaluation

> Storage update: paths are now fixed under PROJECT_ROOT/data. Stop the server
> and move an older history database aside before creating its replacement;
> earlier configurable-path guidance below is historical.

Status: Accepted — reviewed and verified offline on 2026-11-01.

Related: [#33](https://github.com/rafaself/atf-ai-engineer-challenge/issues/33).

## Context

ADR-0003/0004/0005 followed the earlier approved requirements: trusted execution
context, mandatory customer sessions, server-configured bearer mapping and scoped
orders. The owner's later review of the planning/code concluded that token setup,
hashing/comparison and resolver plumbing were disproportionate for a local challenge
with finite fictional data. This is a scope correction, not an implementation bug.
LLM integration, factual tools, conversation context and UX are the evaluation focus.

## Decision

Use optional customer selection at the HTTP boundary. Omitted/null customer_id is
guest mode. A non-null ID is a strict positive SQLite-sized integer and must exist
in the current imported registry on each selected request. HTTP-only selection is
removed from ChatRequest; immutable ExecutionContext carries scope separately from
model messages. Remove tokens, mapping configuration, resolver protocols and dead
configuration paths; add no authentication replacement or production dependencies.

Reuse the existing history store with an optional customer owner: null is guest.
Session reads and complete-turn writes compare customer/null explicitly. Customer
or mode changes require a new session. Keep bounded complete pairs, transactions,
same-session overlap protection, deadlines, cancellation and safe diagnostics.
Guest order tools return a selection-required message before querying the repository.
Selected tools retain per-run dependencies and parameterized customer-scoped SQL.
Chat text and model arguments cannot change the selected customer.

Conversation schema v2 allows nullable owners. Reject v1 unchanged; configure a
fresh path and retain the old file. No automatic deletion, migration or compatibility
path is needed for this development-stage demo. Catalog/order sources remain unchanged.

## Consequences

This is local fictional demo selection, **not authentication**. Any demo user can
select any existing customer. Guest IDs permit continuation by possession and do
not distinguish individual people; no protection against another demo user choosing
the same customer is claimed. Run on loopback with fictional data, not a public
service with real customer information. No frontend, distributed guest identity,
JWT/OAuth, policy retrieval or paid model evaluation is included.

Tokens and the no-guest choice in ADR-0003/0004/0005 are superseded by this
decision. App-owned context, history integrity, customer-scoped reads and the
historical rationale/evidence remain valid. Controlled models and real temporary
SQLite verify the implementation; fresh live model quality remains US-13.
