"""Bounded local search over the frozen store-policy corpus and index."""

from pathlib import Path
from threading import Lock
from typing import Protocol

from emporio_music.domain.errors import PolicyRetrievalError
from emporio_music.domain.policies import (
    PolicyExcerpt,
    PolicyScope,
    PolicySearchResult,
)
from emporio_music.infrastructure.policy_embeddings import E5_CONFIG, E5Embedder
from emporio_music.infrastructure.policy_index import PolicyIndex
from emporio_music.paths import DATA_DIRECTORY
from emporio_music.policies.corpus import PolicyChunk
from emporio_music.policies.index_setup import (
    POLICY_COLLECTION,
    load_verified_policy_corpus,
    policy_index_configuration,
)
from emporio_music.policies.retrieval import expand, query_families

_SEED_LIMIT = 3


class QueryEmbedder(Protocol):
    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]: ...


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
        corpus, _, chunks_sha256 = load_verified_policy_corpus(self._data_directory)
        chunks = {chunk.id: chunk for chunk in corpus.chunks if chunk.indexable}
        config = policy_index_configuration(corpus, chunks_sha256, E5_CONFIG)
        index = PolicyIndex(
            self._data_directory / "policies" / "policy-indexes",
            POLICY_COLLECTION,
            config,
        )
        index.open(list(chunks))

        embedder = self._embedder
        if embedder is None:
            embedder = E5Embedder(allow_download=False)
        self._source = corpus.source
        self._chunks = chunks
        self._index = index
        self._embedder = embedder

    def search(
        self, query: str, *, policy_scope: PolicyScope = "general"
    ) -> PolicySearchResult:
        """Return three ranked seeds plus direct links, capped at eight records."""
        with self._lock:
            try:
                if self._index is None or self._embedder is None:
                    self._initialize()
                assert self._index is not None and self._embedder is not None
                sections = {
                    "online_return": {"4.1", "4.4"},
                    "return_contact": {"cover", "1.2", "4.1", "4.4", "7"},
                    "preference_exchange": {"4.3", "4.4"},
                    "defect": {"4.2", "8.1", "8.2", "8.3"},
                }
                if policy_scope == "general":
                    vector = self._embedder.embed([query], query=True)[0]
                    ranked = self._index.search(
                        vector, query_families(query), limit=_SEED_LIMIT
                    )
                    selected = expand(
                        ranked,
                        {key: chunk.section for key, chunk in self._chunks.items()},
                    )
                else:
                    selected = [
                        key
                        for key, chunk in self._chunks.items()
                        if chunk.section in sections[policy_scope]
                    ]
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
                for record in records:
                    prepared_chunk = self._chunks[record["id"]]
                    if prepared_chunk.applicability is not None:
                        record["applicability"] = prepared_chunk.applicability
                    prepared_rule = prepared_chunk.online_return_rule
                    if prepared_rule is not None:
                        record["online_return_rule"] = prepared_rule
            except PolicyRetrievalError:
                raise
            except Exception as exc:
                raise PolicyRetrievalError(
                    "Store policy retrieval is unavailable"
                ) from exc
        result: PolicySearchResult = {
            "status": "evidence_found" if records else "insufficient_evidence",
            "records": records,
            "policy_scope": policy_scope,
        }
        if policy_scope == "return_contact":
            result["scope_guidance"] = [
                "Os contatos recuperados são gerais; nenhuma fonte os identifica como SAC de devoluções. Apresente os dados como contatos gerais.",
                "A regra de devolução não documenta e-mail específico, etiqueta ou instruções de postagem. Não invente essas etapas nem afirme que o serviço não existe fora do manual.",
                "Os registros divergem na grafia do e-mail e no telefone de atendimento remoto. Mostre as variantes da fonte sem escolher ou normalizar uma delas.",
                "A regra descreve embalagem, acessórios e manuais como condições do produto; não apresenta uma lista de comprovantes ou outros documentos.",
            ]
        return result
