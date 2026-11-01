"""Small persistent cosine index; supplied vectors only, no default embedder."""

import hashlib
import json
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError

from emporio_music_backend.policy_corpus import PolicyChunk


def fingerprint(config: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


class PolicyIndex:
    def __init__(self, directory: Path, name: str, config: dict[str, Any]) -> None:
        self.client = chromadb.PersistentClient(
            str(directory), settings=Settings(anonymized_telemetry=False)
        )
        self.name = name
        self.signature = fingerprint(config)
        self.collection: Any = None

    def open(self, expected_ids: list[str]) -> None:
        try:
            collection = self.client.get_collection(self.name, embedding_function=None)
        except NotFoundError as exc:
            raise ValueError("Missing index; run explicit indexing first") from exc
        if collection.metadata.get("fingerprint") != self.signature:
            raise ValueError("Stale index configuration; use explicit --rebuild")
        if set(collection.get()["ids"]) != set(expected_ids):
            raise ValueError("Incomplete index; use explicit --rebuild")
        self.collection = collection

    def build(
        self, chunks: list[PolicyChunk], vectors: list[list[float]], *, rebuild: bool
    ) -> None:
        if (
            len(chunks) != len(vectors)
            or not chunks
            or not all(c.indexable for c in chunks)
        ):
            raise ValueError("Expected one vector per indexable chunk")
        existing = {c.name for c in self.client.list_collections()}
        if self.name in existing:
            if not rebuild:
                raise ValueError(
                    "Index already exists; reuse it or explicitly --rebuild"
                )
            self.client.delete_collection(self.name)
        self.collection = self.client.create_collection(
            self.name,
            embedding_function=None,
            metadata={"fingerprint": self.signature},
            configuration={"hnsw": {"space": "cosine"}},
        )
        self.collection.add(
            ids=[c.id for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "source": "store_policies.pdf",
                    "section": c.section,
                    "family": c.section.split(".")[0],
                    "pages": json.dumps(c.pages),
                    "hierarchy": json.dumps(c.hierarchy, ensure_ascii=False),
                }
                for c in chunks
            ],
        )

    def search(self, vector: list[float], families: list[str]) -> list[str]:
        if self.collection is None:
            raise ValueError("Index has not been opened")
        result = self.collection.query(
            query_embeddings=[vector],
            n_results=5,
            where={"family": {"$in": families}} if families else None,
            include=["distances"],
        )
        return list(result["ids"][0])
