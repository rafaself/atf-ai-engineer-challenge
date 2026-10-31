---
name: domain-testing
description: Design, modify, review, or diagnose tests in this customer-support agent project. Use for domain regression tests, contract tests, SQLite integration, and agent testing strategy. Routine execution of an unchanged test suite does not require this workflow.
---

# Domain-aligned testing

Preserve the root AGENTS.md testing invariants. Tests express executable contracts
for approved behavior; production domain logic and boundary decisions belong in
the application and its documented architecture, not in test helpers or mocks.

## Establish the expected behavior

- Read the relevant issue/acceptance criteria, applicable working agreements,
  domain sources, contracts, and ADRs before choosing assertions. Resolve conflicts
  using explicit user decisions; ask when a material requirement remains unclear.
- Identify the expected outcome and its source independently of the implementation.
  Do not copy actual output into expected values simply because an agent produced it.
- Distinguish a production defect, a test defect, an environment failure, and an
  intentionally changed requirement. An existing failure is evidence to investigate,
  not authorization to redefine the domain or expand the task.
- Change an incorrect/obsolete test when justified by the requirements. Explain the
  previous assumption, authoritative evidence, and corrected behavior. A refactor
  may change test setup while preserving the same behavioral assertion strength.

## Choose the smallest useful check

- For deterministic rules, error paths, and regressions, write a focused test first
  and observe failure for the intended missing behavior before the implementation
  fix. Import errors or broken fixtures alone do not demonstrate the regression.
  If the fix already exists, disclose that the failing baseline was not verified.
- Use temporary on-disk SQLite databases for persistence, rollback, read-only access,
  and snapshot consistency. Do not replace database behavior with mocks merely to
  obtain a passing result. Keep catalog fixture expectations tied to their snapshot.
- Use small typed fakes at agent/repository ports for application behavior. Do not
  implement a parallel copy of production business rules in test doubles.
- Probe unfamiliar provider capabilities with a small opt-in integration experiment;
  then test the established adapter contract deterministically. Fake model responses
  prove application wiring, not actual model reasoning or provider compatibility.
- Evaluate real model grounding, tool choice, scope handling, and answer quality
  with representative scenarios. Avoid exact-prose assertions and keep paid/network
  model calls out of the default suite.

## Keep tests useful and maintainable

- Assert observable outcomes and meaningful invariants rather than private helper
  names, SQL formatting, or internal call order unless that detail is the requirement.
- Preserve coverage of no-match versus operational failure, unavailable stock,
  exact prices, and unchanged snapshots where relevant. Do not invent extra business
  restrictions merely to simplify validation or assert implementation accidents.
- Do not bypass failures by relaxing thresholds, snapshot-updating, broad mocking,
  suppressing exceptions, skipping, or marking expected failures solely to pass.
- Verify changed behavior and affected boundaries, then run the README's relevant
  quality checks. Avoid tests for trivial reversible edits or library internals,
  duplicate cases, and coverage/test-count targets without behavioral value.
- Report the domain expectation, changed behavior, commands/results, and remaining
  gaps. Never claim a live provider check based on a fake or an unexecuted command.
