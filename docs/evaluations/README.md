# Evaluation records

This repository retains the two end-to-end benchmark deliveries that inform the current demonstration. Their raw captures and machine-readable fixtures remain unchanged; source-freeze maps keep the paths recorded at run time, before this reorganization. Markdown prose has been reflowed without changing recorded decisions or procedures. The folders group studies by evaluation context.

- [Model selection (#82)](model-selection/README.md): ten Bedrock models, 16 Portuguese conversations per model, AI-reviewed results and a provisional Luna selection. No independent human review is claimed.
- [Policy-context comparison (#78)](policy-context/README.md): paired RAG versus embedded-policy conversations, measured cost and latency, grounding diagnostics and pending human semantic review.

The historical retrieval-development runs and intermediate model experiments are available through the repository's Git history, not as current benchmarks. A new experiment uses its own source freeze; the original published results must never be rewritten. Live inference requires fresh explicit authorization.
