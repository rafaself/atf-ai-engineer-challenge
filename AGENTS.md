# Working agreements

- Keep changes within the current user story. Prefer simple, reversible solutions.
- Unless a production dependency is highly consolidated, safe, and trustworthy,
  ask the user before adding it. Keep development tools in the dev group.
- Avoid changes that introduce security vulnerabilities. If a risky change is
  necessary, explain the risk to the user before proceeding.
- Never commit credentials, local environment files, or generated databases.
- Use `type(scope): message` commit subjects of at most 60 characters. Reference
  the related issue in each commit body and link each published commit from that
  issue. Open a focused PR and record actual validation results.
- Run backend quality commands from the repository root using the README's
  `uv run --directory backend ...` commands. Preserve source CSV bytes.

## Testing

- Domain rules, approved requirements, and architecture decisions define expected
  behavior. Tests are executable contracts; they do not own or redefine application
  logic, boundaries, or the domain.
- Never weaken assertions, delete/skip tests, or change expected results merely to
  make the suite green. Correct an obsolete or incorrect test only with evidence
  from the actual requirements/domain, and explain that evidence in the change.
- Prefer test-first development for deterministic rules, error handling, and bug
  fixes. Use integration experiments and model evaluations for provider behavior
  and answer quality; keep live model calls opt-in.
- Before designing, modifying, reviewing, or diagnosing tests, read
  `.agents/skills/domain-testing/SKILL.md`. Report checks actually run and any gaps.
