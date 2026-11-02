# Remaining scope and final submission

## Agent follow-up closeout — 2026-11-02

PR [#75](https://github.com/rafaself/atf-ai-engineer-challenge/pull/75) retains the
evaluated **context-only** persona provisionally: reuse sufficient grounded policy
context, retrieve missing or ambiguous evidence, and always refresh operational
prices, stock, promotions and order details. The deterministic inventory-snapshot
notice and its regressions are retained. The extra conditional-policy rewrite is
reverted; the owner-approved `.codex/config.toml` change is independent configuration.

**Known model limitation:** Qwen still makes categorical Christmas-closure claims
despite receiving the general holiday rule and possible special hours together.
Reusing sufficient context can be appropriate; this does not make the resulting
answer faithful. Separate retrieval sufficiency, tool-use appropriateness and
answer faithfulness when assessing the final demonstration.

The [four-way comparison](examples/context-aware-policy/README.md) records all
20 separately approved guest HTTP turns, exact instruction variants, real tool
calls/evidence/answers, latency, cost and independent retain/revert decisions.
Context-only retrieved missing policy evidence in its isolated sample; none of
the variants repaired Christmas reasoning. These single samples do not establish
reliability, causality or a performance improvement. Earlier
[remediation trials](examples/grounding-followups/README.md) and historical
captures/verdicts remain intact. No additional inference or prompt tuning is part
of this integration. Final offline verification is recorded in the PR.

This closes the scoped agent follow-up, not US-23's full Docker/UI/CLI validation
or the overall challenge submission. The earlier planning notes below are
historical; policy RAG is already implemented and its observed limitations above
must accompany any final capability claims.

## Earlier planning context

Sprint 2 adds persisted context, promotions and customer-scoped orders to the
local API. [US-13 closing evidence](examples/sprint-2/closure/README.md) records
three reviewed final-code conversations and preserves failed comparisons. This is not the complete
challenge solution: store-policy retrieval and evaluation belong to the later sprint.

## Later retrieval sprint and submission work

- Integrate the supplied policy manual for supported store information, hours,
  payment and return-policy questions, with source-grounded answers. Start with
  structure-aware extraction and embedded ChromaDB, explicitly required by
  [Sprint 3 #49](https://github.com/rafaself/atf-ai-engineer-challenge/issues/49).
  See [integration and delivery guidance](sprint-3.md).
- Route operational catalog questions to the product tool and policy questions
  to the policy source. Support mixed questions without using model memory as a
  substitute for either source. Preserve an honest unsupported response meanwhile.
- Evaluate Portuguese tool selection, scope/accessory redirection, ambiguous
  requests, no matches, unavailable products, and grounded prices/stock against
  the chosen live model. Capture failures and adjust prompts/tools from evidence.
- The owner confirmed the customer/order fixtures are fictional and approved
  committing their original bytes. US-09 establishes trusted identity/session/history contracts and
  direct history execution. US-10 added bounded persistent sessions and
  concurrent-turn handling. Issue #33 replaces its former demo-token mechanism
  with guests/direct fictional-customer selection. US-11 enforces read-only order access using
  per-run dependencies and customer-scoped SQL. US-12 #26 was subsequently scheduled by the user and implements promotions/PIX
  pricing from unchanged sources. Frontend/CLI and deployment remain separate work.

The Sprint 2 live scenarios above are reviewed. They do not evaluate store policies
or guarantee future model behavior. Pending capabilities above are later-sprint
requirements, not implemented or accepted behavior. Reuse
current contracts and provider boundaries where they fit; do not preserve obsolete
paths merely for compatibility during this development stage.

## Final challenge submission checks

The supplied challenge PDF requires a public GitHub repository with a real
incremental commit history, reproducible README, assistant-use disclosure and
3–5 actual varied conversations, including a nontrivial retrieval or policy case.
The existing commits/PRs preserve incremental delivery. Confirm public visibility
at submission time; do not assume repository visibility from local Git state.

The deadline is the date/time in the recruiting email; it is not specified in the
repository resources. Confirm it with the user, freeze all repository changes at
the submission cutoff, and send nothing automatically. Submission is a reply to
the original recruiting email with the public repository link; sending it is
outside this implementation authorization.

Before submission, finish policy retrieval and its live evaluation, review the
curated examples and README limits, rerun the documented checks from a fresh checkout, inspect tracked files/history
for secrets, and confirm the final public link. Sprint 2 evidence does not establish the later policy capability or its real-agent
behavior; complete that work before claiming the full challenge is delivered.
