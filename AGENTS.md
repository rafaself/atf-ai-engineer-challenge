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
