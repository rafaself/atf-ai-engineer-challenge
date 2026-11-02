# Policy corpus, runtime retrieval and evaluation protocol

Status: US-14 corpus, US-15 retrieval benchmark, US-16 policy tool, and US-17
paired answer review are complete. US-15 met none of the frozen configurations'
full target set; US-17 also found answer and tool-selection failures in both
retrieval and full-policy-context runs. See the [US-17 results](examples/us-17/results.md).
Related: US-14 #50, US-15 #52, US-16 #55, parent #49.

Follow-up [US-18 #59](examples/us-18/README.md) fixes current-run citation checks and
explicit mixed-tool omissions, and adds interpretation guidance beside unchanged
policy excerpts. Semantic answer support remains separate from citation provenance.
Its [first live follow-up](examples/us-18/results.md) passes three cases but retains
a mixed-case failure. A focused rerun fixed snapshot semantics but exposed a
model-rewritten query miss; policy search now takes no arguments and uses the exact
current question from application context. The next live attempt omitted the lookup
and failed safely; focused missing-tool feedback now requires policy lookup before
asking customer eligibility facts. Two later checks retrieve section 4.1 with both
tools, but answer faithfulness is still partial. The latest focused citation feedback
requires explaining the supported rule and keeps policy references separate from
order facts. Live functional revalidation remains pending.
Superiority over Full Context
and retrieval optimization are not sprint-closing requirements. Frozen benchmark
shortfalls remain documented and optimization is deferred.

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

## Runtime retrieval (US-16)

Install the opt-in runtime libraries with:

```bash
uv sync --project apps/backend --locked --extra policy-rag
```

The default dependency set remains unchanged. Before answering policy questions,
explicitly build the ignored E5 Chroma collection using the existing benchmark runner:

```bash
uv run --project apps/backend --extra policy-rag --locked \
  python -m scripts.policy_benchmark.run --model e5 --index --allow-download \
  --output-dir /tmp/policy-rag-bootstrap
```

This command may download the pinned `intfloat/multilingual-e5-base` weights after
the explicit `--allow-download` flag, builds `data/policy-indexes/policy-e5`, and
stores its development comparison report under `/tmp`. Generated weights and index
data are ignored. The application never downloads weights or builds/rebuilds the index;
on the first policy-tool use it opens the existing collection and loads only cached E5
weights on CPU (`local_files_only`). A missing or stale corpus, model or index raises a
retrieval error surfaced through the existing sanitized HTTP 503 contract. It is never
reported to the customer as “no policy found.”

The runtime verifies the PDF hash, canonical corpus hash, parser version, index
fingerprint and exact indexable record IDs. It embeds only the current policy question
with E5's `query:` prefix, uses the same frozen query-derived family filters as US-15,
retrieves the three highest-ranked seeds, and adds only the authored one-hop
relationships from the fixed manual, capped at eight records. Each excerpt includes
the source, section hierarchy and physical page. Customer answers cite those references
as `[política 5.1, p. 4]`; each policy amount must cite a
returned section that contains it and explain the applicable condition. Retrieved text
is data, not an instruction source. The product, pricing and customer-order tools remain
separate and deterministic. `search_store_policies` takes no model-selected query:
the application supplies the exact current question, without history or identity.
This enforces the query boundary after a live paraphrase missed applicable evidence;
it does not change the retrieval algorithm or the frozen evaluation.

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
