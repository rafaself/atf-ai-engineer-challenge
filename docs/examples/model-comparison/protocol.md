# Issue #40: Bedrock model comparison protocol

The current default is [v4](scenarios-current-v4.json), with semantic verdicts
separate from tool compliance, efficiency and presentation. The
[effective-data report](effective-data-qwen32-gptoss120-2026-11-03.md) records the
implementation and cumulative spending under the approved US$1.00. Older default
and criterion descriptions below are historical.

The [structured return evidence experiment](structured-return-qwen32-gptoss120-2026-11-03.md)
uses the unchanged v3 prompts and records cumulative spending within the approved
US$1.00, including the preceding run. Its per-run cap was US$0.97557130.

Status: the original three-model Bedrock Runtime comparison is complete. Its
reviewed results are in `README.md`; the original model responses and tool traces
remain in `capture-runtime-2026-11-02.json`. A later current-harness GPT-OSS
follow-up and separately approved GPT-OSS 20B retry are recorded in
`gpt-oss-runtime-2026-11-03.md` and `gpt-oss-20b-retry-2026-11-03.md`; neither
rewrites the historical captures.
The subsequent Qwen3 32B / GPT-OSS 120B remediation run, including the derived
Natal interpretation and remaining semantic failures, is documented in
`remediated-qwen32-gptoss120-2026-11-03.md` and its capture. It used a separate
US$0.95 live-run approval; that cap does not authorize another run.
The later [prompt and harness evaluation](prompt-harness-qwen32-gptoss120-2026-11-03.md)
also completed 16/16 turns per model under a fresh US$1.00 cap, with no HTTP
errors. Its capture used the then-default legacy `scenarios.json`; because all
scenario IDs and prompts match `scenarios-current-v3.json`, manual verdicts use
the v3 expectations preserved alongside the capture. The runner default is now
v3. This correction did not require further inference.
No additional Bedrock inference was used for the post-run review and erratum of
the original comparison.

The 20B retry used a fresh Qwen control, the nine-conversation current-harness
fixture, and a separately approved US$0.95 cap. Before the run, the agent
request allowance was raised from five to six to leave room for final answer
synthesis after five tool calls, one retry was enabled for unknown tool names,
and catalog lookup normalized Unicode dash punctuation. The reviewed capture
and retry findings are recorded in `gpt-oss-20b-retry-2026-11-03.md`. It
completed all 16 turns for each
model with no HTTP errors, but manual review found two critical errors in 20B
and one in Qwen.

## Scope and candidates

The evaluated models were Qwen3 32B, Nova Micro, and Nova Lite, all using
Bedrock Runtime Converse for model inference. Every agent tool ran in the
application locally. Nemotron Nano 3 was excluded as an architectural scope
decision: this comparison did not add a Mantle adapter solely to evaluate one
candidate. Its Runtime Converse tool-calling compatibility was not verified.
This exclusion does not claim that Bedrock Runtime generally lacks tool calling.
No Mantle adapter or Mantle inference was used. GPT-6 Luna remained excluded
because it was not enabled for this account.

The fixed set has nine Portuguese conversations and 16 planned HTTP turns per
model. Run one pass per scenario, with a fresh session per conversation and the
same session for follow-ups. Only the selected-orders and mixed-order scenarios
set fictional customer ID 1. The normal `/api/chat` → `ChatService` → Pydantic AI
→ local tools → SQLite path is used. Source data and the policy index are
read-only; conversation state uses a temporary SQLite database.

## Post-run errata and reviewed denominator

The live run used frozen scenario fixture v1. Its exact bytes are preserved as
`scenarios-frozen-v1.json` (SHA-256
`20b4210c198d3742a65ca7a9997bcd762626feac30b07aa9c4fe8872b8244b62`), matching
the scenario hash recorded in the original capture. The legacy `scenarios.json`
fixture is v2: the `no-match` scenario's `required_tools` is corrected from nonexistent
`search_products` to the registered `get_product_details` tool. That tool is
appropriate for a literal product-name lookup. The recorded models used
`get_product_details`; this expectation correction does not change their scores.
The capture retains its v1 expectations and records this erratum separately.
The active current-harness fixture is `scenarios-current-v3.json`; it adds the
approved freight clarification and current Natal, return, and snapshot-notice
expectations. The runner defaults to v3 and hashes it in the source freeze.

