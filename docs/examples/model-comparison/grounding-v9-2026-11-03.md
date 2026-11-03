# Minimal grounding improvement — controlled v9 evaluation

The retained change improves the prepared evidence contract. It replaces an empty
return-step list with explicit full-manual documentation statuses and verbatim
contact entries with roles and provenance. Original instructions and tool routing
were restored after the prompt/scope candidates failed to improve grounding.
There is no semantic validator, new agent/dependency, extra inference stage,
or retry/fallback mechanism.

## Source review and retained behavior

The complete eight-page supplied PDF was reviewed, including outgoing shipment
tracking (5.2/5.3), complaint handling (7.3) and management consultation (10).
The manual does not specify return paperwork, label issuance, posting steps, a
dedicated returns SAC, or the event that starts the ten-business-day refund clock.
Preparation records these as unknown from the manual, not as no requirements or
unavailable service. Negative findings require the exact reviewed PDF SHA-256;
a new source cannot inherit the findings without review.

Contact values are extracted from cover, 1.2 and 7 without normalization. Both
email spellings remain unresolved. The company phone/WhatsApp and the explicit
primary remote WhatsApp have distinct recorded roles; different numbers do not
prove either invalid. Each entry retains section and page references.

All 29 original excerpt texts and page lists, and all seven supplied CSV/PDF files,
are unchanged. The metadata participates in the existing corpus fingerprint.
The derived corpus/freeze and ignored local E5 index were rebuilt together; the
embedding text is unchanged. See [data processing](../../data-processing.md).

## Controlled comparison

The [frozen fixture](scenarios-grounding-v9.json) has six conversations and eight
HTTP turns per model. It covers an initial documents/label question, the same
question after a policy primer, contact authority, legitimate eligibility/refund
questions, a direct address/WhatsApp question, and an undocumented refund-clock
starting event. Expected facts and separate correctness/tool/UX dimensions were
written before the baseline calls. All four arms share the scenario hash and
model settings; temperature is zero. Each arm starts new conversation storage.

| Arm | Qwen pass / partial / fail | GPT-OSS pass / partial / fail | Decision |
| --- | ---: | ---: | --- |
| Current baseline | 1 / 4 / 1 | 0 / 1 / 5 | Control |
| Reviewed data + unified scope + shorter instructions | 1 / 2 / 3 | 0 / 1 / 5 | Reject |
| Same data/scope + explicit fresh-policy/no-typical-procedure wording | 1 / 3 / 2 | 0 / 1 / 5 | Reject |
| Reviewed data only; baseline instructions/routing | 1 / 4 / 1 | 2 / 0 / 4 | Retain evidence-contract improvement |

The capture named `final` is the rejected last prompt variant, **not** the
delivered runtime. The delivered runtime corresponds to `source-only`.

The unified scope returned extra contact excerpts on eligibility-only requests.
Both prompt variants left GPT-OSS's fabricated label workflow intact
and Qwen skipped two follow-up policy reads. One variant also asked for an exact
receipt date despite the customer already saying yesterday. Stronger wording
did not repair these behaviors. The reverted changes are preserved as patches.

In the retained source-only arm, GPT-OSS preserved both email spellings in the
contact-authority answer and answered the direct primary-WhatsApp question
correctly. Qwen's conversation verdict distribution was unchanged. A general
contact suggestion for a question/request is accepted unless it promises
specialized fulfillment; route naming alone never determines factual failure.

These are exploratory single runs of a deliberately difficult subset. The direct
general-contact question uses unchanged evidence, so its GPT-OSS improvement
cannot confidently be attributed to the new metadata. The multi-turn histories
are produced by each arm, not identical seeded messages. Thus the comparison
tests actual conversational behavior but does not isolate history contamination
causally. Zero temperature does not make these runs a statistical reliability
estimate. No overall model ranking or solved-grounding claim follows.

## Correctness, tools and UX

| Metric | Qwen baseline → retained | GPT-OSS baseline → retained |
| --- | ---: | ---: |
| Successful HTTP turns | 8/8 → 8/8 | 8/8 → 8/8 |
| Provider attempts | 15 → 15 | 18 → 17 |
| Turns without current policy read | 1 → 1 | 0 → 0 |
| Additional policy calls beyond one per turn | 0 → 0 | 2 → 1 |
| Recorded corrective retry parts | 0 → 0 | 0 → 0 |
| False refusals / unnecessary clarifications | 0 / 0 → 0 / 0 | 0 / 0 → 0 / 0 |
| Median end-to-end seconds | 1.745 → 1.740 | 3.034 → 3.521 |
| Mean answer words, excluding source footer | 87.0 → 99.8 | 167.5 → 170.6 |

All four arms completed 64 HTTP turns with HTTP 200 and no missing usage or
corrective retries. The retained arm does not establish a latency or conciseness
gain. Latency includes local initialization/tool work, with only eight samples
per model/arm. Lower request counts in rejected variants partly reflect skipped
necessary reads, so are not treated as a reliability improvement.

Remaining errors are consequential. Both models still invent the refund-clock
start; GPT-OSS still supplies undocumented documents and label promises, while
Qwen still turns unspecified paperwork into no paperwork required. The source-only
Qwen follow-up mentions the email spelling variation without listing both values;
its contact-authority answer omits the alternative spelling. This task did not
add a speculative semantic validator to hide these limitations.

## Validation and evidence

The new full-manual metadata regression was observed failing with missing
`procedure` before implementation, then passing. Tests protect full-review hash
binding, unknown-versus-no-requirements semantics, contact values/roles/provenance,
and separation of invented assistant history from current tool evidence. The
fake-model history test proves wiring, not actual reasoning; real multi-turn
cases above assess model behavior. Backend suite: **376 passed**. Ruff lint and
formatting, strict mypy (50 source files), source checksums and diff checks passed.

- [Baseline capture](capture-grounding-v9-baseline-2026-11-03.json)
- [Rejected unified-scope capture](capture-grounding-v9-revised-2026-11-03.json)
- [Rejected stronger-prompt capture](capture-grounding-v9-final-2026-11-03.json)
- [Retained source-only capture](capture-grounding-v9-source-only-2026-11-03.json)
- [Separate metrics](grounding-v9-metrics-2026-11-03.json)
- [First-candidate patch](grounding-v9-first-candidate.patch)
- [Rejected prompt patch](grounding-v9-rejected-prompt.patch)
- [Retained source-only patch against the baseline](grounding-v9-retained.patch)

Each capture contains unchanged prompts, responses, tool messages and source
hashes, plus manual judgments. Review does not infer correctness from HTTP success
or consulted-source footers.

Estimated spend for these four paired arms: **US$0.07030260**. Previous cumulative
spend was US$0.31054065; cumulative is now **US$0.38084325 of US$1.00**, leaving
US$0.61915675. Every arm used a US$0.30 conservative per-turn reservation cap;
the later arms used the actual remaining cumulative approval. These are token
estimates, not an invoice. No credentials were inspected or printed.
