# Working agreements

- Keep changes within the current user story. Prefer simple, reversible solutions.
- Unless a production dependency is highly consolidated, safe, and trustworthy,
  ask the user before adding it. Keep development tools in the dev group.
- Avoid changes that introduce security vulnerabilities. If a risky change is
  necessary, explain the risk to the user before proceeding.
- Never commit credentials, local environment files, or generated databases.
- Use `type(scope): message` commit subjects of at most 60 characters. Every
  commit, including documentation, tests, and tooling, must reference its related
  GitHub issue in the body (for example, `Refs #23` for US-09). Link each published
  commit from that issue. Open a focused PR and record actual validation results.
- Run backend quality commands from the repository root using the README's
  `uv run --directory apps/backend ...` commands. Preserve source CSV bytes.

## Development stage and compatibility

- This project is under active development and is not currently a production
  system. Backward compatibility with earlier project versions is not required
  unless the user explicitly requests it.
- When an approved direction changes, update affected code, callers, tests, and
  documentation together. Remove obsolete implementations and superseded paths
  instead of preserving legacy behavior, deprecated APIs, compatibility shims,
  fallback branches, or duplicate implementations solely for compatibility.
- Prefer one coherent implementation of the current requirements. Do not add
  migration machinery or production-compatibility infrastructure without a concrete
  current need. Continue to preserve applicable domain rules and security boundaries.

## Testing

- Domain rules, approved requirements, and architecture decisions define expected
  behavior. Tests are executable contracts; they do not own or redefine application
  logic, boundaries, or the domain.
- Never weaken assertions, delete/skip tests, or change expected results merely to
  make the suite green. Correct an obsolete or incorrect test only with evidence
  from the actual requirements/domain, and explain that evidence in the change.
- Prioritize tests by failure impact and likelihood: critical business rules,
  complex behavior, consequential edge cases, and failure-prone boundaries.
  Each test must protect a clear behavior or regression and add confidence worth
  its execution, reliability, and maintenance cost. Avoid trivial, redundant, or
  implementation-detail tests; do not pursue coverage or test counts as goals.
- Prefer test-first development for high-value deterministic rules, error handling,
  and bug fixes. Use integration experiments and model evaluations for provider
  behavior and answer quality; keep live model calls opt-in.
- Before designing, modifying, reviewing, or diagnosing tests, read
  `.agents/skills/domain-testing/SKILL.md`. Report checks actually run and any gaps.
