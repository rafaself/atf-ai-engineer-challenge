# Bounded evidence-expansion experiment

Freeze before execution: top-three filtered E5 seeds; append direct related
conditions from expansion.py; no recursion; maximum eight chunks. Original
US-15 results and its question set stay unchanged. Old development/validation
results are exploratory for this new strategy. Twelve new questions and explicit
human answer rubrics are frozen before retrieving or generating new results.
They are authored in the same session, so this is a small author-reviewed holdout,
not independently collected or a broad statistical guarantee.

Report original retrieval Recall@3/5 and MRR@5 unchanged. Expansion is a context
assembly strategy: report evidence recall and all-required-evidence coverage over
its complete context, alongside chunk/character counts, not as improved Recall@5
when more than five records are supplied. Include original filtered-top-five
and expanded contexts for both old/fresh sets.

For generation compare expanded E5 context with all 29 corpus records (the entire
reviewed policy content including cover contacts) on the same 12 new questions.
Use the same Qwen3 32B model in us-east-1, temperature zero, max 1024 output tokens,
identical instructions, no operational tools and no retries. This isolates policy
context assembly; it is not a test of HTTP routing, history or customer boundaries.
Require source references, conditional eligibility, honest missing evidence and
no performed actions. Apply equivalent current-context numeric membership checks
for R$ values to both arms; no silent stripping or retries. Preserve failures.
Review answers manually against the frozen rubrics and source; no LLM-as-judge.
Record usage, wall latency and estimated cost. Reserve at most US$0.50 for the
whole generation experiment, within the existing US$1 session cap; no new provider
or dependency. No US-16 production integration, commits or publication in this task.
