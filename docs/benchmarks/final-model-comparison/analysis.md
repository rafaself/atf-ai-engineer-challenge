# Execution and AI assessment — issue #82

## Recommendation and its scope

**Retain GPT-6 Luna provisionally.** In this single captured pass, Luna and Sol
both scored 16/16 Pass, completed 26/26 HTTP turns, and had no observed critical
errors or customer-boundary violations. Neither had a missing required current
read or wrong argument in the assessed conversations. Luna wins §8's cost
tiebreak: main-run estimated cost US$0.0193957775 versus Sol US$0.38154490,
approximately **19.67 times lower**. USD per Pass is US$0.00121223609375 versus
US$0.02384655625. This does not authorize or require a runtime-default change.

Sol's observed median was lower: 4.818 seconds versus Luna's 5.406 seconds.
Luna also had a 20.982-second maximum versus Sol's 10.058 seconds. These are
attempted HTTP-turn timings on one shared host, including tool execution;
they do not establish a latency distribution or statistical superiority.

The other eight candidates fail the frozen eligibility gates. Haiku had
12 Pass / 3 Partial / 1 Fail, including one critical monetary inference;
Nemotron Super had 12 / 2 / 2, with two critical conversations. Lower raw
token prices or a faster median do not compensate for a failed correctness
gate. See the complete [scorecard and scenario matrix](results.md).

