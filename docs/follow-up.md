# Remaining scope and final submission

Sprint 1 delivers the catalog foundation and local API. It is not the complete
challenge solution. Live compatibility and five remediation scenarios have recorded evidence;
see [examples](examples/README.md). Broader model evaluation remains ongoing.

## Next product work

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
  direct history execution. US-10 implements the approved server-side demo
  token mapping, bounded persistent sessions, and concurrent-turn handling;
  US-11 validates customer mappings and enforces read-only order access using
  per-run dependencies and customer-scoped SQL. US-12 #26 was subsequently scheduled by the user and implements promotions/PIX
  pricing from unchanged sources. Frontend/CLI and deployment remain separate work.

Live multi-turn Bedrock evaluation remains US-13. Other pending capabilities above
are follow-up requirements, not implemented or accepted behaviors. Reuse
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

Before submission, finish the live example and policy scope, review README limits,
rerun the documented checks from a fresh checkout, inspect tracked files/history
for secrets, and confirm the final public link. Offline tests and a merged sprint
PR alone do not satisfy the outstanding real-conversation requirements.
