# Post-implementation #43 review — 2026-11-02

The report identifies relevant operational and evaluation concerns. The smallest
response is to preserve evidence and use the existing Sprint 4 integration work.
No production code, prompt, retrieval relationship, dependency or validator changes
are justified by this review. Issue #43 stays closed for its completed implementation
and offline scope. US-23 (#70) has since closed after its separate Sprint 4 validation;
this PR preserves supplemental evaluation evidence and does not replace that validation.

## Disposition of the four findings

| Finding | Actual evidence | Decision |
| --- | --- | --- |
| 1. Clarification retrieval coverage | Actual pinned CPU E5, current Chroma index and production `LocalPolicySearch` returned the clarification in all 12 queries, alongside original section 5.1 and section 5.2. Queries cover 499.99 / 500 / 500.01, region, minimum spend, outside-region scope, and a short contextual follow-up. Correct source, no-page metadata and text are saved in [e5-retrieval.json](e5-retrieval.json). | No reproduced retrieval failure; do not add a relationship or change ranking. This small sample does not guarantee every possible query. |
| 2. Prompt size | #43's final merged prompt is 7,074 characters / 1,018 whitespace words versus 7,090 / 1,026 originally. | Accept the structural/maintenance benefit. No tokenizer, latency, cost or quality improvement is established by this size difference; no further shortening. |
| 3. Stale index / packaging | US-21 #66 is closed. Commit `50c711b` on the parallel packaging line, already included in US-23's worktree at `790feb1`, documents one-time preparation, explicit `--rebuild` and persistent data/model/index storage. The US-23 validation record reports matching hashes after container recreation and a real cached-E5 query afterward. Main's existing [policy setup](../../guides/policy-retrieval.md) also documents rebuilds. | Already addressed in US-21 and validated in the completed Sprint 4 work. See [US-23 validation](../../archive/sprints/sprint-4-validation.md). Retain explicit preparation; do not add automatic startup rebuilds/downloads. The default bridge path had a separate environment limitation; the report records the tested Linux workaround. |
| 4. Model behavior | Owner approved Qwen only, at most six conversations / 12 turns, US$0.50 total cap. The approved sample completed all 12 HTTP turns, but manual source review found remaining failures. | Functional evidence now exists; it does not establish general reliability or that all intended improvements worked. Preserve failures under US-23 rather than adding speculative prompt patches or semantic enforcement. |

The real Chroma index checks also returned the expected actionable operator errors:
`Missing index; run explicit indexing first` and
`Stale index configuration; use explicit --rebuild`. The stale check used a deliberately
mismatched fingerprint while opening the existing collection; it did not alter the
collection. The missing check used an isolated temporary directory. Runtime maps
retrieval errors to the existing operational-failure contract, not a policy no-match.
No new test framework or production test logic was introduced.

## Approved live sample

[Raw capture](qwen-approved-2026-11-02.json) preserves prompts, actual model/tool
messages, returned evidence, final answers, timings and usage. The capture's production
source was `9383414` (main containing A+B at run time); source hashes are in the capture.
This is the historical evaluation revision, not the current main revision. Only evidence
files and the existing local Codex config were uncommitted. The six scenario IDs and all
12 user messages come unchanged from the #40 fixture. The freight fixture's
`baseline_expected` is explicitly historical: current equality is judged against the
new approved business evidence, not the old gap. Historical captures/verdicts remain
unchanged.

The one-off [approved probe](run_approved_probe.py) reuses the #40 scenario/pricing
loaders and US-18 `RecordingAgent` through the normal ASGI HTTP service, repositories,
agent and tools. Each conversation starts a fresh session; customer 1 is selected
only for the two order cases. Production limits remain five model requests, five
tool calls and 1,024 output tokens, with existing retries only. All possible turns
were reserved upfront at **US$0.324864**, below the approved US$0.50 cap. No conversation
or failed model answer was retried.

There was one local import-path setup failure before any provider initialization
or calls. Setting the package and API source directories on `PYTHONPATH` resolved it. The
successful run used cached local E5/Chroma; the same search instance was preflighted
before chat, so policy latency excludes cold E5 loading. No model downloads occurred.
This API ASGI sample does not itself validate Docker/UI/CLI integration. Those
broader checks were completed separately in US-23; see the [Sprint 4 validation
record](../../archive/sprints/sprint-4-validation.md) for the actual setup, environment limits and
prepared-index check. The sample's narrower scope and historical source revision
remain unchanged.

Reproduction requires fresh explicit paid-run approval; do not overwrite the capture:

```sh
PYTHONPATH="$PWD/packages/emporio_music/src:$PWD/apps/api/src" \
HF_HOME="$PWD/data/benchmark-cache/hf" HF_HUB_OFFLINE=1 \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
uv run --project apps/api --extra policy-rag --locked \
  python docs/examples/issue-43-review/run_approved_probe.py --live \
  --output /tmp/new-approved-qwen-capture.json
```

## Manual source review

This is a small exploratory source-based assessment by coding agents, not an
independent human evaluation or statistical before/after trial. It compares against
#40's preserved Qwen traces and relevant Sprint 3 failures. A single newly passing
case is an observed recovery, not a guarantee or proof of a causal prompt effect.

| Conversation | Result | Before / after evidence |
| --- | --- | --- |
| Named zero-stock product and alternative | Partial | Correctly reports Giannini active but zero stock. Unlike Qwen's prior partial case, the alternative follow-up performs `search_available_products` with no invented budget and returns supported products. The first answer still offers to verify future availability without a source/tool for replenishment dates, and omits the imported-inventory/no-live-confirmation qualifier. |
| Promotion / PIX ordinal follow-up | Pass | Fresh promotion search and literal `Ohana CK-20 Concert Natural` lookup with `payment_method=pix`; final R$439.20 and non-stacking match returned pricing. Maintains Qwen's prior passing behavior; this does not test or fix Nova Lite/Micro. |
| Selected order list / detail follow-up | Pass | Previously Qwen skipped detail lookup and invented the item. Now it calls `get_my_order(order_id=4)`, reports the returned Giannini item, quantity 1 and available tracking, preserves R$799.90 and estimated-date/snapshot caveats. Observed recovery in this sample. |
| Mixed order / online return | Fail | First turn retrieves both order and policy evidence, but does not resolve purchase channel, actual receipt or condition. Follow-up supplies online purchase and five days since receipt; the model makes no fresh policy call, opens with eligibility approval, invents phone/email and offers call scheduling. Missing condition/exclusion facts remain unresolved. Fresh-tool failure persists and unsupported contact/procedure claims remain; no pass is inferred from HTTP 200. |
| Hours / holiday follow-up / product topic switch | Partial | Initial hours lookup is supported; the holiday follow-up skips a fresh policy call and repeats a source notice from conversation text. It also emits a wording typo. The product topic switch correctly calls `get_product_details` and reports Takamine price/stock. Qwen's old hours case stopped on local infrastructure, so this is new semantic evidence, not a matched quality improvement. No retrieval noise harm was observed in the successful product switch. |
| Exact freight threshold | Partial | Current retrieval includes the approved clarification. The answer correctly grants free freight at R$500 only for the metropolitan region, but attributes equality to `store_policies.pdf, p. 4`. The automatic consulted-source notice separately identifies the clarification accurately; it does not repair the generated claim's wrong attribution. The policy decision changed since #40, so this is not evidence of a model reasoning fix against the former source. |

The mixed follow-up invents `(67) 3344-5566` and
`atendimento@emporiomusica.com.br`; these strings are preserved as model errors,
not published as store contacts. Its scheduling offer is outside read-only tools.
The hours follow-up's copied source notice is generated prose, not a new tool return
or proof that the application incorrectly reused evidence.

## Usage and scope of claims

- 6 conversations, 12/12 HTTP 200; 2 pass, 3 partial, 1 fail under the review above.
- 23 recorded Bedrock responses; 78,752 input tokens and 2,160 output tokens.
  The recorder's 30 response objects include seven zero-token synthetic assistant
  history messages; do not count those as paid requests.
- Estimated spend **US$0.0131088**, using the same-day verified #40 manifest's
  US$0.15/M input and US$0.60/M output assumptions. This is not an invoice.
- HTTP latency median **1.7705s**, maximum **3.116s**, sum **23.180s**. It excludes
  setup and the warmed E5 preflight and cannot establish a speed/cost advantage.
- No repeat model matrix, provider/framework changes or new runtime enforcement.
  Do not claim these instructions solved all known model failures.

The existing 347-test combined A+B baseline remains the offline application evidence;
no backend source changed here. The local E5 and live samples are additional,
separately identified evidence rather than replacements for those tests.
