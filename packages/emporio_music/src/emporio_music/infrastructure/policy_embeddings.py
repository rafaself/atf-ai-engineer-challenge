"""Pinned CPU E5 encoder shared by runtime retrieval and its benchmark."""

import importlib
import math
from typing import Any

E5_MODEL = "intfloat/multilingual-e5-base"
E5_REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"
E5_CONFIG: dict[str, Any] = {
    "model": E5_MODEL,
    "dimensions": 768,
    "revision": E5_REVISION,
    "region": None,
    "distance": "cosine",
    "preprocessing": "query:/passage:, L2 normalized",
    "tokenizer_revision": None,
}


class E5Embedder:
    """Load only cached weights unless a benchmark explicitly permits downloads."""

    def __init__(self, *, allow_download: bool = False) -> None:
        try:
            model_type = importlib.import_module(
                "sentence_transformers"
            ).SentenceTransformer
            self.model = model_type(
                E5_MODEL,
                revision=E5_REVISION,
                device="cpu",
                local_files_only=not allow_download,
                trust_remote_code=False,
            )
        except ImportError:
            raise
        self.tokenizer = self.model.tokenizer
        self.last_token_counts: list[int] = []

    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        prepared = [("query: " if query else "passage: ") + text for text in texts]
        counts: list[int] = []
        for text in prepared:
            if not text.strip():
                raise ValueError("Empty embedding input")
            count = len(
                self.tokenizer.encode(text, add_special_tokens=True, truncation=False)
            )
            if count > 512:
                raise ValueError(
                    "Embedding input exceeds tokenizer limit; revise it explicitly"
                )
            counts.append(count)
        vectors = self.model.encode(
            prepared, normalize_embeddings=True, show_progress_bar=False
        ).tolist()
        if len(vectors) != len(texts) or any(
            len(vector) != 768
            or not all(math.isfinite(value) for value in vector)
            or not any(vector)
            for vector in vectors
        ):
            raise ValueError("Invalid E5 embedding response shape or values")
        self.last_token_counts = counts
        return list(vectors)
