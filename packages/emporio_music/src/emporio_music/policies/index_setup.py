"""Load the verified policy corpus and derive persisted index signatures."""

import hashlib
import json
from pathlib import Path
from typing import Any

from emporio_music.policies.corpus import (
    FREIGHT_CLARIFICATION_SOURCE,
    PolicyChunk,
    PolicyCorpus,
)

EMBEDDING_INPUT = "hierarchy joined by newline + newline + section text"
POLICY_COLLECTION = "policy-e5"


def policy_document_text(chunk: PolicyChunk) -> str:
    """Serialize the hierarchy and section text used for passage embeddings."""
    return "\n".join(chunk.hierarchy) + "\n" + chunk.text


def load_verified_policy_corpus(
    data_directory: Path,
) -> tuple[PolicyCorpus, dict[str, Any], str]:
    """Validate current source/corpus hashes against the frozen manifest."""
    policy_directory = data_directory / "policies"
    corpus = PolicyCorpus.model_validate_json(
        (policy_directory / "corpus.json").read_text()
    )
    freeze: dict[str, Any] = json.loads((policy_directory / "freeze.json").read_text())
    source_sha256 = hashlib.sha256(
        (data_directory / corpus.source).read_bytes()
    ).hexdigest()
    clarification_sha256 = hashlib.sha256(
        (data_directory / FREIGHT_CLARIFICATION_SOURCE).read_bytes()
    ).hexdigest()
    chunks_sha256 = hashlib.sha256(
        json.dumps(
            [chunk.model_dump(exclude_none=True) for chunk in corpus.chunks],
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    if (
        source_sha256 != corpus.source_sha256
        or source_sha256 != freeze["source_sha256"]
        or freeze["freight_clarification_source"] != FREIGHT_CLARIFICATION_SOURCE
        or clarification_sha256 != corpus.freight_clarification_sha256
        or clarification_sha256 != freeze["freight_clarification_sha256"]
        or chunks_sha256 != freeze["chunks_sha256"]
        or corpus.parser_version != freeze["parser_version"]
    ):
        raise ValueError("Frozen policy source or corpus mismatch")
    return corpus, freeze, chunks_sha256


def policy_index_configuration(
    corpus: PolicyCorpus,
    chunks_sha256: str,
    embedding_config: dict[str, Any],
) -> dict[str, Any]:
    """Build the shared fingerprint inputs for runtime and benchmark indexes."""
    return {
        **embedding_config,
        "source_sha256": corpus.source_sha256,
        "freight_clarification_sha256": corpus.freight_clarification_sha256,
        "corpus_sha256": chunks_sha256,
        "parser_version": corpus.parser_version,
        "embedding_input": EMBEDDING_INPUT,
    }
