# Benchmarks

## Featured: final Bedrock Runtime Converse model comparison

The [final-model-comparison](final-model-comparison/README.md) directory contains
the frozen protocol, 16-conversation/26-turn fixture, and ten-model manifest for
the final end-to-end model-selection evaluation. All candidates use the **same
Bedrock Runtime Converse integration** and current RAG application. This is
independent of previous model benchmarks and the RAG-versus-embedded-policy
experiment (#78), with its own rubric, spending approval and run artifacts.

**Status (2026-11-03):** all 260 main turns attempted; 255 completed, leaving
155 completed conversations assessed by AI under the owner's post-capture
review amendment. [Results](final-model-comparison/results.md) provisionally
select Luna (16/16 Pass), retaining the runtime default. Total estimated spend:
US$0.5954445075 against the approved US$10 cap. Human review has not occurred;
blank worksheets are ready. See [execution and assessment notes](final-model-comparison/analysis.md).

---

# US-15 policy retrieval benchmark

US-15 implementation, issue #52 / parent #49. No agent integration or generation
quality evidence is delivered here. Raw timestamped JSON reports preserve failures
as well as completed runs; do not overwrite them with improved scores.

## Opt-in setup

From the repository root:

```bash
uv sync --project packages/emporio_music --extra policy-rag --group benchmark --locked
export HF_HOME="$PWD/data/benchmark-cache/hf"
export UV_CACHE_DIR="$PWD/data/benchmark-cache/uv"
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
export TOKENIZERS_PARALLELISM=false
```

Chroma is a development dependency for real on-disk index tests. The separate
benchmark group adds Sentence Transformers and CPU PyTorch, not CUDA. The chat
application never imports the benchmark. Default tests do not download models or
call providers. Model/download caches and generated indexes are Git-ignored.

For application setup, use `make prepare-policy` or the dedicated
`emporio_music.prepare_policy_index` command. That builds the runtime E5 collection
without running this benchmark. The benchmark runner below still builds an index
when `--index` is requested so each embedding configuration can be evaluated.

For each configuration (`e5`, `titan`), first run development only:

```bash
uv run --project packages/emporio_music --env-file .env --extra policy-rag --group benchmark --locked python -m scripts.policy_benchmark.run --model e5 --index --allow-download
```

Replace `e5` with a Bedrock configuration and add `--allow-paid --budget-usd 0.10`
only with permission for source processing and paid calls. E5 needs the download
flag initially; later runs use cached files without it. Default region is `us-east-1`; the owner's 2026-11-01
approval covers model download/source processing and a total US$1 paid budget.
SDK retries are disabled. Each run reserves a conservative token-limit cost before
each attempted provider call, including failed calls. Separate reports must be
summed against the approved total; the per-run limit is not an AWS billing limit.

The updated [IAM policy](../aws/bedrock-invoke-policy.json) grants non-streaming
invocation for the exact Titan embedding-model ARN. Initial probes returned access
denials for both. The owner applies the policy; benchmark code does not alter AWS.
Model-catalog and Marketplace subscription permissions are not required.

Use `--index` once per configuration. To query an existing compatible collection,
omit `--index`; missing, stale or incomplete indexes fail clearly. `--rebuild`
requires `--index` and explicitly replaces only that named benchmark collection.
Benchmark collections default to `data/policy-benchmark-indexes`, separate from the
runtime E5 index at `data/policy-indexes`; pass `--index-dir` to use another location.
A failed model request never becomes an empty successful search or score.

After freezing the configuration and query rules, run the untouched validation
split exactly once per model, without indexing again:

```bash
uv run --project packages/emporio_music --env-file .env --extra policy-rag --group benchmark --locked python -m scripts.policy_benchmark.run --model e5 --split validation --final-validation
```

Do not tune after viewing validation scores. Report contamination if a later
change uses these outcomes. No lexical fusion was added without measured need.

## Controlled comparison

Inputs are the same 26 indexable records and frozen questions/labels from US-14.
The input text is heading hierarchy joined by newlines, followed by section text;
all models use this same semantic content. E5 receives `passage:`/`query:` prefixes
and normalized 768-dimensional embeddings. Titan uses normalized 1024-dimensional
vectors. Chroma uses cosine distance with no embedding function.

E5's pinned tokenizer checks full prefixed inputs against 512 tokens. Titan's tokenizer
is not public: UTF-8 bytes provide a conservative preflight bound (8,192), while
the non-truncating API reports exact input token counts after invocation. These
limitations must remain visible; estimates are not exact provider billing data.
Oversized inputs fail, requiring explicit corpus/label review rather than truncation.

The query-only filtering rule is frozen in `scripts/policy_benchmark/evaluation.py` before runs.
It unions broad policy families when multiple recognized terms occur and applies
no filter for unknown topics. It never reads question topics/gold labels. Each
query embedding is reused between vector-only and filtered search for fairness;
three repeated embedding invocations measure query variability, not a response
cache. Reports retain timings for every repeat, final rankings, ranking instability,
and relevant top-five evidence lost by filtering. They separate model-load,
document-embedding and index-write times. Existing-index runs incur no new indexing
charges. Benchmark index-directory bytes are shared across benchmark collections,
not per-model sizes.

Recall/MRR, multi-group coverage, denominators and frozen gates follow
[US-14's protocol](../guides/policy-retrieval.md). Unsupported cases receive rankings but
no recall/MRR; nearest neighbors are not evidence of answerability. Retrieval
results do not establish generated answer quality or cross-language performance.

Cost assumptions checked 2026-11-01: Titan US$0.00002/1K input tokens. Local model
API cost is zero; electricity and hardware costs excluded.
Sources: [AWS Titan pricing](https://aws.amazon.com/blogs/machine-learning/get-started-with-amazon-titan-text-embeddings-v2-a-new-state-of-the-art-embeddings-model-on-amazon-bedrock/),
[Titan input contract](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-embed-text.html),
[E5 model card](https://huggingface.co/intfloat/multilingual-e5-base).

## Local hardware feasibility (observed 2026-11-01)

The machine has an AMD Ryzen 7 6800H (8 cores / 16 logical CPUs), approximately
14 GiB RAM visible to Linux, and 154 GiB free on the project filesystem. E5 Base
completed development on CPU with four compute threads: approximately 12 seconds
model loading, 7.3 seconds embedding 26 documents, and 38 ms median / 96 ms maximum
query embedding over 48 samples. This establishes practical CPU support for this
small embedding workload, not general local generative-LLM capacity.

At inspection, only 1.2–2.6 GiB memory remained available and nearly all 8 GiB swap
was in use. `/tmp` is tmpfs, so model/package caches were moved to ignored on-disk
`data/benchmark-cache/` to avoid retaining roughly 4 GiB in RAM-backed storage.
Run large typing jobs and model experiments sequentially. GPU acceleration is not
required or claimed by these results. Timing depends on competing host workload;
no isolated-machine performance guarantee or peak-RAM measurement is claimed.


## Current access and accounting notes

The owner applied the updated invocation policy during this session. Titan
completed development and validation using its built index; earlier denied and
partial attempts remain in the report set. Model-catalog permissions were denied
but are not required for embedding inference and are not added to runtime access.
All approved experimentation and setup probes consumed a conservative upper
reservation below US$0.022, within the approved US$1 cap. Reservations are not
billed costs. No SDK retries were enabled.

## Follow-up experiment

See the [bounded expansion and full-manual comparison](expansion/results.md)
for fresh questions, frozen methodology, raw contexts/answers and provisional
source-based answer review. Original US-15 reports and thresholds are unchanged.


## Development scripts, outside runtime

Benchmark runners and helpers live in repository-level `scripts/policy_benchmark/`.
They are excluded from the shared-package wheel. Run from the repository root
using the commands above; the dotenv path is relative to that working directory.
The repository checks include development scripts in strict mypy:
`make check-python`.

The follow-up comparison can be reproduced with:

```bash
uv run --project packages/emporio_music --extra policy-rag --group benchmark --locked python -m scripts.policy_benchmark.context_experiment
uv run --project packages/emporio_music --env-file .env --extra policy-rag --group benchmark --locked python -m scripts.policy_benchmark.context_experiment --generate --retrieval-report docs/benchmarks/expansion/<retrieval-report>.json
```

This follow-up experiment uses the runtime E5 index in `data/policy-indexes`; prepare
it with `make prepare-policy` before running the commands above. The second command
makes paid calls; use it only with explicit approval and the recorded experiment
budget. Moving these scripts does not alter the frozen rule, questions or recorded
model outputs.