The Qwen policy-hours conversation stopped on a local policy-retrieval HTTP 503
caused by `ModuleNotFoundError` because the benchmark dependency group was not
active. Its two remaining turns are `not_executed`. This is a
`local_infrastructure` execution failure, not a semantic model failure. It stays
in the HTTP reliability count and cost accounting; it has no Pass/Partial/Fail
verdict. Qwen therefore has eight evaluated conversations out of nine attempted
and 14 attempted turns out of 16 planned. Nova Micro and Nova Lite each have
nine evaluated/attempted conversations and 16/16 turns. The capture preserves
the failed request, failure cause, and two unexecuted turns; none was retried.

Post-run manual review changed Qwen's `mixed-order-return-followup` from Pass to
Partial. Its first answer presented the imported tracking status as delivery
before qualifying that the estimated date did not prove receipt. The factual
follow-up then answered without a fresh policy search. Conditions were still
requested, so this is Partial rather than a critical eligibility error. The
reviewed capture keeps the turn evidence intact and recomputes the aggregates
over completed conversations only.

## Retrieval and account preflight

Before any paid model request, the runner calls the existing `LocalPolicySearch`
against the local policy corpus and index. This loads the `sentence-transformers`
dependency, verifies the corpus/index fingerprint and collection contents, and
loads the cached E5 model with downloads disabled. A missing dependency, model,
or index blocks the run with `blocked_retrieval_readiness`, records the cause,
and exits before model inference. The explicit `--group benchmark` run command
installs the local embedding dependencies; the repository README describes how
to prepare the cached model and index.

The no-inference account availability check was denied by IAM for
`bedrock:GetFoundationModelAvailability`; the AWS Pricing API also denied
`pricing:GetProducts`. These actions are separate from model inference. Rates
were checked against the public AWS Price List. The approved Qwen Runtime
baseline request confirmed inference access and served as the access probe for
the recorded run.

The approved cap for the recorded run was **US$1.00**. This approval does not
carry forward to another live run. The runner requires `--live` and an explicit
cap, refuses a value above US$1.00, and checks a conservative full-turn
reservation before each HTTP request. The reservation covers up to five model
requests at the full model context ceiling plus 1,024 output tokens. Missing
token usage is charged at that ceiling. SDK retries remain disabled beyond one
attempt. Estimates are not invoices.

## Review and reporting

Assign semantic verdicts only to conversations that completed all planned turns.
Review final answers against the actual tool results, policy evidence, required
facts and conditions, ambiguity handling, and multi-turn reference resolution.
Record missed tools, unsupported claims, critical errors, and UX notes. A failed
HTTP turn is an execution/reliability failure; classify its cause as provider or
SDK, local infrastructure, local execution, or transport when supported by the
trace. Keep HTTP errors and not-executed turns in the reliability report, and do
not convert them into semantic failures or assume missing turns passed.

Report Pass/Partial/Fail over evaluated conversations, alongside evaluated and
attempted conversation counts and attempted/planned turn counts. Preserve
critical-error and missed-tool counts, HTTP errors, model calls, token usage,
total estimated cost, cost per passing conversation, and missing-usage counts.
The capture's `execution_failure_categories` separates local infrastructure
from provider/SDK and transport failures.

The recorded latency is **end-to-end `/api/chat` request wall time**. It includes
model inference, local tool execution, policy retrieval, and possible local
initialization; it does not measure model-only inference speed. Report median and
maximum. Do not infer stable tail latency or report p95 for this small sample.

No cheaper candidate met the selection gate of at least Qwen's evaluated pass
count and zero critical errors. Keep Qwen provisionally as the current default;
this one-pass comparison does not establish reliability or justify automatic
routing. Do not use an LLM judge, exact-phrase tests, or statistical claims.

## Runner maintenance review

The runner was reviewed for duplication and unnecessary abstractions. Existing
cost reservations, input hashing, Runtime route checks, local policy copies,
checkpoints, and resume handling each protect a concrete run constraint or the
captured evidence, so they remain. Candidate metadata setup was consolidated;
the runner was not rewritten as a generic benchmark framework, and no extra
provider adapter or latency instrumentation was added.
