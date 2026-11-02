"""Local policy search keeps its fixed source/index boundary explicit."""

import json
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from emporio_music_backend.agent.policies import LocalPolicySearch
from emporio_music_backend.contracts.errors import PolicyRetrievalError
from emporio_music_backend.infrastructure.policy_embeddings import (
    E5_CONFIG,
    E5Embedder,
)
from emporio_music_backend.infrastructure.policy_index import PolicyIndex
from emporio_music_backend.policy_corpus import PolicyCorpus
from emporio_music_backend.policy_retrieval import expand, query_families


class FixedEmbedder:
    def __init__(self) -> None:
        self.queries: list[tuple[list[str], bool]] = []

    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        self.queries.append((texts, query))
        return [[1.0, *([0.0] * 767)] for _ in texts]


def _runtime_data(tmp_path: Path, *, build_index: bool) -> None:
    repository_data = Path(__file__).parents[3] / "data"
    policy_directory = tmp_path / "policies"
    policy_directory.mkdir()
    for name in ("store_policies.pdf",):
        shutil.copy2(repository_data / name, tmp_path / name)
    for name in ("corpus.json", "freeze.json"):
        shutil.copy2(repository_data / "policies" / name, policy_directory / name)
    if not build_index:
        return

    corpus = PolicyCorpus.model_validate_json(
        (policy_directory / "corpus.json").read_text()
    )
    freeze = json.loads((policy_directory / "freeze.json").read_text())
    config = {
        **E5_CONFIG,
        "source_sha256": corpus.source_sha256,
        "corpus_sha256": freeze["chunks_sha256"],
        "parser_version": corpus.parser_version,
        "embedding_input": "hierarchy joined by newline + newline + section text",
    }
    chunks = [chunk for chunk in corpus.chunks if chunk.indexable]
    vectors = [
        [1.0, *([0.0] * 767)] if chunk.section == "2" else [0.0, 1.0, *([0.0] * 766)]
        for chunk in chunks
    ]
    index = PolicyIndex(tmp_path / "policy-indexes", "policy-e5", config)
    index.build(chunks, vectors, rebuild=False)


def test_query_filters_and_direct_expansion_remain_bounded() -> None:
    assert query_families("Posso devolver e quem paga o frete?") == ["4", "5"]
    assert query_families("Pergunta sem tema reconhecido") == []
    sections = {
        section: section for section in ["4.1", "4.4", "4.2", "8.1", "8.2", "8.3"]
    }
    assert expand(["4.1"], sections) == ["4.1", "4.4"]
    result = expand(["4.2", "4.1", "4.1", "8.3"], sections)
    assert result[:2] == ["4.2", "4.1"]
    assert len(result) == len(set(result)) <= 8


def test_runtime_uses_frozen_index_and_returns_source_section_page(
    tmp_path: Path,
) -> None:
    _runtime_data(tmp_path, build_index=True)
    embedder = FixedEmbedder()
    search = LocalPolicySearch(data_directory=tmp_path, embedder=embedder)

    result = search.search("Qual é o horário de atendimento?")

    assert result["status"] == "evidence_found"
    assert result["records"] == [
        {
            "id": "policy-v2.1-s2",
            "source": "store_policies.pdf",
            "section": "2",
            "hierarchy": ["2 Horário de Funcionamento"],
            "pages": [2],
            "text": next(
                record.text
                for record in PolicyCorpus.model_validate_json(
                    (tmp_path / "policies" / "corpus.json").read_text()
                ).chunks
                if record.id == "policy-v2.1-s2"
            ),
        }
    ]
    assert embedder.queries == [(["Qual é o horário de atendimento?"], True)]


def test_successful_empty_search_is_distinct_from_index_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _runtime_data(tmp_path, build_index=True)
    monkeypatch.setattr(PolicyIndex, "search", lambda *args, **kwargs: [])
    result = LocalPolicySearch(
        data_directory=tmp_path, embedder=FixedEmbedder()
    ).search("Pergunta sem tema")
    assert result["status"] == "insufficient_evidence"
    assert result["records"] == []


def test_missing_index_raises_operational_retrieval_error(tmp_path: Path) -> None:
    _runtime_data(tmp_path, build_index=False)
    search = LocalPolicySearch(data_directory=tmp_path, embedder=FixedEmbedder())
    with pytest.raises(PolicyRetrievalError, match="unavailable") as failure:
        search.search("Qual é o horário?")
    assert isinstance(failure.value.__cause__, ValueError)


def test_runtime_e5_is_pinned_cpu_only_and_does_not_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    class FakeTokenizer:
        def encode(self, text: str, **kwargs: object) -> list[int]:
            observed["input"] = text
            observed["tokenizer_kwargs"] = kwargs
            return [1]

    class FakeBatch:
        def tolist(self) -> list[list[float]]:
            return [[1.0, *([0.0] * 767)]]

    class FakeModel:
        tokenizer = FakeTokenizer()

        def __init__(self, model: str, **kwargs: object) -> None:
            observed["model"] = model
            observed.update(kwargs)

        def encode(self, texts: list[str], **kwargs: object) -> FakeBatch:
            observed["encoded"] = texts
            observed["encode_kwargs"] = kwargs
            return FakeBatch()

    module = ModuleType("sentence_transformers")
    module.__dict__["SentenceTransformer"] = FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    embedder = E5Embedder()
    assert embedder.embed(["horários"], query=True)[0][0] == 1.0
    assert observed["model"] == "intfloat/multilingual-e5-base"
    assert observed["revision"] == E5_CONFIG["revision"]
    assert observed["device"] == "cpu"
    assert observed["local_files_only"] is True
    assert observed["trust_remote_code"] is False
    assert observed["encoded"] == ["query: horários"]
