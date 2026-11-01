# Remaining scope and final submission

Sprint 2 adds persisted context, promotions and customer-scoped orders to the
local API. [US-13](examples/sprint-2/README.md) records three reviewed real-agent
conversations and two preserved failures with corrections. This is not the complete
challenge solution: store-policy retrieval and evaluation belong to the later sprint.

## Later retrieval sprint and submission work

- Integrate the supplied policy manual for supported store information, hours,
  payment and return-policy questions, with source-grounded answers. Start with
  simple document extraction/section lookup; a vector database is not required.
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
