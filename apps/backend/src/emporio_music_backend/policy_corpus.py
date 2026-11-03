"""Prepare the fixed store manual and approved policy overlay locally."""

import hashlib
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from emporio_music_backend.contracts.policies import OnlineReturnRule
from emporio_music_backend.paths import DATA_DIRECTORY

PARSER_VERSION = "poppler-effective-policies-v6"
FREIGHT_CLARIFICATION_SOURCE = "policies/freight-clarification.json"
HEADING = re.compile(r"^(\d+(?:\.\d+)?)\.?\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ].+)$")


class PolicyChunk(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str
    section: str
    hierarchy: list[str]
    pages: list[int]
    text: str = Field(min_length=1)
    indexable: bool
    source: str | None = None
    source_references: list[str] = Field(default_factory=list)
    online_return_rule: OnlineReturnRule | None = None


class FreightPolicyClarification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1]
    approval_status: Literal["approved"]
    approved_by: Literal["business owner"]
    approval_reference: str = Field(min_length=1)
    recorded_on: str
    manual_section: Literal["5.1"]
    delivery_area: str = Field(min_length=1)
    threshold_brl: Decimal = Field(gt=Decimal("0"))
    comparison: Literal["greater_than_or_equal"]
    fee_below_threshold_brl: Decimal = Field(ge=Decimal("0"))
    fee_at_or_above_threshold_brl: Decimal = Field(ge=Decimal("0"))


