# Policy corpus, runtime retrieval and evaluation protocol

Current processing (2026-11-03): `poppler-reviewed-returns-v9` prepares 29
records with canonical hours, one effective freight section, and structured
online-return conditions/exclusions, applicability, refund facts, explicit
procedure documentation status and source-preserved general contacts. The original PDF and freight approval remain
unchanged; effective freight provenance is stored in `source_references`. The
current labels are `questions-v3.json`; prior label files/captures remain historical.
The application shows policy references and partial-list notices, with one-time
simulation disclosure replacing per-answer snapshot and freight-ingestion notices.
See [data processing decisions](data-processing.md) for the implemented rationale.

Status: US-14 corpus, US-15 retrieval benchmark, US-16 policy tool, and US-17
paired answer review are complete. US-15 met none of the frozen configurations'
full target set; US-17 also found answer and tool-selection failures in both
retrieval and full-policy-context runs. See the [US-17 results](examples/us-17/results.md).
Related: US-14 #50, US-15 #52, US-16 #55, parent #49.

[US-18](examples/us-18/README.md) records the grounding investigation and output
simplification. That version returned source excerpts without section-specific advice;
the current return-contact scope additionally returns reviewed interpretation guidance.
The application appends a “Fontes consultadas” list from successful current-run
records, alongside partial-result notices where relevant. It does not parse
generated citations or currency mentions to decide HTTP success. Generated claims,
references, price presentation and tool choice still require model-quality review.
Exact pricing and customer scope remain enforced inside the operational tools.

The policy tool requires an explicit scope. The retained routing is the baseline:
`online_return` selects 4.1/4.4; `return_contact` selects those sections plus
cover, 1.2 and 7; `preference_exchange` selects 4.3/4.4; `defect` selects
4.2 and 8.1–8.3. The attempted unified scope and shorter instructions were not
retained after controlled runs failed to improve grounding and regressed Qwen
follow-ups. See the v9 comparison below rather than treating simplification as
proven improvement.

The retained source improvement replaces an empty next-step list with explicit
`procedure` documentation statuses, bound to a full-manual review and its PDF
hash. Contact entries retain their exact values, roles and section/page references.
Both email spellings remain unresolved; section 7 explicitly designates a primary
remote WhatsApp channel. Missing documentation is not proof of unavailable service
or of no requirements. Existing source excerpts remain unchanged.

The model still chooses tools and authors prose. No semantic validator, additional
model stage or retry/fallback mechanism was added. Existing output checks protect
presentation and append consulted sources without certifying answer truth.

For `general` scope, the policy tool uses the current question plus the latest prior user question
when their combined text is at most 256 characters. A bounded local E5 check missed
section 4.1 for “E se eu já usei o instrumento?” alone, returning sections 1.1, 10,
8.3, 4.2, 8.1 and 8.2. Adding the preceding return question returned sections 4.4,
4.1 and 4. An unrelated prior hours question also added section 2 to a return query,
so this limited context can introduce irrelevant sections. These checks assess
retrieval only, not generated answers or live Qwen behavior. Frozen US-15 targets
remain unmet; sprint closure does not require RAG to outperform Full Context.

