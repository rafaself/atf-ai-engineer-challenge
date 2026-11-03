"""Local policy search keeps its fixed source/index boundary explicit."""

import json
import shutil
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from emporio_music.agent.policies import PolicyTools
from emporio_music.domain.errors import PolicyRetrievalError
from emporio_music.infrastructure.policy_embeddings import (
    E5_CONFIG,
    E5Embedder,
)
from emporio_music.infrastructure.policy_index import PolicyIndex
from emporio_music.policies.corpus import PolicyCorpus
from emporio_music.policies.retrieval import expand, query_families
from emporio_music.policies.search import LocalPolicySearch

from tests._support import REPOSITORY_ROOT, run_async


class FixedEmbedder:
    def __init__(self) -> None:
        self.queries: list[tuple[list[str], bool]] = []

    def embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        self.queries.append((texts, query))
        return [[1.0, *([0.0] * 767)] for _ in texts]


def _runtime_data(tmp_path: Path, *, build_index: bool) -> PolicyIndex | None:
    repository_data = REPOSITORY_ROOT / "data"
    policy_directory = tmp_path / "policies"
    policy_directory.mkdir()
    for name in ("store_policies.pdf",):
        shutil.copy2(repository_data / name, tmp_path / name)
    for name in ("corpus.json", "freeze.json"):
        shutil.copy2(repository_data / "policies" / name, policy_directory / name)
    shutil.copy2(
        repository_data / "policies" / "freight-clarification.json",
        policy_directory / "freight-clarification.json",
    )
    if not build_index:
        return None

    corpus = PolicyCorpus.model_validate_json(
        (policy_directory / "corpus.json").read_text()
    )
    freeze = json.loads((policy_directory / "freeze.json").read_text())
    config = {
        **E5_CONFIG,
        "source_sha256": corpus.source_sha256,
        "freight_clarification_sha256": corpus.freight_clarification_sha256,
        "corpus_sha256": freeze["chunks_sha256"],
        "parser_version": corpus.parser_version,
        "embedding_input": "hierarchy joined by newline + newline + section text",
    }
    chunks = [chunk for chunk in corpus.chunks if chunk.indexable]
    vectors = [
        [1.0, *([0.0] * 767)]
        if chunk.section == "2" or chunk.id == "policy-v2.1-s5.1"
        else [0.0, 1.0, *([0.0] * 766)]
        for chunk in chunks
    ]
    index = PolicyIndex(tmp_path / "policy-indexes", "policy-e5", config)
    index.build(chunks, vectors, rebuild=False)
    return index


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


def test_online_return_evidence_exposes_deadline_not_waiting_period(
    tmp_path: Path,
) -> None:
    index = _runtime_data(tmp_path, build_index=True)
    assert index is not None and index.collection is not None
    index.collection.update(
        ids=["policy-v2.1-s4.1"], embeddings=[[1.0, *([0.0] * 767)]]
    )
    result = LocalPolicySearch(
        data_directory=tmp_path, embedder=FixedEmbedder()
    ).search("Comprei online e recebi há cinco dias. Posso devolver?")
    record = next(item for item in result["records"] if item["section"] == "4.1")
    rule = record["online_return_rule"]
    assert rule["request_deadline_calendar_days_after_receipt"] == 7
    assert rule["minimum_wait_calendar_days"] == 0
    assert rule["required_customer_facts"] == [
        "online_purchase",
        "actual_receipt_date",
        "original_packaging",
        "no_signs_of_use",
        "all_accessories",
        "all_manuals",
    ]
    assert record["source"] == "store_policies.pdf"
    assert "em até 7 (sete) dias corridos" in record["text"]


