# US-15 policy retrieval benchmark

US-15 implementation, issue #52 / parent #49. No agent integration or generation
quality evidence is delivered here. Raw timestamped JSON reports preserve failures
as well as completed runs; do not overwrite them with improved scores.

## Opt-in setup

From the repository root:

```bash
uv sync --project apps/backend --group benchmark --locked
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

For each configuration (`e5`, `titan`), first run development only:

```bash
uv run --env-file .env --project apps/backend --group benchmark --locked python -m emporio_music_backend.benchmark.run --model e5 --index --allow-download
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
A failed model request never becomes an empty successful search or score.

After freezing the configuration and query rules, run the untouched validation
split exactly once per model, without indexing again:

```bash
uv run --env-file .env --project apps/backend --group benchmark --locked python -m emporio_music_backend.benchmark.run --model e5 --split validation --final-validation
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

The query-only filtering rule is frozen in `benchmark/evaluation.py` before runs.
It unions broad policy families when multiple recognized terms occur and applies
no filter for unknown topics. It never reads question topics/gold labels. Each
query embedding is reused between vector-only and filtered search for fairness;
three repeated embedding invocations measure query variability, not a response
cache. Reports retain timings for every repeat, final rankings, ranking instability,
and relevant top-five evidence lost by filtering. They separate model-load,
document-embedding and index-write times. Existing-index runs incur no new indexing
charges. Index-directory bytes are shared across collections, not per-model sizes.

Recall/MRR, multi-group coverage, denominators and frozen gates follow
[US-14's protocol](../policy-retrieval.md). Unsupported cases receive rankings but
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