The latest approved current-code batch stopped at its first mixed turn: both tools
returned evidence, but the citation-format retry was exhausted and HTTP 500 resulted.
The five remaining planned turns were not run. See the
[batch review](examples/us-18/results.md#finding-5-authorized-current-code-grounding-batch)
for partial grounding and citation-format findings.

## Full-source return review (2026-11-03)

The reviewed v9 metadata supersedes v7's empty next-step list. The v8 routing
and advisory strings remain after the unified-scope candidates failed evaluation. Source excerpts and pages remain unchanged. The full eight-page
manual was checked, including outgoing shipment tracking, complaint escalation,
and final management-consultation guidance. None specifies return paperwork,
label issuance, posting instructions, a dedicated returns SAC, or the starting
event of the ten-business-day refund period. Those findings are preparation-time
facts bound to the reviewed source SHA-256. A different source requires review
before those facts can be regenerated. No claim is made that those services or
requirements cannot exist outside this manual.

The metadata participates in the existing corpus fingerprint. The local index
must be rebuilt even though the embedding text itself did not change. See the
[controlled v9 comparison](examples/model-comparison/grounding-v9-2026-11-03.md)
for separate correctness, tool-use and UX results.

## Reproduce offline

Install system Poppler (`pdftotext`; development preparation prerequisite), then
from the repository root run:

```bash
uv run --project packages/emporio_music --locked python -m emporio_music.policies.corpus
uv run --project apps/api --locked pytest tests/test_policy_corpus.py
```

The command updates the derived corpus and freeze hashes reproducibly. It verifies `data/store_policies.pdf` against `data/SHA256SUMS`, invokes
Poppler layout extraction, applies the versioned freight clarification and the
source-grounded Natal-hours interpretation, then writes `data/policies/corpus.json`.
`freeze.json` keeps a separate hash for the freight clarification source and a canonical
hash for the effective records. The current benchmark reads the
versioned `questions-v3.json`, whose clarification hash and q13 evidence label include
the approved rule. The original `questions.json` and its hash remain frozen for earlier
benchmark captures. No credentials, model downloads, network, or new Python dependencies
are needed.
It is never invoked by application startup. Missing Poppler/extraction failure is
an error, not an empty corpus. The source is never modified.

## Runtime retrieval (US-16)

Install the opt-in runtime libraries with:

```bash
uv sync --project apps/api --locked --extra policy-rag
```

The default dependency set remains unchanged. Before answering policy questions,
explicitly build the ignored E5 Chroma collection:

```bash
uv run --project apps/api --extra policy-rag --locked \
  python -m emporio_music.prepare_policy_index --allow-download
```

The freight clarification changes the effective corpus and index fingerprint. Any
previous `policy-e5` collection is therefore stale; rebuild it with `--rebuild`
before using the updated corpus. Use `--rebuild` only for an intentional replacement;
keep `--allow-download` only when you intend to fetch the pinned local E5 weights.

This command may download the pinned `intfloat/multilingual-e5-base` weights after
the explicit `--allow-download` flag and builds `data/policy-indexes/policy-e5`.
It does not run a retrieval benchmark or write a benchmark report. Generated weights
and index data are ignored. The application never downloads weights or builds/rebuilds the index;
on the first policy-tool use it opens the existing collection and loads only cached E5
weights on CPU (`local_files_only`). A missing or stale corpus, model or index raises a
retrieval error surfaced through the existing sanitized HTTP 503 contract. It is never
reported to the customer as “no policy found.”

The runtime verifies the PDF hash, separately versioned freight-clarification hash,
canonical corpus hash, parser version, index fingerprint and exact indexable record
IDs. It embeds the bounded policy query with
E5's `query:` prefix and uses the same query-derived family filter rule as US-15,
retrieves the three highest-ranked seeds, and adds only the authored one-hop
relationships from the fixed manual, capped at eight records. Each excerpt includes
its source, section hierarchy and physical page when the source has one. The approved
freight clarification is a separate record sourced from
`data/policies/freight-clarification.json`; it references section 5.1 but has no PDF
page because its wording is not in the original manual. Customer answers cite available
references in readable form; the application independently lists consulted
sections/pages.
The model should explain the applicable conditions when presenting a policy amount. Retrieved text
is data, not an instruction source. The product, pricing and customer-order tools remain
separate and deterministic. `search_store_policies` takes no model-selected query:
the application may append the latest prior user question to the current question,
but excludes assistant text, tool results, identity and labels. The combined text is
bounded to 256 characters; longer combinations use only the current question. This
addresses the recorded short follow-up miss without a query-rewriting model or changes
to ranking and expansion. The contextual check is exploratory; it does not change
frozen labels or US-15 metrics.

The search has no calibrated similarity threshold. A non-empty nearest-neighbor result
is a candidate, not proof that it answers the question. If the excerpts do not directly
support a claim or leave an eligibility fact unresolved, the persona must state that the
retrieved evidence is insufficient, ask for missing customer facts where useful, and
avoid claims based on the manual's silence. An empty successful result is marked
`insufficient_evidence`; model/index errors remain operational failures. US-15 found no
configuration meeting every frozen target, so E5 with metadata filtering and this bounded
expansion remain provisional. The prior full-policy-context comparison did not establish
reliable answers either. US-17 reviewed four real conversations in both modes. The RAG arm
returned one HTTP 500, and both modes missed a required policy-tool call in the mixed-order
case. Full details, including failures, are in the [paired results](examples/us-17/results.md).
These controls, offline tests and eight observed route calls do not establish future
generated-answer quality.

## Preparation decisions

The fixed v2.1 manual has 8 physical pages and 28 numbered sections. A compact page-1
contact record preserves the cover email discrepancy, giving 29 PDF-derived records.
Each numbered section is one chunk; parent headings are attached as hierarchy, not
duplicated body text. Heading-only parent sections 5, 6 and 8 remain as
provenance-bearing records with `indexable=false`; the 26 remaining PDF-derived records
are indexable. The approved freight clarification adds one separate, indexable record,
for 30 effective records and 27 indexable records total. Cover branding is omitted, but
the contact line is evidence and retains its original spelling and physical page
reference. Repeated page
headers, footers and final branding/version lines are omitted. Wrapped prose and list
continuations are joined, repeated whitespace and invisible zero-width spaces are
removed. The four tables become explicit header-labeled rows, including wrapped cell
values, so conditions remain attached to their payment/delivery row. Column boundaries
derive from the first complete data row. Each of the four known table sections must
contain exactly one table with the expected headers and row count; missing recognition
fails instead of flattening the table into prose. This is specific to the reviewed
manual, not a general PDF table parser. Physical PDF pages are numbered from 1. Sections
5.2, 7.2 and 9 span pages; their content is joined without page furniture. A deterministic
overlay adds the owner-approved equality rule as a separate record rather than rewriting
section 5.1. Its source hash participates in the freeze and index fingerprint. No other
overlap is used: duplicating short rules would inflate relevance counts. Unexpected section
structure or changed source bytes fails for explicit review. Poppler version is recorded
because extraction can vary by version. Semantic corpus comparison excludes that
provenance field: an identical corpus from a different Poppler release is acceptable;
changed content still fails.

No oversized section currently needs splitting. US-15 must count the complete hierarchy
plus text with each actual tokenizer, including query/document prefixes, before
indexing. Never silently truncate: if any model limit is exceeded, revise chunks and
labels together and create a new frozen corpus before comparisons. Stable section IDs
identify this manual version; source hash and parser version must also accompany future
indexes. The freeze records canonical chunk content hashes to detect extraction drift
independently of the installed Poppler version. The dataset hash freezes evaluation
questions/labels. Documentation is reviewed through Git changes rather than a prose-file
hash requiring refresh for every edit.

## Ambiguities and source authority

- Company table and WhatsApp section differ in contact number; cover and table
  also differ in email spelling. Present the discrepancy; do not choose an
  authoritative contact without clarification.
- Payment table gives a general installment minimum while subsection 3.1 gives
  tier-specific conditions. Explanatory answers should retrieve both and qualify
  the discrepancy. The deterministic quote tool follows the specific per-range
  terms in 3.1 and includes the conflicting general minimum in its result; this
  records its calculation basis without claiming the source conflict was resolved.
- The original PDF's local freight clause specifies above/below a threshold but not
  equality. Owner-approved Workstream A in #43 resolves equality: for deliveries in
  the Região Metropolitana de Campo Grande, totals below R$ 500,00 cost R$ 35,00 and
  totals at or above R$ 500,00 are free. The separate clarification source preserves
  this new decision without attributing its wording to the PDF. Historical US-15 and
  benchmark captures remain evidence against the earlier ambiguous source; their
  questions, labels and results are unchanged.
- Section 2 gives regular Sunday/holiday closure and separately says Natal hours may
  be extended. Corpus processing makes that relationship explicit: the manual does
  not establish whether the store is open or closed on a specific Natal; any change
  is to be announced in advance. This interpretation is derived from the unchanged
  PDF and retains its section 2, page 2 provenance.
- Return eligibility needs channel, actual receipt, condition and exclusions;
  imported order status alone does not establish these. Warranty statements are
  manual claims, not independently verified legal advice.
- Campaign descriptions do not establish current promotions. Operational tools
  remain authoritative for active offers and amounts. Procedures about forwarding
  complaints do not grant the agent capabilities to perform those actions.

## Deterministic quote and deadline sources

Issue #85 adds typed calculations beside retrieval. Quote results identify policy
sections 3.1, 5.1/5.2 and the separately approved freight clarification. The
R$ 500,00 equality rule is confirmed for Campo Grande metropolitan freight, but the
manual does not define whether the threshold uses original or discounted totals;
quotes return a freight amount only when those two bases agree. Mixed payment is
allowed only above R$ 2.000,00; neither the threshold basis nor an extra PIX discount
for mixed tender is specified, so those cases remain qualified in the tool result.

Deadline results identify sections 4.1, 4.2, 5.1/5.2 or 8.1. Current orders do not
store dispatch or actual-receipt dates, and estimated delivery never supplies either
event. The ten-business-day refund period has no documented start event. Business-day
delivery estimates exclude weekends and state that public holidays are not modeled.
These outcomes preserve source uncertainty rather than expanding the retrieval
corpus or fabricating operational facts.

## Frozen evaluation, before tuning

`data/policies/questions-v2.json` has 25 Portuguese questions: 16 development and
9 validation, with required evidence groups, topic, expected response behavior
and critical flags. Each group contains acceptable alternative chunk IDs; current
labels use one ID per group. Multiple groups require all evidence. Unsupported
cases have zero groups. Labels derive from source rules, not retrieved rankings.
Its q13 gold evidence points to the approved freight clarification and its expected
behavior is to state the resolved conditions. The original `questions.json` remains
the v1 dataset used by historical benchmark captures; its q13 still labels section
5.1 as a gap, matching the unresolved source at that time. New runs use the version
and source hash recorded in `freeze.json` and verify the clarification hash in the
current dataset.
Validation cases are authored/visible for review but must not be used to tune
retrieval. Record any later inspection of their results before final evaluation
as contamination; report exploratory results rather than claiming a blind test.
This small hand-authored set cannot establish broad model quality.

For each answerable case, Recall@K is the fraction of required groups hit by the
first K unique chunk IDs (a group is hit by any acceptable alternative). MRR@5 is
the reciprocal rank of the first relevant chunk, or zero. Report macro means and
case/group denominators for development and validation separately. Coverage@5 is
the fraction of multi-group cases where every required group is hit. Empty-gold
cases are excluded from retrieval metrics; generation must decline unsupported
claims, judged separately against the behavior label. Nearest neighbors alone
cannot prove answerability. Document missing customer facts versus missing policy.

Preselected adequacy targets on each split: Recall@3 >= 0.80, Recall@5 >= 0.90,
MRR@5 >= 0.80, multi-group coverage@5 = 1.00, and all required groups retrieved
at 5 for every critical case. Unsupported generation cases must contain no
invented policy; report counts and reviewed explanations, not a retrieval score.
These are challenge acceptance targets, not statistical confidence guarantees.
Do not lower them after viewing results. If no configuration passes, preserve
failures and review a bounded next change. Filters must derive only from query
text, with the same rule across configurations, and cannot use gold labels.

## Permission and later work

Source provenance and original checksums are in `data/README.md`. On 2026-11-01, the
owner confirmed the manual is fictional and approved versioning the extracted corpus;
the original PDF stays unchanged. Raw layout output is reproducible with
`pdftotext -layout` and need not be tracked. Normalization removes PDF presentation
noise and makes table relationships explicit for retrieval and lower-cost generators.
No quality improvement is claimed from that choice. The owner separately approved the
US-15 fictional-data Titan V2 benchmark in `us-east-1` with a total paid-run cap of US$1.
US-16 runtime embeddings use local E5. For US-17, the owner separately approved four
paired Qwen3 32B conversations in `us-east-1`, capped at US$0.50. The recorded cost
estimate, including a worst-case reserve for the failed call, is US$0.0573106 under the
stated token-rate assumption; this is not an invoice. No Cohere calls were made. Any new
external processing or paid runs require their own explicit authorization and bounded
scope. Existing section IDs and gold labels remain unchanged; the cover contact has its
own ID.

## Structured online-return evidence

Preparation attaches `online_return_rule` to section 4.1: seven calendar days
is the request deadline after actual receipt, with zero minimum wait. It records
online purchase, actual receipt, original packaging, no signs of use, accessories,
and manuals, plus section 4.4 exclusions (customization/setup, explicitly final-sale
clearance, and wind-instrument mouthpieces). Runtime retrieval passes this prepared
metadata through with the source text. It is not a customer eligibility decision.

Earlier source/benchmark descriptions in this guide retain their historical scope;
the current processing contract is documented above and in data-processing.md.
