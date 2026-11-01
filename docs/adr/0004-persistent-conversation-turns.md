# ADR-0004: Persistent conversation turns

> Identity update: [ADR-0007](0007-simplified-demo-identity.md), proposed in #33,
> replaces tokens and mandatory customer identity with local fictional selection
> and guest sessions. Context separation and customer-scoped reads remain.

Historical decision record. [Issue #32](https://github.com/rafaself/atf-ai-engineer-challenge/issues/32)
simplifies persistence and import infrastructure. Expected revisions, cross-instance
coordination, exact DDL checks and runtime source fingerprints described below are
retired where applicable. See the current [architecture](../architecture.md).

Status: Accepted (offline persistence, demo identity, and integration evidence)

Related issue: [US-10 #24](https://github.com/rafaself/atf-ai-engineer-challenge/issues/24)

## Context

US-09 established provider/transport-neutral identity, session, and text-history
contracts. US-10 must make them useful across HTTP requests and application
restarts, without allowing customers or models to choose another customer's
identity or silently overwrite a concurrent turn. The user approved server-side
demo token mappings, same-session conflict rejection, and separate conversation
storage. Production authentication, orders, and distributed infrastructure remain
outside this story.

## Decision

Use one owned writable SQLite file, separate from the replaceable catalog snapshot.
A schema/application marker rejects unrelated files rather than creating tables
inside them. New and existing owned files use mode 0600. Sessions contain a UUID4,
customer owner, and nonnegative revision. Each turn row contains both user and
assistant text and its sequence; row insertion and revision advancement are one
transaction. Schema migrations, ORM, and a generic repository framework are not
needed for this active-development local slice.

ConversationRepository offers create, owned bounded load, and expected-revision
append. Queries are parameterized. Load checks UUID and customer together before
reading any history, using one consistent read transaction. Unknown and foreign
sessions have the same safe error. Stale append revisions return conflict instead
of replacing a completed turn. Every operation opens/closes its own connection.
Catalog import never replaces conversation storage.

The HTTP adapter resolves bearer credentials using DEMO_CUSTOMER_TOKENS_JSON before
session/model access. Mapping keys are private URL-safe tokens (32–256 characters),
values strict positive customer IDs; empty/invalid/duplicate-key configuration fails
closed. The resolver retains token digests and compares them with constant-time
comparison. No default identity or anonymous persistent-session path exists. The
mapping is local demo identity only; US-11 will validate customer existence and add
order authorization. Credentials never become context fields or model arguments.

ChatService requires identity-only context and owns all history selection. A
request omitting session_id creates a session; an explicit valid UUID4 continues
only an owned existing session. Explicit null/malformed IDs fail validation. A
successful ChatResponse always includes answer and session_id. AgentExecutor
returns AgentResponse instead, so provider completion cannot claim a durable turn.
The adapter's explicit-history interface remains available for lower-level calls,
but ChatService rejects caller-supplied session/history instead of bypassing storage.

Keep all completed turns on disk until explicit local reset. Load the latest
contiguous suffix of complete pairs fitting both configurable limits: 6 turns and
24,000 characters by default, with maxima of 20 turns / 64,000 characters. Stop at
an oversized newer turn rather than skipping it and replaying older context.
The budget covers historical text, not total provider tokens. Product references
survive through retained answer text/order; there is no summarizer or vector memory.
The assistant must clarify references outside retained context, and instructions
still require new retrieval for mutable prices/stock. Offline wiring checks do
not prove that every live model answer follows those instructions.

Use a per-service set of active IDs on the single server event loop to reject
same-session overlap, releasing IDs in finally. Check ownership before consulting
active state. Versioned SQLite append remains the final lost-update guard across
service instances, without claiming distributed request scheduling. Serialize lazy
service construction so concurrent cache misses do not initialize duplicate services.

SQLite operations are synchronous and fail immediately on lock contention
(timeout=0). Keep transactions short and outside model work. Check cancellation
and the deadline after model validation and immediately before a non-awaiting
atomic append. This avoids the late background-thread write hazard after a timed
out/cancelled request. The local filesystem commit cannot be asynchronously
interrupted and can briefly block the loop; this is a deliberate local-demo tradeoff.
Other operational errors remain safe storage failures, not empty history.

Only complete successful turns are saved. Empty first-turn sessions may survive
failure without counting as completed turns. If append fails, do not return model
output as success. Once commit succeeds, losing the response does not undo the
turn; no exactly-once delivery, replay recovery API, or generalized retry deduplication
is promised. Stop the server before manually resetting the conversation file.

The provider adapter translates only user/assistant text, never identity/session
metadata or historical tool traces. Additionally, output validation accepts tool
returns only from messages stamped with the current SDK run ID, including output
retries. Diagnostics use per-event metadata allowlists, excluding raw conversation,
query, identity, credential, path, and tool-result contents. Validation errors do
not echo request inputs. No third-party debug logging is enabled.

## Consequences and validation

The public API changes deliberately: authenticated requests and session-aware
responses replace the earlier stateless HTTP shape without compatibility branches.
README/API/environment documentation describes token generation, limits, errors,
retention/reset, snapshot freshness, and response-loss limits. The supported setup
is one process/event loop on loopback. Multi-worker coordination, automatic expiry,
production auth, customer datasets, and order operations remain follow-up work.

Regression tests first reproduced unauthenticated execution, historical tool-result
notice reuse, and permissive permissions on a copied database. Real SQLite tests
cover restart, ownership, complete history limits, stale writes, and rollback after
an insert failure. Service tests cover overlap, independent progress, cancellation,
timeout, invalid output, storage failure/retry, and conflicting service instances.
An authenticated HTTP/controlled-model/SQLite scenario restarts the application,
uses a saved second-product reference, re-imports catalog data, retrieves a changed
price, rejects foreign/unknown sessions, and inspects diagnostics for private data.
Most new storage/service scenarios were added after their implementation; only the
three identified regressions have observed failing baselines. No live multi-turn
Bedrock evaluation is claimed; that remains explicitly opted in under US-13.

US-11 handoff completed: [ADR-0005](0005-authorized-operational-snapshots.md)
records the required operational snapshot, customer-registry validation and
read-only customer-scoped tools. Earlier future-tense US-11 references above
record the decision context at the time of this ADR.
