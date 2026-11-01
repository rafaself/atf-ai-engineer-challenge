"""Manual-backed preparation invariants; no network or models."""

import hashlib
import json
from pathlib import Path

import pytest

from emporio_music_backend.paths import DATA_DIRECTORY
from emporio_music_backend.policy_corpus import parse_layout, prepare


def test_manual_tables_cross_pages_and_source_bytes_are_preserved() -> None:
    source = DATA_DIRECTORY / "store_policies.pdf"
    before = source.read_bytes()
    corpus = prepare(source)
    chunks = {chunk.section: chunk for chunk in corpus.chunks}
    assert len(chunks) == 28
    assert chunks["5.2"].pages == [4, 5]
    assert "SEDEX" in chunks["5.2"].text
    assert "2 a 5 dias úteis" in chunks["5.2"].text
    assert chunks["7.2"].pages == [6, 7]
    assert chunks["9"].pages == [7, 8]
    assert "100,00" in chunks["3"].text
    assert "80,00" in chunks["3.1"].text
    assert chunks["4.1"].hierarchy[0].startswith("4 ")
    assert source.read_bytes() == before
    assert prepare(source) == corpus


def test_changed_source_is_rejected_before_extraction(tmp_path: Path) -> None:
    source = tmp_path / "changed.pdf"
    source.write_bytes(b"not the reviewed manual")
    with pytest.raises(ValueError, match="checksum"):
        prepare(source)


def test_incomplete_extraction_is_rejected() -> None:
    with pytest.raises(ValueError, match="structure"):
        parse_layout("1. Sobre a loja\nIncomplete extraction")


def test_labels_reference_existing_evidence_and_preserve_frozen_dataset() -> None:
    corpus = prepare(DATA_DIRECTORY / "store_policies.pdf")
    ids = {chunk.id for chunk in corpus.chunks}
    directory = DATA_DIRECTORY / "policies"
    raw = (directory / "questions.json").read_bytes()
    freeze = json.loads((directory / "freeze.json").read_text())
    assert hashlib.sha256(raw).hexdigest() == freeze["questions_sha256"]
    canonical = json.dumps(
        [chunk.model_dump() for chunk in corpus.chunks],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == freeze["chunks_sha256"]
    protocol = (DATA_DIRECTORY.parent / "docs" / "policy-retrieval.md").read_bytes()
    assert hashlib.sha256(protocol).hexdigest() == freeze["protocol_sha256"]
    dataset = json.loads(raw)
    assert dataset["source_sha256"] == corpus.source_sha256
    questions = dataset["questions"]
    assert len(questions) == len({q["id"] for q in questions}) == 25
    assert {q["split"] for q in questions} == {"development", "validation"}
    for question in questions:
        for group in question["evidence_groups"]:
            assert group and set(group) <= ids
        if not question["evidence_groups"]:
            assert question["expectation"] == "unsupported"


def test_normalization_keeps_table_relationships_and_joins_wrapped_values() -> None:
    chunks = {
        c.section: c for c in prepare(DATA_DIRECTORY / "store_policies.pdf").chunks
    }
    assert (
        "Forma: PIX | Condições: Pagamento à vista | Observações: 5% de desconto sobre o preço de tabela"
        in chunks["3"].text
    )
    assert (
        "Modalidade: SEDEX (Correios) | Prazo Estimado: 2 a 5 dias úteis | Rastreamento: Sim | Seguro: Incluído"
        in chunks["5.2"].text
    )
    assert "R$ 50,00" in chunks["3.1"].text
    for chunk in chunks.values():
        assert "  " not in chunk.text
        assert "\u200b" not in chunk.text
    saved = json.loads((DATA_DIRECTORY / "policies" / "corpus.json").read_text())
    assert saved == prepare(DATA_DIRECTORY / "store_policies.pdf").model_dump()
