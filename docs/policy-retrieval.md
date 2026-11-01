# Policy corpus and evaluation protocol (US-14)

Status: local corpus preparation only; no embeddings, index or agent integration.
Related: #50, parent #49. Changes are intentionally uncommitted.

## Reproduce offline

Install system Poppler (`pdftotext`; development preparation prerequisite), then
from the repository root run:

```bash
uv run --directory apps/backend --locked python -m emporio_music_backend.policy_corpus
uv run --directory apps/backend --locked pytest tests/test_policy_corpus.py
```

The command verifies `data/store_policies.pdf` against `data/SHA256SUMS`, invokes
Poppler layout extraction and writes versionable `data/policies/corpus.json`.
No credentials, model downloads, network, or new Python dependencies are needed.
It is never invoked by application startup. Missing Poppler/extraction failure is
an error, not an empty corpus. The source is never modified.

## Preparation decisions

The fixed v2.1 manual has 8 physical pages and 28 numbered sections. A compact page-1
contact record preserves the cover email discrepancy, giving 29 records total. Each
numbered section is one chunk; parent headings are attached as hierarchy, not duplicated
body text. Heading-only parent sections 5, 6 and 8 remain as provenance-bearing records
with `indexable=false`; US-15 must exclude those three from embeddings/search. The
remaining 26 records are indexable. Cover branding is omitted, but the contact line is
evidence and retains its original spelling and physical page reference. Repeated page
headers, footers and final branding/version lines are omitted. Wrapped prose and list
continuations are joined, repeated whitespace and invisible zero-width spaces are
removed. The four tables become explicit header-labeled rows, including wrapped cell
values, so conditions remain attached to their payment/delivery row. Column boundaries
derive from the first complete data row. Each of the four known table sections must
contain exactly one table with the expected headers and row count; missing recognition
fails instead of flattening the table into prose. This is specific to the reviewed
manual, not a general PDF table parser. Physical PDF pages are numbered from 1. Sections
5.2, 7.2 and 9 span pages; their content is joined without page furniture. No overlap is
used: duplicating short rules would inflate relevance counts. Unexpected section
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
  tier-specific conditions. Retrieve both for installment questions and qualify
  the discrepancy rather than silently imposing a precedence rule.
- Local freight specifies above/below a threshold but not equality. Equality
  requires clarification, not an invented free-shipping entitlement.
- Return eligibility needs channel, actual receipt, condition and exclusions;
  imported order status alone does not establish these. Warranty statements are
  manual claims, not independently verified legal advice.
- Campaign descriptions do not establish current promotions. Operational tools
  remain authoritative for active offers and amounts. Procedures about forwarding
  complaints do not grant the agent capabilities to perform those actions.

## Frozen evaluation, before tuning

`data/policies/questions.json` has 25 Portuguese questions: 16 development and
9 validation, with required evidence groups, topic, expected response behavior
and critical flags. Each group contains acceptable alternative chunk IDs; current
labels use one ID per group. Multiple groups require all evidence. Unsupported
cases have zero groups. Labels derive from source rules, not retrieved rankings.
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
owner confirmed the manual is fictional and explicitly approved versioning the extracted
corpus, superseding the former ignored-output/distribution gate. `corpus.json` is a
reviewable repository artifact; the original PDF stays unchanged. Raw layout output is
reproducible with `pdftotext -layout` and need not be tracked. Normalization removes PDF
presentation noise and makes table relationships explicit for retrieval and lower-cost
generators. No quality/token-cost improvement is claimed before US-15/US-17 measure it.
Existing section IDs and gold labels are unchanged; the cover contact has its own ID.
The parser version and frozen chunk hash are revised before benchmarking. External
provider processing has not been performed or separately authorized. Paid runs
additionally require explicit opt-in, confirmed region/access and a bounded cost
estimate. US-15 implements comparisons; US-16 integrates the existing agent; US-17
evaluates generated answers. Review this delivery before beginning those dependent
stories.