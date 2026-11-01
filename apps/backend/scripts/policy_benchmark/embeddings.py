"""Two explicit embedding configurations, with no import-time model loading."""

import importlib
import json
import math
from typing import Any

E5_REVISION = "d128750597153bb5987e10b1c3493a34e5a4502a"
MODELS = {
    "e5": "intfloat/multilingual-e5-base",
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
        self.model: Any = None
        self.tokenizer: Any = None
        if name == "e5":
            model_type = importlib.import_module(
                "sentence_transformers"
            ).SentenceTransformer
            self.model = model_type(
                MODELS[name],
                revision=E5_REVISION,
                device="cpu",
                local_files_only=not allow_download,
                trust_remote_code=False,
            )
            self.tokenizer = self.model.tokenizer
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
        prepared = (
            [("query: " if query else "passage: ") + t for t in texts]
            if self.name == "e5"
            else texts
        )
        counts = []
        for text in prepared:
            if not text.strip():
                raise ValueError("Empty embedding input")
            if self.tokenizer is not None:
                count = len(
                    self.tokenizer.encode(
                        text, add_special_tokens=True, truncation=False
                    )
                )
                if count > 512:
                    raise ValueError(
                        "Embedding input exceeds tokenizer limit; revise corpus explicitly"
                    )
            else:
                # Titan tokenizer is not public: conservative byte bound before the
                # non-truncating API; exact inputTextTokenCount is checked afterwards.
                count = len(text.encode("utf-8"))
                if count > 8192 or len(text) > 50000:
                    raise ValueError("Titan conservative input bound exceeded")
            counts.append(count)
        self.token_counts.extend(counts)
        if self.name == "e5":
            vectors = self.model.encode(
                prepared, normalize_embeddings=True, show_progress_bar=False
            ).tolist()
            self.tokens += sum(counts)
        else:
            vectors = []
            for text in prepared:
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
