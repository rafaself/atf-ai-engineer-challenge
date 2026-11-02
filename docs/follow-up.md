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

## Sprint status and remaining quality work

Sprint 3 policy retrieval and evaluation are integrated; follow-up #59 is closed
and merged through PR #62. Sprint 4 supplies the React/API interface, Docker
packaging and direct Python CLI. [US-23 validation](sprint-4-validation.md)
records the completed end-to-end checks, environment limits and historical model
evidence; [the curated conversations](examples/submission.md) preserve their
revision boundaries and failures.

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