class PolicyCorpus(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: str
    source_sha256: str
    parser_version: str
    extractor_version: str
    freight_clarification_sha256: str
    chunks: list[PolicyChunk]


# Table widths come from the first complete data row, not centered headers.
_TABLES = {
    "1.2": (("Campo", "Informação"), 7),
    "2": (("Dia", "Horário"), 3),
    "3": (("Forma", "Condições", "Observações"), 4),
    "5.2": (("Modalidade", "Prazo Estimado", "Rastreamento", "Seguro"), 3),
}

_EFFECTIVE_HOURS = """2. Horário de Funcionamento
Segunda a sexta-feira: 09h às 18h.
Sábado: 09h às 13h.
Domingos e feriados, com exceções de datas especiais: fechado no horário regular; veja a regra de datas especiais abaixo.
Datas especiais — Natal, Black Friday e aniversário da loja: pode haver atendimento em horário especial ou estendido. Os horários especiais de cada ocorrência não estão informados. Para um Natal específico, o manual não confirma abertura nem fechamento. Alterações são comunicadas previamente nas redes sociais e no atendimento via WhatsApp.
O atendimento via WhatsApp segue os horários da loja, com respostas automáticas fora do expediente."""


def normalize_lines(section: str, lines: list[str]) -> str:
    """Serialize this reviewed manual's tables; unwrap prose and list items."""
    output: list[str] = []
    index = 0
    table_count = 0
    while index < len(lines):
        line = lines[index].replace("\u200b", "")
        table = _TABLES.get(section)
        if table and line.strip().startswith(table[0][0] + " "):
            headers = re.split(r"\s{2,}", line.strip())
            table_count += 1
            if tuple(headers) != table[0] or table_count != 1:
                raise ValueError(f"Unexpected table headers/count in {section}")
            index += 1
            if index == len(lines):
                raise ValueError(f"Missing table rows in {section}")
            first = lines[index]
            starts = [m.start() for m in re.finditer(r"\S(?:.*?)(?=\s{2,}|$)", first)]
            if len(starts) != len(headers):
                raise ValueError(f"Unexpected table columns in {section}")
            rows: list[list[str]] = []
            while index < len(lines):
                row_line = lines[index]
                cells = [
                    row_line[start:end].strip()
                    for start, end in zip(
                        starts, [*starts[1:], len(row_line)], strict=True
                    )
                ]
                if cells[0]:
                    if len(rows) == table[1]:
                        break
                    if not all(cells):
                        raise ValueError(f"Incomplete table row in {section}")
                    rows.append(cells)
                else:
                    if not rows:
                        raise ValueError(f"Orphan table continuation in {section}")
                    for col, cell in enumerate(cells):
                        if cell:
                            rows[-1][col] += " " + cell
                index += 1
            if len(rows) != table[1]:
                raise ValueError(f"Unexpected table rows in {section}")
            output.extend(
                " | ".join(
                    f"{header}: {value}"
                    for header, value in zip(headers, row, strict=True)
                )
                for row in rows
            )
            continue
        clean = " ".join(line.split())
        # Headings/list items and explicitly named policy clauses stay separate.
        boundary = bool(HEADING.fullmatch(clean) or re.match(r"^(?:•|\d+\.)\s", clean))
        boundary = boundary or bool(re.match(r"^[^:]{1,45}: ", clean))
        if output and output[-1].startswith("• ") and line == line.lstrip():
            boundary = True
        if output and not boundary and not output[-1].count(" | ") and index > 1:
            output[-1] += " " + clean
        else:
            output.append(clean)
        index += 1
    if section in _TABLES and table_count != 1:
        raise ValueError(f"Missing expected table in {section}")
    return "\n".join(output)


def parse_layout(text: str) -> list[PolicyChunk]:
    """Normalize section text and preserve physical PDF page references."""
    entries: list[tuple[str, list[str], list[int], list[str]]] = []
    parents: dict[str, str] = {}
    for page, content in enumerate(text.split("\f"), 1):
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("Empório da Música Manual"):
                continue
            if re.fullmatch(r"Página \d+", stripped):
                continue
            if stripped.startswith(("Empório da Música —", "Última atualização:")):
                continue
            match = HEADING.fullmatch(stripped)
            if match:
                section, title = match.groups()
                if section in {entry[0] for entry in entries}:
                    raise ValueError(f"Duplicate section {section}")
                heading = f"{section} {title}"
                hierarchy = [heading]
                if "." in section:
                    parent = section.split(".")[0]
                    if parent not in parents:
                        raise ValueError(f"Missing parent {parent}")
                    hierarchy.insert(0, parents[parent])
                else:
                    parents[section] = heading
                entries.append((section, hierarchy, [], []))
            if entries:
                _, _, pages, lines = entries[-1]
                if page not in pages:
                    pages.append(page)
                lines.append(line.rstrip())
    chunks = [
        PolicyChunk(
            id=f"policy-v2.1-s{section}",
            section=section,
            hierarchy=hierarchy,
            pages=pages,
            text=normalize_lines(section, lines),
            indexable=len(lines) > 1,
        )
        for section, hierarchy, pages, lines in entries
    ]
    expected = [
        "1",
        "1.1",
        "1.2",
        "2",
        "3",
        "3.1",
        "4",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "5",
        "5.1",
        "5.2",
        "5.3",
        "6",
        "6.1",
        "6.2",
        "7",
        "7.1",
        "7.2",
        "7.3",
        "8",
        "8.1",
        "8.2",
        "8.3",
        "9",
        "10",
    ]
    if [c.section for c in chunks] != expected:
        raise ValueError("Unexpected manual structure; review extraction")
    # Keep customer-facing cover contacts, including the conflicting email spelling.
    cover_lines = [
        " ".join(line.split())
        for line in text.split("\f")[0].splitlines()
        if "@" in line
    ]
    if len(cover_lines) != 1:
        raise ValueError("Unexpected cover contact structure")
    chunks.insert(
        0,
        PolicyChunk(
            id="policy-v2.1-cover",
            section="cover",
            hierarchy=["Capa — contato"],
            pages=[1],
            text="Capa — contato\n" + cover_lines[0],
            indexable=True,
        ),
    )
    return chunks


def _format_brl(amount: Decimal) -> str:
    return f"{amount:.2f}".replace(".", ",")


def _effective_chunks(
    chunks: list[PolicyChunk], clarification: FreightPolicyClarification
) -> list[PolicyChunk]:
    """Apply reviewed rules once, preserving raw sources and internal provenance."""
    result: list[PolicyChunk] = []
    for chunk in chunks:
        if chunk.section == "2":
            chunk = chunk.model_copy(update={"text": _EFFECTIVE_HOURS})
        elif chunk.section == "4.1":
            rule: OnlineReturnRule = {
                "request_deadline_calendar_days_after_receipt": 7,
                "minimum_wait_calendar_days": 0,
                "required_customer_facts": [
                    "online_purchase",
                    "actual_receipt_date",
                    "original_packaging",
                    "no_signs_of_use",
                    "all_accessories",
                    "all_manuals",
                ],
                "excluded_product_conditions": [
                    "customized_or_custom_setup",
                    "clearance_explicit_final_sale",
                    "wind_instrument_mouthpiece",
                ],
            }
            chunk = chunk.model_copy(update={"online_return_rule": rule})
        elif chunk.section == "5.1":
            threshold = _format_brl(clarification.threshold_brl)
            fee = _format_brl(clarification.fee_below_threshold_brl)
            upper_fee = clarification.fee_at_or_above_threshold_brl
            upper = (
                "frete grátis"
                if upper_fee == 0
                else f"taxa de frete de R$ {_format_brl(upper_fee)}"
            )
            # Retain delivery estimate, carrier and contact clauses verbatim.
            clauses = chunk.text.splitlines()[3:]
            chunk = chunk.model_copy(
                update={
                    "source": "effective_store_policies",
                    "pages": [],
                    "source_references": [
                        "store_policies.pdf#section=5.1&page=4",
                        FREIGHT_CLARIFICATION_SOURCE,
                    ],
                    "text": "\n".join(
                        [
                            "5.1 Entregas na Região Metropolitana de Campo Grande",
                            f"Aplicabilidade: somente para entregas na {clarification.delivery_area}.",
                            f"Para pedidos com total abaixo de R$ {threshold}, a taxa fixa de frete é R$ {fee}.",
                            f"Para pedidos com total igual ou superior a R$ {threshold}, há {upper}.",
                            *clauses,
                        ]
                    ),
                }
            )
        result.append(chunk)
    return result


def prepare(source: Path) -> PolicyCorpus:
    clarification_path = DATA_DIRECTORY / FREIGHT_CLARIFICATION_SOURCE
    manifest = (DATA_DIRECTORY / "SHA256SUMS").read_text()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if f"{digest}  store_policies.pdf" not in manifest:
        raise ValueError("Source checksum mismatch; review the manual before preparing")
    clarification_bytes = clarification_path.read_bytes()
    clarification_sha256 = hashlib.sha256(clarification_bytes).hexdigest()
    clarification = FreightPolicyClarification.model_validate_json(clarification_bytes)
    version = subprocess.run(
        ["pdftotext", "-v"], capture_output=True, text=True, check=True
    ).stderr.splitlines()[0]
    result = subprocess.run(
        ["pdftotext", "-layout", str(source), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    chunks = parse_layout(result.stdout)
    chunks = _effective_chunks(chunks, clarification)
    return PolicyCorpus(
        source="store_policies.pdf",
        source_sha256=digest,
        parser_version=PARSER_VERSION,
        extractor_version=version,
        freight_clarification_sha256=clarification_sha256,
        chunks=chunks,
    )


def main() -> None:
    corpus = prepare(DATA_DIRECTORY / "store_policies.pdf")
    destination = DATA_DIRECTORY / "policies" / "corpus.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(corpus.model_dump_json(indent=2, exclude_none=True) + "\n")
    freeze_path = destination.parent / "freeze.json"
    freeze = json.loads(freeze_path.read_text())
    questions_source = "questions-v3.json"
    freeze.update(
        version=4,
        parser_version=corpus.parser_version,
        extractor_version=corpus.extractor_version,
        source_sha256=corpus.source_sha256,
        freight_clarification_sha256=corpus.freight_clarification_sha256,
        questions_source=questions_source,
        questions_sha256=hashlib.sha256(
            (destination.parent / questions_source).read_bytes()
        ).hexdigest(),
        chunks_sha256=hashlib.sha256(
            json.dumps(
                [chunk.model_dump(exclude_none=True) for chunk in corpus.chunks],
                ensure_ascii=False,
                sort_keys=True,
            ).encode()
        ).hexdigest(),
    )
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"chunks": len(corpus.chunks), "output": str(destination)}))


if __name__ == "__main__":
    main()
