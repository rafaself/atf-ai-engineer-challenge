# Git delivery

Use the repository's actual conventions and available tools. This reference
supplies decision guidance, not authorization to publish, merge, or delete work.

## Choose the correct base

- Check local modifications, upstream tracking, and current remote/PR state. Refresh
  remote references when needed and permitted before relying on an old snapshot.
- Use the agreed integration base and dependency strategy. For a new work item,
  avoid continuing on a branch whose PR has already merged. Reuse an existing branch
  only when it is appropriate to the requested delivery and preserves user work.
- If changes landed on an obsolete branch, inspect the actual unmerged delta against
  the current base. Transfer only the intended changes through the normal workflow.
  Preserve commits and avoid rewriting shared history by default.
- A non-fast-forward update, conflicting change, or protected-branch rejection is a
  reason to inspect the new state, not to force the operation or bypass protection.
  Rewrite shared history only when explicitly authorized, with a verified tip guard.

## Publish a focused change

- Follow repository commit conventions and issue-reference requirements rather than
  hard-coding a universal format. Stage only intended paths and inspect the staged
  diff; preserve unrelated changes, including pre-existing staged work.
- When publishing is authorized, push the intended branch and verify success. Add
  commit links to the relevant work item when the workflow requires them.
- When a PR is requested or required, target the correct base. Describe the concrete
  resulting behavior, relevant validation, and material limitations. Use closing
  keywords only for work items the PR should actually close.
- Do not claim remote checks passed based on local results or the absence of checks.
  Keep issues open when the agreed completion boundary is merge rather than PR creation.

## Merge and clean up when authorized

- Re-read PR state, base, head, and required checks before merging. Guard the merge
  against the verified head so unreviewed concurrent changes are not merged silently.
  Do not bypass failing required checks or repository protections.
- Verify the resulting merge and work-item state; auto-closing behavior may be delayed
  or absent. Update references and completion evidence without closing a broader
  parent initiative prematurely.
- Synchronize local integration branches without overwriting local work. Delete
  branches/worktrees only when requested or clearly authorized and their work is
  verified integrated. For squash/cherry-pick histories, confirm equivalent changes
  rather than assuming ancestry alone establishes their status.
- Refresh stale remote-tracking references before cleanup. Treat an already-deleted
  branch as an inventory update; use tip guards for remote deletion so concurrent
  unmerged work cannot be removed. Never broadly delete branches based on names.
