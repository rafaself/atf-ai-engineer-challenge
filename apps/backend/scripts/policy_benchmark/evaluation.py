"""Frozen evidence-group retrieval metrics and query-only metadata rules."""

import unicodedata
from statistics import mean
from typing import Any


def score(ranked: list[str], groups: list[list[str]]) -> dict[str, float] | None:
    if not groups:
        return None
    unique = list(dict.fromkeys(ranked))

    def recall(k: int) -> float:
        return sum(bool(set(group) & set(unique[:k])) for group in groups) / len(groups)

    relevant = set().union(*map(set, groups))
    rr = next(
        (1 / rank for rank, item in enumerate(unique[:5], 1) if item in relevant), 0.0
    )
    return {
        "recall3": recall(3),
        "recall5": recall(5),
        "mrr5": rr,
        "coverage5": float(recall(5) == 1),
    }


# Frozen before any retrieval runs. Broad unions preserve related eligibility rules.
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
    text = "".join(
        c
        for c in unicodedata.normalize("NFD", query.lower())
        if not unicodedata.combining(c)
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


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["scores"] is not None]
    multi = [row for row in answerable if row["groups"] > 1]
    metrics = (
        {
            key: mean(row["scores"][key] for row in answerable)
            for key in ("recall3", "recall5", "mrr5")
        }
        if answerable
        else {}
    )
    coverage = mean(row["scores"]["coverage5"] for row in multi) if multi else None
    critical_misses = [
        row["id"]
        for row in answerable
        if row["critical"] and row["scores"]["coverage5"] != 1
    ]
    passed = bool(
        metrics
        and metrics["recall3"] >= 0.8
        and metrics["recall5"] >= 0.9
        and metrics["mrr5"] >= 0.8
        and (coverage is None or coverage == 1)
        and not critical_misses
    )
    return {
        **metrics,
        "multi_group_coverage5": coverage,
        "answerable_cases": len(answerable),
        "evidence_groups": sum(row["groups"] for row in answerable),
        "unsupported_cases": len(rows) - len(answerable),
        "multi_group_cases": len(multi),
        "critical_misses": critical_misses,
        "passes_frozen_targets": passed,
    }
