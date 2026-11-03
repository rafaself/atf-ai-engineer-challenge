"""Bounded local search over the frozen store-policy corpus and index."""

import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import Protocol

from emporio_music.domain.errors import PolicyRetrievalError
from emporio_music.domain.policies import PolicyExcerpt, PolicySearchResult
from emporio_music.infrastructure.policy_embeddings import E5_CONFIG, E5Embedder
from emporio_music.infrastructure.policy_index import PolicyIndex
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import (
    FREIGHT_CLARIFICATION_SOURCE,
    PolicyChunk,
    PolicyCorpus,
)
from emporio_music.policies.retrieval import expand, query_families

_EMBEDDING_INPUT = "hierarchy joined by newline + newline + section text"
_COLLECTION = "policy-e5"
_SEED_LIMIT = 3
_MAX_CONTEXTUAL_QUERY_CHARS = 256


class QueryEmbedder(Protocol):
    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]: ...


def _canonical_chunks_sha256(corpus: PolicyCorpus) -> str:
    serialized = json.dumps(
        [chunk.model_dump(exclude_none=True) for chunk in corpus.chunks],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    return hashlib.sha256(serialized).hexdigest()


class LocalPolicySearch:
    """Lazily open the prebuilt E5 index and locally cached model on policy use."""

    def __init__(
        self,
        *,
        data_directory: Path = DATA_DIRECTORY,
        embedder: QueryEmbedder | None = None,
    ) -> None:
        self._data_directory = data_directory
        self._embedder = embedder
        self._index: PolicyIndex | None = None
        self._chunks: dict[str, PolicyChunk] = {}
        self._source = "store_policies.pdf"
        self._lock = Lock()

    def _initialize(self) -> None:
        policy_directory = self._data_directory / "policies"
        corpus = PolicyCorpus.model_validate_json(
            (policy_directory / "corpus.json").read_text()
        )
        freeze = json.loads((policy_directory / "freeze.json").read_text())
        source_path = self._data_directory / corpus.source
        source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        clarification_path = self._data_directory / FREIGHT_CLARIFICATION_SOURCE
        freight_clarification_sha256 = hashlib.sha256(
            clarification_path.read_bytes()
        ).hexdigest()
        chunks_sha256 = _canonical_chunks_sha256(corpus)
        if (
            source_sha256 != corpus.source_sha256
            or source_sha256 != freeze["source_sha256"]
            or freeze["freight_clarification_source"] != FREIGHT_CLARIFICATION_SOURCE
            or freight_clarification_sha256 != corpus.freight_clarification_sha256
            or freight_clarification_sha256 != freeze["freight_clarification_sha256"]
            or chunks_sha256 != freeze["chunks_sha256"]
            or corpus.parser_version != freeze["parser_version"]
        ):
            raise ValueError("Frozen policy source or corpus mismatch")

        chunks = {chunk.id: chunk for chunk in corpus.chunks if chunk.indexable}
        config = {
            **E5_CONFIG,
            "source_sha256": corpus.source_sha256,
            "freight_clarification_sha256": corpus.freight_clarification_sha256,
            "corpus_sha256": chunks_sha256,
            "parser_version": corpus.parser_version,
            "embedding_input": _EMBEDDING_INPUT,
        }
        index = PolicyIndex(
            self._data_directory / "policy-indexes", _COLLECTION, config
        )
        index.open(list(chunks))

        embedder = self._embedder
        if embedder is None:
            embedder = E5Embedder(allow_download=False)
        self._source = corpus.source
        self._chunks = chunks
        self._index = index
        self._embedder = embedder

    def search(self, query: str) -> PolicySearchResult:
        """Return three ranked seeds plus direct links, capped at eight records."""
        with self._lock:
            try:
                if self._index is None or self._embedder is None:
                    self._initialize()
                assert self._index is not None and self._embedder is not None
                vector = self._embedder.embed([query], query=True)[0]
                ranked = self._index.search(
                    vector, query_families(query), limit=_SEED_LIMIT
                )
                selected = expand(
                    ranked,
                    {
                        chunk_id: chunk.section
                        for chunk_id, chunk in self._chunks.items()
                    },
                )
                records: list[PolicyExcerpt] = [
                    {
                        "id": chunk.id,
                        "source": chunk.source or self._source,
                        "section": chunk.section,
                        "hierarchy": list(chunk.hierarchy),
                        "pages": list(chunk.pages),
                        "text": chunk.text,
                    }
                    for chunk_id in selected
                    if (chunk := self._chunks.get(chunk_id)) is not None
                ]
            except PolicyRetrievalError:
                raise
            except Exception as exc:
                raise PolicyRetrievalError(
                    "Store policy retrieval is unavailable"
                ) from exc
        return {
            "status": "evidence_found" if records else "insufficient_evidence",
            "records": records,
        }
