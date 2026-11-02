# Remaining scope and final submission

Sprint 3 policy retrieval and evaluation are integrated; follow-up #59 is closed
and merged through PR #62. Sprint 4 supplies the React/API interface, Docker
packaging and direct Python CLI. See [architecture](architecture.md) and
[US-23 validation](sprint-4-validation.md) for current behavior and evidence.

Remaining quality work concerns actual model tool selection, mixed order/policy
reasoning, unsupported claims and retrieval relevance. The
[historical failures](examples/us-18/results.md) remain visible; a consulted-source
list does not certify generated claims. Keep broader agent/model improvements in
existing follow-up #43/#40 rather than expanding final documentation work.

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

Before submission, review the curated examples and README limits against the
final delivered revision, inspect tracked files for secrets, and confirm the
public repository link and deadline. [US-23 validation](sprint-4-validation.md)
records executed checks and environmental limits. Historical captures do not
establish current model quality; any new paid evaluation requires separate approval.
