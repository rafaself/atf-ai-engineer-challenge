"""Persistent policy index with explicit vectors and configuration fingerprints."""

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from emporio_music.domain.errors import PolicyRetrievalError
from emporio_music.policies.corpus import PolicyChunk


def fingerprint(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


class PolicyIndex:
    """Open, query, or explicitly rebuild one named policy collection."""

    def __init__(self, directory: Path, name: str, config: dict[str, Any]) -> None:
        self.directory = directory
        self.name = name
        self.signature = fingerprint(config)
        self.client: Any = None
        self.collection: Any = None
        self._not_found_error: type[Exception] | None = None

    def _connect(self) -> Any:
        if self.client is None:
            try:
                chromadb = importlib.import_module("chromadb")
                settings = importlib.import_module("chromadb.config").Settings
                self._not_found_error = importlib.import_module(
                    "chromadb.errors"
                ).NotFoundError
            except (ImportError, AttributeError) as exc:
                raise PolicyRetrievalError(
                    "Install the optional policy-rag dependencies"
                ) from exc
            self.client = chromadb.PersistentClient(
                path=str(self.directory),
                settings=settings(anonymized_telemetry=False),
            )
        return self.client

    def open(self, expected_ids: list[str]) -> None:
        client = self._connect()
        assert self._not_found_error is not None
        try:
            collection = client.get_collection(self.name, embedding_function=None)
        except self._not_found_error as exc:
            raise ValueError("Missing index; run explicit indexing first") from exc
        if collection.metadata.get("fingerprint") != self.signature:
            raise ValueError("Stale index configuration; use explicit --rebuild")
        if set(collection.get()["ids"]) != set(expected_ids):
            raise ValueError("Incomplete index; use explicit --rebuild")
        self.collection = collection

    def exists(self) -> bool:
        """Check for the named collection without embedding or changing it."""
        return self.name in {
            collection.name for collection in self._connect().list_collections()
        }

    def build(
        self, chunks: list[PolicyChunk], vectors: list[list[float]], *, rebuild: bool
    ) -> None:
        if (
            len(chunks) != len(vectors)
            or not chunks
            or not all(chunk.indexable for chunk in chunks)
        ):
            raise ValueError("Expected one vector per indexable chunk")
        client = self._connect()
        existing = {collection.name for collection in client.list_collections()}
        if self.name in existing:
            if not rebuild:
                raise ValueError(
                    "Index already exists; reuse it or explicitly --rebuild"
                )
            client.delete_collection(self.name)
        self.collection = client.create_collection(
            self.name,
            embedding_function=None,
            metadata={"fingerprint": self.signature},
            configuration={"hnsw": {"space": "cosine"}},
        )
        self.collection.add(
            ids=[chunk.id for chunk in chunks],
            embeddings=vectors,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "source": chunk.source or "store_policies.pdf",
                    "section": chunk.section,
                    "family": chunk.section.split(".")[0],
                    "pages": json.dumps(chunk.pages),
                    "hierarchy": json.dumps(chunk.hierarchy, ensure_ascii=False),
                }
                for chunk in chunks
            ],
        )

    def search(
        self, vector: list[float], families: list[str], *, limit: int = 5
    ) -> list[str]:
        if self.collection is None:
            raise ValueError("Index has not been opened")
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("Search limit must be between 1 and 5")
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=limit,
            where={"family": {"$in": families}} if families else None,
            include=["distances"],
        )
        return list(result["ids"][0])
