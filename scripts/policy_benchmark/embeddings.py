"""Two explicit embedding configurations, with no import-time model loading."""

import json
import math
from typing import Any

from emporio_music.infrastructure.policy_embeddings import (
    E5_CONFIG,
    E5_MODEL,
    E5_REVISION,
    E5Embedder,
)

MODELS = {
    "e5": E5_MODEL,
    "titan": "amazon.titan-embed-text-v2:0",
}
# USD / 1K input tokens, official AWS pricing checked 2026-11-01.
RATES = {"e5": 0.0, "titan": 0.00002}


class Embedder:
    def __init__(
        self,
        name: str,
        *,
        allow_download: bool,
        allow_paid: bool,
        region: str,
        budget: float,
    ) -> None:
        if name not in MODELS:
            raise ValueError("Unknown embedding configuration")
        if name != "e5" and not allow_paid:
            raise ValueError("Bedrock embedding requires explicit --allow-paid")
        self.name = name
        self.config: dict[str, Any] = {
            "model": MODELS[name],
            "dimensions": 768 if name == "e5" else 1024,
            "revision": E5_REVISION
            if name == "e5"
            else "Bedrock managed model ID; weights not pinnable",
            "region": region if name != "e5" else None,
            "distance": "cosine",
            "preprocessing": "query:/passage:, L2 normalized"
            if name == "e5"
            else "inputText, normalize=true",
            "tokenizer_revision": None,
        }
        self.budget = budget
        self.reserved_usd = 0.0
        self.tokens = 0
        self.token_counts: list[int] = []
        self.calls = 0
        self.client: Any = None
        self.local_e5: E5Embedder | None = None
        if name == "e5":
            self.local_e5 = E5Embedder(allow_download=allow_download)
            self.config = dict(E5_CONFIG)
        else:
            import boto3  # type: ignore[import-untyped]
            from botocore.config import Config  # type: ignore[import-untyped]

            self.client = boto3.Session(region_name=region).client(
                "bedrock-runtime",
                config=Config(
                    connect_timeout=5,
                    read_timeout=30,
                    retries={"total_max_attempts": 1},
                ),
            )

    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        if self.name == "e5":
            if self.local_e5 is None:
                raise ValueError("E5 embedder is unavailable")
            vectors = self.local_e5.embed(texts, query=query)
            counts = self.local_e5.last_token_counts
            self.tokens += sum(counts)
            self.token_counts.extend(counts)
        else:
            counts = []
            for text in texts:
                if not text.strip():
                    raise ValueError("Empty embedding input")
                # Titan tokenizer is not public: conservative byte bound before the
                # non-truncating API; exact inputTextTokenCount is checked afterwards.
                count = len(text.encode("utf-8"))
                if count > 8192 or len(text) > 50000:
                    raise ValueError("Titan conservative input bound exceeded")
                counts.append(count)
            self.token_counts.extend(counts)
            vectors = []
            for text in texts:
                # Reserve worst-case accepted token use BEFORE the request, including
                # failed calls; SDK retries are disabled. No inferred billing refunds.
                upper = 8192
                charge = upper * RATES[self.name] / 1000
                if self.reserved_usd + charge > self.budget:
                    raise ValueError("Paid embedding budget exhausted before request")
                self.reserved_usd += charge
                body = {"inputText": text, "dimensions": 1024, "normalize": True}
                self.calls += 1
                response = self.client.invoke_model(
                    modelId=MODELS[self.name],
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                payload = json.loads(response["body"].read())
                tokens = payload["inputTextTokenCount"]
                if tokens > upper:
                    raise ValueError("Provider returned input count above limit")
                self.tokens += tokens
                vectors.append(payload["embedding"])
        dimension = self.config["dimensions"]
        if len(vectors) != len(texts) or any(
            len(v) != dimension or not all(math.isfinite(x) for x in v) or not any(v)
            for v in vectors
        ):
            raise ValueError("Invalid embedding response shape/values")
        return list(vectors)
