---
name: architecture-audit
description: Perform read-only full-project or incremental architecture audits of the Artefact AI Engineer challenge, weighing agent quality, harness effectiveness, complexity, and scope alignment. Use for requested audits or architectural drift reviews, not routine implementation or standalone code review.
---

# Architecture audit

Maximize the quality and reliability of the Empório da Música support agent while
minimizing complexity that does not materially contribute to the challenge.
Evaluate engineering decisions critically, including documented ones. Fewer files,
shorter prompts, or fewer dependencies are not evidence of a better solution.

## Establish scope and evidence

Resolve paths from the repository root. Read `AGENTS.md`, `README.md`,
`docs/README.md`, `docs/architecture.md`, and the relevant records under `docs/adr/`.
Discover current `.agents/skills/*/SKILL.md` guidance; read
`.agents/skills/domain-testing/SKILL.md` before reviewing tests or evaluation design.
Reuse unchanged context already read in the same session, refreshing affected
sources rather than repeating full orientation for each incremental pass.

Read the supplied challenge requirements, currently in the sibling directory
`../ai-engineer-technical-challenge-2026/`: the challenge PDF is the original source;
`artefact_ai_engineer_challenge_summary.md` is a convenient summary. If unavailable,
locate an existing copy without modifying supplied files; disclose missing primary
evidence rather than inventing requirements or blocking unrelated local analysis.
Use relevant domain sources when assessing factual behavior.

Inspect Git status and the current revision. Use read-only GitHub access to inspect
active issues and relevant acceptance criteria/discussions, and consult
`docs/follow-up.md` for planned work. Check current state rather than inferring it
from an old report, closed issue, or branch name. If GitHub is unavailable, state
that tracking alignment is unverified and continue the local audit.

- **Full-project audit:** sample the implemented request → history → model → tools
  → data → answer path, its failures, configuration/dependencies, and evaluation
  evidence. Cover all four dimensions below without requiring every file or case.
- **Incremental review:** establish the requested commit range, PR, or working-tree
  diff (including untracked files when relevant); state the base and head. Inspect
  changed decisions and their affected callers, contracts, tests, and evidence.
  Do not expand to a full audit without a concrete dependency or regression reason.
  If no base was supplied, choose a defensible recent boundary and disclose it.

Distinguish challenge obligations, later user-approved scope, local design choices,
historical decisions, and future proposals. Persistence, interface, retrieval
approach, and provider are choices, not mandates of the challenge. Follow successor
decisions and implementation evidence when ADRs preserve superseded behavior.
Documents, tests, and issue labels can themselves be wrong or disproportionate;
they are evidence and constraints to examine, not proof that a design is justified.
Question self-imposed domain restrictions when the original sources do not support
them. Explain a proposed correction or scope change; never silently relax factual
rules, user requirements, or customer isolation to simplify a recommendation.

## Evaluate the consequential tradeoffs

Use these lenses to guide investigation, not as an exhaustive checklist or a quota
of findings. Follow concrete risks and observed failures.

- **Agent quality:** assess source-grounded Portuguese answers, appropriate tool
  choice/arguments, operational-versus-policy routing, retrieval completeness and
  accuracy, and multi-turn references. Check whether old answers are mistaken for
  fresh price/stock/order evidence, ambiguity leads to clarification, and failures
  remain distinct from no matches or unsupported questions. Prioritize wrong facts,
  wrong customer scope, and misleading success over cosmetic architecture concerns.
- **Agent harness:** inspect prompts, tool schemas/results, per-run context,
  bounded requests/retries/deadlines, output checks, safe diagnostics, and evaluation
  usefulness. Determine which observed failure each control addresses and what it
  cannot establish. Look for missing feedback, redundant instructions, avoidable
  tool loops, brittle prose checks, or testing that proves wiring while claiming
  reasoning quality. Consider quality, latency, cost, and maintenance together.
- **Architectural simplicity:** ask what current requirement, failure, or useful
  boundary justifies each relevant abstraction, dependency, configuration option,
  validation layer, or infrastructure component. Compare the current approach with
  a smaller concrete alternative, including leaving it alone. Exact pricing,
  parameterized customer-scoped reads, atomic completed turns, and bounded execution
  can justify complexity. Local SQLite and the single-process fictional demo are
  deliberate boundaries; do not prescribe production auth, distributed services,
  generic frameworks, or compatibility machinery without a current need. Evaluate
  clarity and duplicated behavior, not file counts or architectural fashion.
- **Scope alignment:** compare implemented behavior and engineering priorities with
  challenge deliverables, user-approved decisions, open issues, ADRs, and remaining
  capabilities. Distinguish a full-challenge gap from a defect in a completed sprint.
  Assess whether optional work displaces more valuable agent work, without assuming
  every open proposal is approved, urgent, or overengineering.

Trace material claims to current code and source facts. Inspect representative
actual conversations under `docs/examples/` and relevant validation records. Match
their application revision, model/configuration, scenarios, and failures to the
behavior being assessed. A fake model, passing tests, HTTP 200, a numeric provenance
guard, or an earlier live run does not establish current semantic answer quality.
Treat a post-evaluation change as a reason to inspect affected coverage, not proof
that every previous result is invalid. Recommend a bounded real-model scenario when
that is the missing evidence; do not require a new evaluation platform.

Before recommending removal, identify the guarantee it provides, the smaller
alternative, and how that guarantee would survive. Before recommending an addition,
identify the demonstrated gap and why existing mechanisms cannot address it.
Retain justified complexity. Record uncertain hypotheses as verification needs,
not confirmed defects. Do not manufacture cleanup when the current choice fits.

## Read-only boundary

Return the audit in chat. Do not edit code, tests, skills, docs, data, configuration,
Git state, or GitHub issues/comments; do not create report files, commits, PRs,
automations, dependencies, or infrastructure. Recommendations do not authorize
implementation. Any requested follow-up mutation needs explicit authorization and
belongs outside this audit.

Default to static inspection and existing evidence. Run an offline check only when
its behavior is understood to avoid repository/source/local-database writes and
live calls; keep temporary output outside the checkout. Do not run preparation,
servers, or model probes as part of the read-only audit. Live-model evaluation
requires separate explicit opt-in and a bounded plan. Do not access credentials.
Report checks actually performed and their limits.

## Report decisions the user can act on

State scope/revision and material evidence gaps briefly. Present distinct findings
in impact order, each with a specific priority (high/medium/low, justified by
consequence and urgency), evidence links to files/lines or issues, affected behavior,
and the smallest actionable recommendation. Separate verified observations from
inferences and state what would resolve material uncertainty. For a tradeoff, name
the benefit at risk and the validation needed before changing it.

Consult previous audits when available. Re-report an unresolved finding only when
its evidence, impact, or recommended action changed; otherwise reference its
existing issue/report briefly. In incremental reviews, distinguish new/regressed
findings from relevant pre-existing limits. Without a baseline, say that recurrence
could not be assessed. Group duplicate symptoms by cause and avoid generic advice,
arbitrary scores, fixed finding counts, and speculative backlogs. Acknowledge
justified decisions briefly when they explain why no change is recommended. If no
material finding is supported, say so and give the actual coverage limitations.