def test_search_store_policies_returns_approved_freight_evidence(
    tmp_path: Path,
) -> None:
    index = _runtime_data(tmp_path, build_index=True)
    assert index is not None and index.collection is not None
    indexed = index.collection.get(
        ids=["policy-v2.1-s5.1"],
        include=["metadatas", "documents"],
    )
    assert indexed["metadatas"][0]["source"] == "effective_store_policies"
    assert indexed["metadatas"][0]["pages"] == "[]"
    assert "igual ou superior a R$ 500,00" in indexed["documents"][0]
    search = LocalPolicySearch(data_directory=tmp_path, embedder=FixedEmbedder())
    tools = PolicyTools(search)
    context = SimpleNamespace(
        prompt="O frete é grátis para um pedido de R$ 500 na região metropolitana?",
        deps=SimpleNamespace(history=[]),
    )

    result = run_async(tools.search_store_policies(context, policy_scope="general"))  # type: ignore[arg-type]

    record = next(
        item for item in result["records"] if item["id"] == "policy-v2.1-s5.1"
    )
    assert result["status"] == "evidence_found"
    assert record["source"] == "effective_store_policies"
    assert record["section"] == "5.1"
    assert record["pages"] == []
    assert "igual ou superior a R$ 500,00" in record["text"]
    assert "R$ 35,00" in record["text"]


def test_online_scope_returns_only_applicable_prepared_rules(tmp_path: Path) -> None:
    _runtime_data(tmp_path, build_index=True)
    embedder = FixedEmbedder()
    result = LocalPolicySearch(data_directory=tmp_path, embedder=embedder).search(
        "Meu pedido consta entregue; posso devolver?", policy_scope="online_return"
    )
    assert result["policy_scope"] == "online_return"
    assert {record["section"] for record in result["records"]} == {"4.1", "4.4"}
    assert embedder.queries == []
    record = next(record for record in result["records"] if record["section"] == "4.1")
    assert record["applicability"] == "online_purchase_remorse"
    assert (
        record["online_return_rule"]["refund_information"]["deadline_business_days"]
        == 10
    )
    assert (
        record["online_return_rule"]["procedure"]["required_documents"]
        == "not_specified_in_manual"
    )


def test_return_contact_scope_preserves_contact_roles_and_unknown_procedure(
    tmp_path: Path,
) -> None:
    _runtime_data(tmp_path, build_index=True)
    embedder = FixedEmbedder()
    result = LocalPolicySearch(data_directory=tmp_path, embedder=embedder).search(
        "Qual contato do SAC para devolução e como recebo a etiqueta?",
        policy_scope="return_contact",
    )

    assert result["policy_scope"] == "return_contact"
    assert {record["section"] for record in result["records"]} == {
        "cover",
        "1.2",
        "4.1",
        "4.4",
        "7",
    }
    assert any(
        "contato@emporiodamusica.com.br" in record["text"]
        for record in result["records"]
    )
    assert any(
        "contato@empóriodamusica.com.br" in record["text"]
        for record in result["records"]
    )
    assert any("3341-4444" in record["text"] for record in result["records"])
    assert any("3321-4500" in record["text"] for record in result["records"])
    rule = next(
        record["online_return_rule"]
        for record in result["records"]
        if record["section"] == "4.1"
    )
    assert rule["procedure"]["returns_specific_contact"] == "not_identified_in_manual"
    assert embedder.queries == []


def test_freight_clarification_source_participates_in_index_fingerprint(
    tmp_path: Path,
) -> None:
    corpus = PolicyCorpus.model_validate_json(
        (REPOSITORY_ROOT / "data" / "policies" / "corpus.json").read_text()
    )
    freeze = json.loads(
        (REPOSITORY_ROOT / "data" / "policies" / "freeze.json").read_text()
    )
    config = {
        **E5_CONFIG,
        "source_sha256": corpus.source_sha256,
        "freight_clarification_sha256": corpus.freight_clarification_sha256,
        "corpus_sha256": freeze["chunks_sha256"],
        "parser_version": corpus.parser_version,
        "embedding_input": "hierarchy joined by newline + newline + section text",
    }

    first = PolicyIndex(tmp_path / "first", "policy-e5", config)
    same = PolicyIndex(tmp_path / "same", "policy-e5", config)
    changed = PolicyIndex(
        tmp_path / "changed",
        "policy-e5",
        {**config, "freight_clarification_sha256": "different-source"},
    )

    assert first.signature == same.signature
    assert first.signature != changed.signature


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
