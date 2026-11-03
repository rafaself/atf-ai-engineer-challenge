# Archived evaluation runners

These focused runners produced the completed November 2, 2026 evaluations linked
below. Their reports and raw captures are the historical evidence; the scripts
remain in version control so their setup and run logic can be inspected.

- [Nova 2 Lite holiday evaluation](../../docs/examples/grounding-followups/nova2-benchmark-2026-11-02.md)
- [Nemotron holiday evaluation](../../docs/examples/grounding-followups/nemotron-benchmark-2026-11-02.md)
- [Qwen Natal reasoning probe](../../docs/examples/model-comparison/qwen-policy-uncertainty-2026-11-02.md)

These scripts are not imported by the chat application. They remain in the
repository-wide lint and type checks because those checks scan `scripts/`.
Run them from the repository root. They reuse helpers from the current comparison
runner and shared capture utilities, so a new run uses the current checkout and
does not reproduce the historical capture byte-for-byte. Treat any rerun as a
new experiment: use a fresh output path, refresh the provider and retrieval
preflight, and obtain separate approval before making paid model calls.

The current multi-model comparison remains in [`scripts/compare_models.py`](../compare_models.py).
