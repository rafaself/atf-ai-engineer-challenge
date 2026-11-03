# Context-aware tool use and conditional policy experiment

Production changes for this task are confined to `agent/persona.py`. Tool
signatures, RAG, original policies, pricing, contracts, customer isolation and
model configuration are unchanged. The retained persona permits reuse of sufficient
source-grounded policy context, requests retrieval for missing/ambiguous evidence,
and still requires fresh operational lookups for prices, stock, promotions and
order details. Earlier assistant interpretations do not outrank their sources.

Both proposed improvements were implemented and evaluated separately and together.
The extra conditional-reasoning rewrite did not repair the observed failure, so it
was reverted rather than expanding the prompt further. Existing instructions to
respect conditions/exceptions and disclose uncertainty remain. The success criterion
of correct holiday reasoning is **not achieved**; this report does not claim otherwise.

## Fixed comparison and provenance

The user separately approved **US$0.75**, four variants, two conversations each,
20 maximum HTTP turns. Old spending approvals were not used. Read the frozen
[protocol](protocol.md), exact [variant strings](variants.json), and reusable
[evaluation caller](run_probe.py). Production still uses one STORE_INSTRUCTIONS;
variant substitution occurs only in the evaluation caller before constructing
fresh agents, not through a new application prompt framework.

The historical baseline is `../grounding-followups/qwen-final.json` (source
`3417a1e`). Its prompt matches the baseline variant after the SDK's trailing-newline
normalization. The four newly captured cells use the same source/tools/model,
with only the supplied instruction string changed. Each raw capture records both
source hashes and the actual evaluated instructions; observed request instructions
were checked against their frozen variants. All initial hours searches returned
one chunk, `policy-v2.1-s2`, containing general holiday closure and possible special
Christmas hours. Every first answer preserved both facts in subsequent history.

| Dimension | New baseline | Context only (retained) | Conditional only | Combined |
| --- | --- | --- | --- | --- |
| Initial hours retrieval | Yes, sufficient section 2 | Same | Same | Same |
| Holiday follow-up tool choice | Reused sufficient context | Reused sufficient context | Reused sufficient context | Reused sufficient context |
| Holiday follow-up faithfulness | Fail | Fail | Fail | Fail |
| Product topic switch | Fresh details; requested price/stock correct, unsupported extra PIX claim | Fresh details; requested facts correct | Fresh details; requested facts correct | Fresh details; requested facts correct |
| Missing-policy follow-up | No retrieval; unsupported source | Retrieved 4.1 plus related records; grounded answer | No retrieval; unsupported source | No retrieval; unsupported source |

Tool-use appropriateness and answer faithfulness are independent. Not searching
again for holidays is reasonable here because sufficient context was already
available. Baseline and conditional-only additionally violate their own old fresh-turn
instruction, but that is not the substantive factual failure. All four follow-ups
categorically say Christmas is closed despite the source qualification. The new
baseline also repeats the possible exception inconsistently. The other variants
omit Christmas from their list of possible special dates in that answer. No variant
confirms an actual special schedule; the problem is unsupported definite closure.

The missing-evidence conversation first asks only about Takamine availability,
then asks the online withdrawal deadline. No policy evidence is supplied before
that follow-up. Context-only correctly calls `search_store_policies`, cites section
4.1, gives seven days after receipt, the product conditions and source-supported
refund details. The others give a seven-day interval without retrieving the store
policy and attribute it to an unsupported source/section. The baseline invokes a
legal authority not present in the evidence; this review does not assess that law,
only the absence of grounding and fabricated store-source attribution.

Actual source records and complete final answers remain in:
[baseline](baseline.json), [context-only](context_only.json),
[conditional-only](conditional_only.json), [combined](combined.json).
Historical captures and verdicts are untouched. This is manual source review by
the root coding agent, not an independent human evaluation.

The baseline product-switch answer additionally volunteered that standard and PIX
prices are identical without consulting PIX pricing. That assertion is unsupported
and conflicts with the existing non-promotional PIX rule. This is separate from
the fresh operational lookup, which did happen. Do not count correct requested
price/stock as proof every extra statement is faithful.

## Independent recommendations

- **Context-aware use: retain provisionally.** It expresses the requested contract
  correctly without relaxing operational freshness. In its isolated sample it
  retrieved missing policy evidence while avoiding redundant holiday retrieval
  and performing the product lookup. The baseline already reused holiday context,
  so this does not demonstrate fewer unnecessary calls. The combined cell's miss
  shows the result is not reliable and cannot be causally credited to one edit.
- **Conditional rewrite: revert.** Neither isolated nor combined wording repaired
  holiday interpretation. Keep the existing generic condition/exception safeguards;
  do not retain extra unproven text or introduce holiday-specific patches. A future
  hypothesis requires separate evaluation, not repetition until a favorable answer.

Selecting context-only restores exactly an evaluated variant, rather than creating
an untested final mixture. No more provider calls were made after this decision.
The model still fails the central conditional-policy success criterion. No chunk
change, mandatory retrieval, classifier, semantic output gate or new dependency
is justified by this sample.

## Usage and latency

All 20 HTTP turns returned 200; that is not a semantic pass. Values below reconcile
with [summary.json](summary.json). The upfront worst-case reservation is
**US$0.541440**, below the newly approved US$0.75. Estimated actual total spend is
**US$0.01861515**, using the same-day verified manifest's US$0.15/M input and
US$0.60/M output assumptions; this is not an invoice.

| Variant | Recorded Bedrock responses | Input / output tokens | Estimated USD | Warm HTTP median / max seconds |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 8 | 26,828 / 707 | 0.0044484 | 2.410 / 3.219 |
| Context only | 9 | 31,300 / 656 | 0.0050886 | 2.875 / 5.973 |
| Conditional only | 8 | 27,309 / 626 | 0.00447195 | 1.931 / 2.360 |
| Combined | 8 | 28,112 / 649 | 0.0046062 | 4.417 / 5.269 |

The historical hours sequence took 2.555 / 2.168 / 1.461 seconds for its three
turns; the retained context-only cell took 3.828 / 1.138 / 5.973 seconds. These
single observations include provider variation and do not establish a latency
regression or improvement. E5 is cached/preflighted and HTTP timing excludes setup.
Zero-token synthetic assistant history objects are excluded from provider counts.
All variants ran once in fixed order; no randomization, repeats or significance
claims. No three-model matrix and no automatic retries of failed conversations.

## Offline verification and reproduction

The combined persona passed the existing 356-test offline suite before inference;
Ruff lint/format and strict mypy across 91 files passed. Retained context-only was
then checked again: 356 tests passed in 9.19 seconds; static checks also passed. No fake-model/prose-phrase test was added to claim real reasoning
coverage. No previous assertion or verdict was weakened.

Commands from repository root:

```sh
uv run --project apps/api --locked pytest tests
uv run --project apps/api --locked ruff check .
uv run --project apps/api --locked ruff format --check .
make check-python
```

Any future paid reproduction needs new approval and a fresh output directory:

```sh
PYTHONPATH="$PWD/packages/emporio_music/src:$PWD/apps/api/src" \
HF_HOME="$PWD/data/benchmark-cache/hf" HF_HUB_OFFLINE=1 \
OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 \
uv run --project apps/api --extra policy-rag --locked \
  python docs/examples/context-aware-policy/run_probe.py --live \
  --output-dir /tmp/new-approved-context-comparison
```

Create that directory first. Existing captures are opened exclusively and cannot
be overwritten. The original instruction variants remain available as evidence,
even though the conditional rewrite is no longer the production persona.
