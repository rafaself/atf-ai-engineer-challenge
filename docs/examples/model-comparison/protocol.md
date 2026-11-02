# Issue #40: Bedrock model comparison protocol

Status: the three-model Runtime-only comparison and manual review are complete.
The Bedrock availability API was denied by IAM, but the Qwen Runtime baseline
succeeded. The reviewed report is in `capture-runtime-2026-11-02.json`.

## Frozen evaluation

Use the exact prompts and source-derived expectations in `scenarios.json`. The
nine conversations contain 16 planned HTTP turns per model. Run one pass per
scenario, Qwen3 32B first as the reference, then Nova Micro and Nova Lite. Use one
fresh session per scenario; reuse its session ID for follow-up turns. Only the
selected-orders and mixed-order scenarios set fictional customer ID 1. A failed
HTTP turn fails that scenario and leaves later turns in that conversation
unexecuted. Do not retry it or fabricate answers. Continue with independent
scenarios unless provider access fails or the cost guard stops the run. In the
recorded run, one Qwen policy-search turn failed locally with HTTP 503 because
the benchmark dependency group was not active; its two follow-up turns were
left unexecuted and the failed turn was not retried. The other two models
completed all 16 planned turns.

The application revision and fixture hashes are recorded in every capture before
the first request. Catalog, order, CSV, PDF, policy-corpus, and index files are
read-only inputs. Conversation history is written only to a temporary SQLite file.
The evaluator uses the normal `/api/chat` → `ChatService` → Pydantic AI → local
tools → SQLite path. Qwen3 32B, Nova Micro, and Nova Lite all use Bedrock Runtime
Converse for model inference. Qwen follows the app's established default route;
the reviewed Sprint 2 captures show actual Qwen tool calls through that path.
Nemotron Nano 3 is excluded because its documented client-side tool-calling route
uses Bedrock Mantle, outside the Runtime-only constraint for this comparison.

## Preflight and spending guard

The three candidate IDs, Runtime Converse routes, token ceilings, and rates are
recorded in `pricing.json`. Standard rates were checked against AWS's current `us-east-1`
Bedrock Price List offer on 2026-11-02 (version `20261030160456`); the offer prices
tokens per 1K and the manifest converts them to per 1M. Qwen uses the existing
Runtime Converse route, which has reviewed live tool-call evidence in
`docs/examples/sprint-2/closure/README.md`. The benchmark uses Pydantic AI's
existing Converse integration for all candidates. The recorded principal could
not call Bedrock's availability API, but its approved Qwen baseline request
confirmed Runtime inference access. A candidate without verified Runtime
Converse/tool support is excluded, and an unavailable or incompatible Qwen
baseline blocks the matrix. Do not substitute another model.
GPT-6 Luna remains excluded.

The approved cap for this run is **US$1.00**. The runner refuses a larger cap,
requires explicit `--live`, and checks current-day pricing and runtime tool
compatibility before evaluating. It checks the remaining budget before every
HTTP turn. Its reservation assumes the maximum five model requests per turn, each at
the full model input-context ceiling plus 1,024 output tokens. After a turn, it
uses observed usage and reserves the full request ceiling for any request whose
usage is missing. This is deliberately conservative; estimates are not invoices.
The SDK's existing retry setting stays at one total attempt, and the app's
existing one output correction remains inside the five-request limit.

At the absolute limits, the three-model matrix could issue 240 provider requests,
process up to 36,800,000 input-context tokens, and generate up to 245,760 output
tokens. Full-context reservations exceed the approved cap at the issue's
illustrative rates, so a complete matrix is not guaranteed; stop safely at US$1
and mark all remaining work unexecuted. Never raise the cap in code or silently
retry paid requests.

## Review rubric and recommendation

Review every final customer-facing answer against that turn's actual tool
arguments/results and the frozen policy text. Grade each conversation pass,
partial, or fail. HTTP 200 alone does not pass. Record required facts/tool use,
unsupported claims and omissions, critical errors, HTTP/provider failures,
request counts, available token usage, estimated cost, and observed wall time.
Report median and maximum latency; do not report p95 for this small sample.

A cheaper candidate is recommendable only if it has at least as many passing
conversations as Qwen, has zero observed critical errors, and human review finds
no material UX weakness. Otherwise keep Qwen or report insufficient evidence.
Use no LLM judge, exact-phrase tests, or statistical reliability claims.

The reviewed capture includes the frozen expected facts and required tools,
observed tool calls, full per-turn trace, and completed human-review fields for
verdict, critical errors, missed tools, unsupported claims, and notes. Review
each answer against its actual tool results and policy text. Missing token usage
is counted separately and costed at the full request reservation.

The final report belongs in `README.md` beside sanitized captures and must include
one compact table with model, pass/partial/fail, critical errors, missed tools or
unsupported claims, HTTP errors, model calls, tokens, total estimated cost,
cost per successful conversation, and median/maximum latency. State every
denominator and missing-usage field. Keep failures and not-executed turns visible.

## Current execution preflight

The no-inference account availability check reached AWS and returned
`AccessDeniedException` for `GetFoundationModelAvailability`. The AWS Pricing API
also denied the account request, so rates were independently checked from the
public AWS Price List file. AWS's sanitized error states that no identity-based
policy allows `bedrock:GetFoundationModelAvailability` or `pricing:GetProducts`.
These are separate from inference permissions. No inference calls were made by
preflight. When the availability action is denied, the live runner uses the user-approved Qwen
baseline request as its access probe, subject to the same US$1.00 cost guard; a
provider denial stops the matrix. Credential values are not included in reports.
