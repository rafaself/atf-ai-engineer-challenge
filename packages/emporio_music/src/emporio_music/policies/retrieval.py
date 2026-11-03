"""Frozen query-only metadata rules and one-hop manual relationships."""

import unicodedata

# Same broad union rule as the US-15 benchmark; inspect only supplied query text.
_FILTER_RULES = [
    (("horario", "abrem", "sabado", "domingo", "feriado"), {"2"}),
    (("endereco", "contato", "whatsapp", "email", "e-mail"), {"cover", "1", "7"}),
    (
        ("pagamento", "pix", "cartao", "dividir", "parcela", "vezes", "boleto"),
        {"3", "6"},
    ),
    (("promoc", "campanha", "desconto"), {"3", "6"}),
    (("devol", "troca", "arrepend", "reembolso", "personalizado"), {"4"}),
    (("defeito", "garantia", "queda"), {"4", "8"}),
    (("frete", "entreg", "envia", "rastreio"), {"5"}),
    (("dados", "privacidade", "marketing"), {"9"}),
]


def query_families(query: str) -> list[str]:
    """Return the frozen metadata-family union inferred from query text alone."""
    text = "".join(
        character
        for character in unicodedata.normalize("NFD", query.lower())
        if not unicodedata.combining(character)
    )
    return sorted(
        set().union(
            *(
                families
                for words, families in _FILTER_RULES
                if any(word in text for word in words)
            )
        )
    )


# Direct section links reviewed against the fixed manual. Do not traverse recursively.
RELATED = {
    "4.1": ["4.4"],
    "4.3": ["4.4"],
    "4.2": ["8.1", "8.2", "8.3"],
    "8.1": ["4.2", "8.2", "8.3"],
    "8.2": ["4.2", "8.1", "8.3"],
    "8.3": ["4.2", "8.1", "8.2"],
    "3": ["3.1", "6.2"],
    "3.1": ["3", "6.2"],
    "6.2": ["3", "3.1"],
    "7": ["1.2", "cover"],
    "1.2": ["7", "cover"],
    "cover": ["1.2", "7"],
}


def expand(ranked_ids: list[str], sections: dict[str, str]) -> list[str]:
    """Retain the three highest-ranked seeds and add direct records, capped at eight."""
    seeds = list(dict.fromkeys(ranked_ids))[:3]
    by_section = {section: chunk_id for chunk_id, section in sections.items()}
    result = list(seeds)
    for seed in seeds:
        for section in RELATED.get(sections[seed], []):
            chunk_id = by_section.get(section)
            if chunk_id is not None and chunk_id not in result:
                result.append(chunk_id)
    return result[:8]
