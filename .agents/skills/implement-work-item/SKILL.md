---
name: implement-work-item
description: Implement an existing user story, issue, or approved development task through scoped repository changes, validation, and authorized delivery. Use when asked to implement a specified work item; not for backlog design, standalone reviews, or general research.
---

# Implement a work item

Deliver the requested behavior with evidence, without expanding a bounded task into a larger initiative. User instructions and applicable repository guidance govern this workflow, including what delivery actions are authorized.

## Establish the task and starting state

- Read the work item, acceptance criteria, relevant domain sources, repository instructions, and current implementation. Treat existing code/tests as evidence, not as authority when they contradict approved requirements.
- Inspect the working tree and integration base before editing. Preserve unrelated user changes. Check current dependency status rather than assuming that a closed issue, old branch name, or earlier report establishes readiness.
- Honor the chosen dependency strategy: wait for required merges, or stack changes only when authorized. Do not merge prerequisites automatically. Continue useful independent investigation while a dependency prevents implementation.
- Resolve consequential scope/interface conflicts with the user. Choose simple, reversible implementation details autonomously where the task permits. Keep tightly related work together; do not add abstractions or infrastructure merely to satisfy a generic development pattern.

## Implement the bounded behavior

- Map acceptance criteria to observable outcomes and identify the smallest useful change within existing boundaries. Follow an approved plan, but verify assumptions against the actual environment and explain material deviations.
- Keep follow-up features outside the delivery. Record omissions and external blockers explicitly rather than silently redefining completion.
- Apply the repository's testing/dependency/security guidance. Use another skill only when it is available and relevant; this workflow does not require delegation, a specific testing framework, or any companion skill.
- If delegation is requested or otherwise authorized and useful, preserve the task's constraints in assignments and verify the integrated result. Do not introduce a mandatory review-agent or multi-agent pipeline for ordinary implementation.

## Validate what was actually delivered

- Derive assertions from requirements and domain evidence independently of the implementation. Prefer test-first work for deterministic rules and regressions when appropriate; never weaken tests merely to make a change pass.
- Use the narrowest meaningful checks first. After they pass, run required checks and affected integration boundaries; repeat or broaden only for a concrete reason.
- Execute documented commands from the stated directory and verify they work there. Reuse established tooling rather than inventing an additional task runner.
- Distinguish local deterministic tests, infrastructure integration, and live-provider behavior. Test doubles do not prove provider compatibility or generated-answer quality. Mark unperformed checks and unsatisfied criteria honestly.
- Inspect the final diff and working tree for unintended changes. If review reveals a defect, investigate the concrete scenario, fix within scope when authorized, and verify the correction without turning remediation into unrelated cleanup.

## Deliver within authorization

- Implementation, committing, pushing, publishing a PR, merging, closing an issue, and deleting branches are distinct actions. Use authorization already given in the task/session or applicable guidance; do not ask again unnecessarily, or infer that authority for one action grants every subsequent action.
- For Git delivery, read [Git delivery](references/git-delivery.md) when relevant. Otherwise deliver the requested local result without requiring a Git host.
- Summarize the behavior changed, validation performed, relevant artifacts, and remaining limitations. Update tracking only to reflect verified outcomes; an implemented change, passing tests, an open PR, and a merged delivery are different states. Stop at the requested boundary rather than starting the next work item.
