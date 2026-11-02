"""Prepare the fixed store manual and approved policy overlay locally."""

import hashlib
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from emporio_music_backend.paths import DATA_DIRECTORY

PARSER_VERSION = "poppler-normalized-sections-v4"
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


def _freight_clarification_chunk(
    clarification: FreightPolicyClarification,
) -> PolicyChunk:
    threshold = _format_brl(clarification.threshold_brl)
    below_fee = _format_brl(clarification.fee_below_threshold_brl)
    at_or_above_fee = clarification.fee_at_or_above_threshold_brl
    if at_or_above_fee == 0:
        at_or_above = "frete grátis"
    else:
        at_or_above = f"taxa de frete de R$ {_format_brl(at_or_above_fee)}"
    return PolicyChunk(
        id="policy-v2.1-freight-clarification-v1",
        section="5.1 (clarificação aprovada)",
        hierarchy=[
            "5 Política de Frete e Entregas",
            "5.1 Entregas na Região Metropolitana de Campo Grande",
            "Esclarecimento comercial aprovado",
        ],
        pages=[],
        text=(
            "Esclarecimento comercial aprovado pela proprietária da loja "
            f"(fonte: {FREIGHT_CLARIFICATION_SOURCE}; referência: "
            f"{clarification.approval_reference}; registrado em "
            f"{clarification.recorded_on}). Aplicabilidade: somente para entregas "
            f"na {clarification.delivery_area}. A redação original do PDF na "
            f"seção {clarification.manual_section} não define o caso de igualdade; "
            "esta é uma clarificação comercial nova. Para pedidos com total abaixo "
            f"de R$ {threshold}, a taxa fixa de frete é R$ {below_fee}. Para pedidos "
            f"com total igual ou superior a R$ {threshold}, há {at_or_above}."
        ),
        indexable=True,
        source=FREIGHT_CLARIFICATION_SOURCE,
    )


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
    chunks.append(_freight_clarification_chunk(clarification))
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
    print(json.dumps({"chunks": len(corpus.chunks), "output": str(destination)}))


if __name__ == "__main__":
    main()