These are **AI judgments**, not human-reviewed findings. The owner authorized
Codex to assess the already-completed capture and waived the independent human
review requirement. The assessment is unblinded, performed by the implementing
assistant, without an independent second reviewer. The exact amendment and
unchanged rubric are in [protocol §11](protocol.md#11-owner-amendment-v13--after-capture-2026-11-03).
No judging API calls, prompt tuning, substitution or additional paid reruns
were performed. Later human review may change the judgments.

## Average cost per interaction

A **model interaction** here is one captured model response to a prompt,
including tool-call responses. A user chat turn can require several such
interactions. The first average is estimated main-run USD divided by captured
model responses; the second divides the same cost by 26 attempted chat turns.
Both exclude preflight and include failed-call costs and unknown-usage
reservations, amortized across the denominator. These are observed workload
averages, not fixed prices for future prompts.

| Model | USD per model interaction (prompt + response) | USD per attempted chat turn |
| --- | ---: | ---: |
| nova_micro | 0.00015637 | 0.00036086 |
| nova_lite | 0.00026907 | 0.00068302 |
| nemotron_nano_3_30b | 0.00025071 | 0.00041463 |
| nemotron_super_3_120b | 0.00065027 | 0.00130054 |
| gpt_oss_20b | 0.00022581 | 0.00048637 |
| gpt_oss_120b | 0.00047980 | 0.00095959 |
| qwen3_32b | 0.00055973 | 0.00105488 |
| claude_haiku_5_5 | 0.00072791 | 0.00148382 |
| gpt6_luna | 0.00035265 | 0.00074599 |
| gpt6_1_sol | 0.00693718 | 0.01467480 |

## Capture integrity, interruption and accounting

Measurement ran 2026-11-03, from 15:48:21 to 16:12:30 UTC, against clean commit
`fb13623b6e0b161db05c671044705c9b6b4ff891`. The capture records 75 application
source files, all supplied data/policy hashes, the rebuilt policy-index tree,
and cached E5 revision `d128750597153bb5987e10b1c3493a34e5a4502a`.
The pre-existing stale index was backed up and explicitly rebuilt from the
current reviewed corpus before the measurement freeze; no weights were
downloaded and no embedding-provider call was made.

The owner's concurrent README edit triggered the clean-tree guard. Their
explicit waiver permitted continuation. The resume used an isolated checkout
at the **same measurement commit**, with exact equality of frozen source,
data, policy-index and E5 evidence. No model prompts, tools or limits changed.
The original 519 provider attempts remain an identical prefix of the final
565-attempt ledger, and all previously attempted conversations were skipped.
The original US$0.5453514825 ledger was carried forward, not added a second time.
The interrupted GPT-OSS 120B case was retained as an execution failure and
was not retried. `resolved_control_stops` records this lineage.

| Accounting item | Observed value |
| --- | ---: |
| Planned / attempted main HTTP turns | 260 / 260 |
| Completed / failed main HTTP turns | 255 / 5 |
| Completed / planned conversations | 155 / 160 |
| Not-executed main HTTP turns | 0 |
| Provider attempts, preflight / main / total | 22 / 543 / 565 |
| Recorded main model responses | 541 |
| Estimated preflight USD | 0.019167090 |
| Estimated main USD, including missing-usage reservations | 0.5762774175 |
| Total estimated USD | **0.5954445075** |
| Missing-usage requests / retained USD reservation | 2 / 0.00197048 |
| Explicitly approved cap / worst bounded envelope USD | 10.00 / 9.81175456 |

The missing-usage reservations are Nova Micro US$0.00074858 and Nova Lite
US$0.0012219. They remain included even though billed usage is unknown.
Recorded cache-read tokens are conservatively billed at uncached input rates;
cache-write premiums are included. Input counts include base input, cache reads
and cache writes exactly once. These are rate-based estimates, not an AWS
invoice. Never add `capture-interrupted.json` spending to the final ledger.

Final capture SHA256:
`e9c7b2dc44175c4b5ff9af4511925ce96563434d00e8198fe39ba245639a85c1`.
Interrupted capture SHA256:
`0c0438d219dc7ac59939c3aee3474ffca35462834fb936c7a6105733d8e72009`.
Both files were copied without reserializing or altering their bytes.

## Execution failures, separate from semantic scores

All ten preflights completed a real tool roundtrip over Runtime Converse,
including both NVIDIA routes. Seven candidates completed all 26 main turns;
Nova Micro and GPT-OSS 120B completed 25, Nova Lite 23. Five conversations have
**no Pass/Partial/Fail judgment** because one planned turn failed:

| Candidate | Scenario / turn | HTTP | Cause and attribution |
| --- | --- | ---: | --- |
| Nova Micro | final-order-total-vs-unit / 1 | 503 | Provider `ServiceUnavailableException`; unknown usage reservation retained |
| Nova Lite | named-stock-alternative / 2 | 500 | Local agent execution / `UnexpectedModelBehavior` / `ModelRetry`; trace attempted alternatives for nonexistent product ID 12345 |
| Nova Lite | promotion-pix / 2 | 503 | Provider `ModelErrorException`; unknown usage reservation retained |
| Nova Lite | final-online-return-missing-accessory / 2 | 500 | Local agent execution / `ToolRetryError` / `ModelRetry` |
| GPT-OSS 120B | final-order-total-vs-unit / 1 | 500 | Local `BudgetFault` source-freeze guard before provider transmission, caused by concurrent README edit; **not a model defect** |

Per-turn failure categories, exception chains and successful earlier turns
remain in [capture.json](capture.json). Local/provider failures were not silently
replaced, converted to quality failures or retried to improve reliability scores.

## How the semantic judgments were made

Each of the 155 completed conversations was inspected with its questions,
full answers, actual tool arguments/results and the frozen scenario rubric.
The authority is the supplied operational snapshot and effective store policy,
not general retail practice or external legal assumptions. A correct fact with
a missing required refresh can remain Pass while the tool diagnostic records
the missed read. Failed conversations are excluded from semantic diagnostics.

Judgment choices requiring later human attention are explicit in
[ai-review.json](ai-review.json):

- A historical order total is not a historical unit price, even with quantity
  one or an equal current catalog price. Six completed candidates' final
  order-total cases made this critical inference; Luna and Sol preserved the
  missing item-price field. Haiku acknowledged the absent field but then said
  quantity one made the total correspond to the item value, producing a
  contradictory monetary explanation.
- Store policy describes original packaging, no signs of use, all accessories
  and manuals. It does not require a sealed box, prohibit all testing, specify
  a return-label workflow, identify a returns SAC, or set the start of the
  ten-business-day refund clock. Invented requirements/procedures are critical;
  unresolved contact variants presented as a single authoritative email are
  Partial. General contact values can be supported by the structured policy
  procedure payload even when the displayed record list contains only return
  sections; their mere presence is not an invention.
- Missing one included accessory is an unmet return condition. Nova Micro
  nevertheless promised label generation; GPT-OSS models invented workflow
  details, while Luna and Sol declined approval and explained the source limit.
- Product references resolve against the assistant's actual preceding list.
  Qwen's ordinal-as-ID promotion lookup and singular `Baixo` category produced
  false availability claims. Nova Micro's bass follow-up relabeled a standard
  quote as a PIX price despite a correctly routed lookup. These are critical.
- Missing requested product codes are Partial. Wrong optional material specs
  are noncritical Fail. A harmless redundant read or verbosity alone does not
  change the semantic verdict. Sourced extra PIX information for the first bass
  remains correct, while the deviation from its prescribed standard-payment
  tool argument is recorded separately for GPT-OSS 20B and Haiku.
- Christmas results preserve the conditional holiday exception; no candidate
  invented confirmed opening or closure at 10:00 in the dedicated Christmas
  case. GPT-OSS 20B is Partial because it omits the separate WhatsApp-hours
  answer. All other nine pass that case.

No customer-boundary violation was observed in the completed conversations.
The guest-order scenario was correctly protected; Nano's unnecessary order-ID
clarification was Partial for not following the demo-selection guidance.

UX notes remain case-linked rather than forming an invented composite score:
Nano repeatedly asked for unnecessary internal/order details; GPT-OSS 20B exposed
English planning in some answers; Haiku's first used-item response truncated
midword, but its complete two-turn conversation supplied the needed conditions.
Luna's three and Sol's one redundant reads affect efficiency, not their verdicts.

## Later human review

[review.json](review.json) contains 160 original blank primary/second/resolution
rows, with execution status already recorded.
[review-worksheet.json](review-worksheet.json) contains shuffled candidate aliases
and sanitized captured evidence. The private operator alias map is kept outside
Git in ignored local benchmark-cache storage. AI assessments use public model
keys and a separate identity map, leaving the human candidate map unpublished.
Providing raw answers or this report to later reviewers may enable deblinding;
do not represent that later review as blinded without checking their exposure.

Default reporting still enforces independent human second reviews for
Partial/Fail/critical findings. The explicit AI mode is separately authorized,
labeled and tested; it never fills a human row or invents a second reviewer.

## Validation

The measurement implementation passed the complete workspace check before the
run (396 backend tests and 6 CLI tests). The reporting amendment adds one
regression test for explicit AI opt-in, preserved human forms and unchanged
critical-error/Pass gates. The implementation was already present when that
test was added; a failing pre-implementation baseline was not demonstrated.

Final post-report validation and detailed diagnostic tables follow below.

## Grounding and tool diagnostics

Counts below apply to the completed conversations only. Critical conversations
and distinct recorded critical findings have separate denominators. Tool
diagnostics include missing required refreshes even when the answer stayed correct.

| Model | Critical conversations / completed | Critical findings | Unsupported claims | Missing reads | Wrong arguments | Redundant calls | Eligible |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nova_micro | 4 / 15 | 5 | 5 | 4 | 3 | 3 | no |
| nova_lite | 5 / 13 | 6 | 8 | 1 | 3 | 1 | no |
| nemotron_nano_3_30b | 6 / 16 | 11 | 14 | 16 | 1 | 2 | no |
| nemotron_super_3_120b | 2 / 16 | 2 | 4 | 5 | 0 | 1 | no |
| gpt_oss_20b | 4 / 16 | 8 | 9 | 3 | 1 | 3 | no |
| gpt_oss_120b | 4 / 15 | 9 | 12 | 2 | 0 | 2 | no |
| qwen3_32b | 4 / 16 | 4 | 8 | 8 | 3 | 0 | no |
| claude_haiku_5_5 | 1 / 16 | 1 | 2 | 1 | 1 | 0 | no |
| gpt6_luna | 0 / 16 | 0 | 0 | 0 | 0 | 3 | yes |
| gpt6_1_sol | 0 / 16 | 0 | 0 | 0 | 0 | 1 | yes |

## Model execution and cache detail

| Model | Main responses / provider attempts | Output-validation retries | Cache read / write tokens | Reported reasoning tokens | Main USD / Pass |
| --- | --- | --- | --- | --- | --- |
| nova_micro | 60 / 61 | 0 | 0 / 0 | 0 | 0.00156373 |
| nova_lite | 66 / 67 | 0 | 0 / 0 | 0 | 0.00253694 |
| nemotron_nano_3_30b | 43 / 43 | 0 | 0 / 0 | 0 | 0.00539025 |
| nemotron_super_3_120b | 52 / 52 | 0 | 0 / 0 | 0 | 0.00281785 |
| gpt_oss_20b | 56 / 56 | 0 | 0 / 0 | 0 | 0.00114960 |
| gpt_oss_120b | 52 / 52 | 0 | 0 / 0 | 0 | 0.00277215 |
| qwen3_32b | 49 / 49 | 0 | 0 / 0 | 0 | 0.00391811 |
| claude_haiku_5_5 | 53 / 53 | 0 | 0 / 0 | 0 | 0.00321495 |
| gpt6_luna | 55 / 55 | 0 | 96829 / 43765 | 0 | 0.00121224 |
| gpt6_1_sol | 55 / 55 | 0 | 98092 / 44558 | 0 | 0.02384656 |

Reported reasoning-token zero means no separate reasoning usage was reported,
not proof of absent internal reasoning. Application-level output-validation
retry counts are zero; failed tool argument/validation chains are still
preserved as failures in the raw trace. Serialized settings show the same
1,024-token ceiling, while the SDK omitted unsupported temperature parameters
for Haiku, Luna and Sol. The comparison therefore reflects actual adapter/model
behavior rather than pretending all candidates support identical decoding.

## Final verification

- `make check` passed after the reporting amendment: **397 backend tests and
  6 CLI tests**, including all 16 focused benchmark cases; Ruff, formatting,
  strict mypy, three package builds, frontend lint/typecheck/build passed.
- A sandboxed focused run stalled at the SDK/TestClient roundtrip and was
  terminated; the complete run outside that sandbox passed all those cases.
  No test was weakened or skipped.
- Existing frontend installation reports **10 moderate npm advisories**;
  dependency files were not changed by this work.
- All seven supplied CSV/PDF checksums passed. Published JSON, artifact links,
  final/partial capture lineage, exact ledger sum, blank human forms and report
  regeneration were checked. No generated database, index, local environment
  file or private human alias map is included in the delivery.
