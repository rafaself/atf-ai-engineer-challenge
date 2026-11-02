"""Manual-backed preparation invariants; no network or models."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from emporio_music_backend.paths import DATA_DIRECTORY
from emporio_music_backend.policy_corpus import normalize_lines, parse_layout, prepare


def test_manual_tables_cross_pages_and_source_bytes_are_preserved() -> None:
    source = DATA_DIRECTORY / "store_policies.pdf"
    before = source.read_bytes()
    corpus = prepare(source)
    chunks = {chunk.section: chunk for chunk in corpus.chunks}
    assert len(corpus.chunks) == 30
    assert chunks["5.2"].pages == [4, 5]
    assert "SEDEX" in chunks["5.2"].text
    assert "2 a 5 dias úteis" in chunks["5.2"].text
    assert chunks["7.2"].pages == [6, 7]
    assert chunks["9"].pages == [7, 8]
    assert "100,00" in chunks["3"].text
    assert "80,00" in chunks["3.1"].text
    assert chunks["4.1"].hierarchy[0].startswith("4 ")
    assert source.read_bytes() == before


@pytest.mark.parametrize(
    ("order_total", "expected_fee"),
    [
        ("499.99", "35.00"),
        ("500.00", "0.00"),
        ("500.01", "0.00"),
    ],
)
def test_approved_freight_clarification_covers_threshold_edges(
    order_total: str, expected_fee: str
) -> None:
    clarification = json.loads(
        (DATA_DIRECTORY / "policies" / "freight-clarification.json").read_text()
    )
    amount = Decimal(order_total)
    threshold = Decimal(clarification["threshold_brl"])
    if amount < threshold:
        fee = Decimal(clarification["fee_below_threshold_brl"])
        expected_statement = (
            "total abaixo de R$ 500,00, a taxa fixa de frete é R$ 35,00"
        )
    else:
        assert clarification["comparison"] == "greater_than_or_equal"
        fee = Decimal(clarification["fee_at_or_above_threshold_brl"])
        expected_statement = "total igual ou superior a R$ 500,00, há frete grátis"

    assert fee == Decimal(expected_fee)
    record = next(
        chunk
        for chunk in prepare(DATA_DIRECTORY / "store_policies.pdf").chunks
        if chunk.id == "policy-v2.1-freight-clarification-v1"
    )
    assert expected_statement in record.text


def test_freight_clarification_is_geographically_scoped_and_provenanced() -> None:
    corpus = prepare(DATA_DIRECTORY / "store_policies.pdf")
    record = next(
        chunk
        for chunk in corpus.chunks
        if chunk.id == "policy-v2.1-freight-clarification-v1"
    )

    assert record.section == "5.1 (clarificação aprovada)"
    assert record.pages == []
    assert record.source == "policies/freight-clarification.json"
    assert (
        "somente para entregas na Região Metropolitana de Campo Grande" in record.text
    )
    assert "a redação original do pdf" in record.text.lower()
    assert "não define o caso de igualdade" in record.text.lower()
    assert "GitHub issue #43, Workstream A" in record.text
    assert "registrado em 2026-11-02" in record.text

    manual_record = next(chunk for chunk in corpus.chunks if chunk.section == "5.1")
    assert manual_record.pages == [4]
    assert manual_record.source is None


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
    freeze = json.loads((directory / "freeze.json").read_text())
    historical_raw = (directory / freeze["historical_questions_source"]).read_bytes()
    assert (
        hashlib.sha256(historical_raw).hexdigest()
        == freeze["historical_questions_sha256"]
    )
    historical = json.loads(historical_raw)
    historical_q13 = next(q for q in historical["questions"] if q["id"] == "q13")
    assert historical_q13["evidence_groups"] == [["policy-v2.1-s5.1"]]
    assert historical_q13["expectation"] == "qualify_gap"

    raw = (directory / freeze["questions_source"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == freeze["questions_sha256"]
    canonical = json.dumps(
        [chunk.model_dump(exclude_none=True) for chunk in corpus.chunks],
        ensure_ascii=False,
        sort_keys=True,
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == freeze["chunks_sha256"]
    clarification_sha256 = hashlib.sha256(
        (directory / "freight-clarification.json").read_bytes()
    ).hexdigest()
    assert corpus.freight_clarification_sha256 == clarification_sha256
    assert (
        freeze["freight_clarification_source"] == "policies/freight-clarification.json"
    )
    assert freeze["freight_clarification_sha256"] == clarification_sha256
    dataset = json.loads(raw)
    assert dataset["source_sha256"] == corpus.source_sha256
    assert dataset["freight_clarification_sha256"] == clarification_sha256
    questions = dataset["questions"]
    assert len(questions) == len({q["id"] for q in questions}) == 25
    assert {q["split"] for q in questions} == {"development", "validation"}
    current_q13 = next(q for q in questions if q["id"] == "q13")
    assert current_q13["evidence_groups"] == [
        ["policy-v2.1-freight-clarification-v1"]
    ]
    assert current_q13["expectation"] == "state_conditions"
    for question in questions:
        for group in question["evidence_groups"]:
            assert group and set(group) <= ids
        if not question["evidence_groups"]:
            assert question["expectation"] == "unsupported"


def test_benchmark_runner_loads_current_versioned_questions() -> None:
    from scripts.policy_benchmark.run import load_inputs

    _, questions, freeze = load_inputs()
    q13 = next(question for question in questions if question["id"] == "q13")

    assert freeze["questions_source"] == "questions-v2.json"
    assert q13["evidence_groups"] == [
        ["policy-v2.1-freight-clarification-v1"]
    ]
    assert q13["expectation"] == "state_conditions"


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
    regenerated = prepare(DATA_DIRECTORY / "store_policies.pdf").model_dump(
        exclude_none=True
    )
    # Tool version is provenance, not semantic content. Text drift still fails.
    saved.pop("extractor_version")
    regenerated.pop("extractor_version")
    assert saved == regenerated


def test_supplied_csv_and_pdf_checksums_remain_unchanged() -> None:
    for line in (DATA_DIRECTORY / "SHA256SUMS").read_text().splitlines():
        expected, filename = line.split(maxsplit=1)
        source = DATA_DIRECTORY / filename.strip()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected


def test_cover_preserves_conflicting_contact_with_page_reference() -> None:
    chunks = {
        c.section: c for c in prepare(DATA_DIRECTORY / "store_policies.pdf").chunks
    }
    assert chunks["cover"].pages == [1]
    assert "contato@emporiodamusica.com.br" in chunks["cover"].text
    assert "contato@empóriodamusica.com.br" in chunks["1.2"].text


@pytest.mark.parametrize("section", ["1.2", "2", "3", "5.2"])
def test_known_table_cannot_silently_become_prose(section: str) -> None:
    with pytest.raises(ValueError, match="table"):
        normalize_lines(section, ["Section heading", "Missing table header"])


def test_heading_only_sections_are_marked_non_indexable() -> None:
    chunks = prepare(DATA_DIRECTORY / "store_policies.pdf").chunks
    assert {c.section for c in chunks if not c.indexable} == {"5", "6", "8"}
