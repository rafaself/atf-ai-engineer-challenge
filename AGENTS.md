# Working agreements

## Purpose and scope

This is a local AI Engineer technical challenge. The product being evaluated is
LLM interaction quality: tool use, grounded answers, conversational context,
retrieval, and user experience. Keep that integration reliable and simple.

- Stay within the current task and concrete challenge requirements. Use the
  smallest sufficient supporting infrastructure; SQLite is a deliberate choice.
  Avoid speculative abstractions and production infrastructure unless required
  by the challenge or explicitly requested by the user.
- If a plan introduces work outside this purpose or disproportionate complexity,
  stop the affected work, explain why, and propose a simpler alternative or
  deferral. Resolve that scope with the user; make routine decisions autonomously.
- Preserve factual accuracy, domain rules, and customer isolation when simplifying.

## Implementation and data

- Use clear names, focused modules, and explicit imports from defining modules.
  Update code, callers, tests, and documentation together when behavior changes.
- Backward compatibility is unnecessary unless requested. Remove superseded code;
  do not add compatibility shims, duplicate paths, or migration machinery without
  a current need.
- Preserve all supplied CSV/PDF bytes. Never commit credentials, local environment
  files, or generated databases. Explain any necessary security risk before proceeding.
- Ask before adding a production dependency unless it is well-established and
  trustworthy. Keep development tools in the dev dependency group.

## Validation

- Before designing, modifying, or reviewing tests, read
  `.agents/skills/domain-testing/SKILL.md`; also use it when diagnosing test failures.
- Requirements and domain rules define expected behavior. Never weaken or skip
  tests merely to pass; explain requirement evidence when correcting obsolete tests.
  Prioritize consequential rules, failures, and boundaries over coverage counts
  or redundant implementation checks. Prefer test-first work for deterministic
  rules and bug fixes.
- Use representative real conversations to evaluate LLM behavior; controlled
  tests do not establish answer quality. Live model calls require explicit opt-in.
- Run checks appropriate to the change from the repository root using the README's
  `uv run --directory apps/backend ...` commands. Report actual results and gaps.

## Delivery

- Use `type(scope): message` commit subjects of at most 60 characters. Every commit,
  including documentation, tests, tooling, and merges, must reference its related
  GitHub issue in the body, for example `Refs #23`. Link each published commit
  from that issue.
- When delivering through a PR, keep it focused and record actual validation results.
