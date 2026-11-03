"""Consequential ranking and real local-index boundaries, without model requests."""

from pathlib import Path

from scripts.policy_benchmark.evaluation import query_families, score, summarize


def test_group_recall_and_first_relevant_rank_ignore_duplicate_ids() -> None:
    result = score(["noise", "a", "a", "b", "c"], [["a", "alternative"], ["c"]])
    assert result == {"recall3": 0.5, "recall5": 1.0, "mrr5": 0.5, "coverage5": 1.0}
    assert score(["alternative"], [["a", "alternative"]]) == {
        "recall3": 1.0,
        "recall5": 1.0,
        "mrr5": 1.0,
        "coverage5": 1.0,
    }


def test_no_evidence_is_not_zero_recall_and_missing_evidence_is_zero() -> None:
    assert score(["noise"], []) is None
    assert score(["noise"], [["a"]]) == {
        "recall3": 0.0,
        "recall5": 0.0,
        "mrr5": 0.0,
        "coverage5": 0.0,
    }


def test_real_persistent_index_rejects_mismatch_and_preserves_scoping(
    tmp_path: Path,
) -> None:
    import pytest
    from emporio_music.infrastructure.policy_index import PolicyIndex
    from emporio_music.policies.corpus import PolicyChunk

    chunks = [
        PolicyChunk(
            id=f"c{i}",
            section=str(i),
            hierarchy=["Test"],
            pages=[1],
            text=f"Evidence {i}",
            indexable=True,
        )
        for i in [1, 2]
    ]
    index = PolicyIndex(
        tmp_path, "test-policy", {"model": "controlled", "dimensions": 2}
    )
    assert not index.exists()
    with pytest.raises(ValueError, match="Missing"):
        index.open(["c1", "c2"])
    index.build(chunks, [[1.0, 0.0], [0.0, 1.0]], rebuild=False)
    assert index.exists()
    assert index.search([1.0, 0.0], []) == ["c1", "c2"]
    assert index.search([1.0, 0.0], ["2"]) == ["c2"]
    with pytest.raises(ValueError, match="Search limit"):
        index.search([1.0, 0.0], [], limit=6)
    index.open(["c1", "c2"])
    wrong = PolicyIndex(tmp_path, "test-policy", {"model": "different"})
    with pytest.raises(ValueError, match="Stale"):
        wrong.open(["c1", "c2"])
    with pytest.raises(ValueError, match="Incomplete"):
        index.open(["c1"])
    with pytest.raises(ValueError, match="already exists"):
        index.build(chunks, [[1.0, 0.0], [0.0, 1.0]], rebuild=False)


def test_filter_uses_query_text_and_preserves_multiple_topics() -> None:
    assert query_families("Posso devolver e quem paga o frete?") == ["4", "5"]
    assert query_families("Pergunta sem tema reconhecido") == []


def test_critical_miss_blocks_selection_even_with_high_mean_scores() -> None:
    rows = [
        {
            "id": "q1",
            "groups": 2,
            "critical": True,
            "scores": {"recall3": 0.5, "recall5": 0.5, "mrr5": 1.0, "coverage5": 0.0},
        }
    ]
    summary = summarize(rows)
    assert summary["critical_misses"] == ["q1"]
    assert summary["multi_group_coverage5"] == 0
    assert summary["passes_frozen_targets"] is False


def test_paid_adapter_requires_opt_in_before_aws_initialization() -> None:
    import pytest

    from scripts.policy_benchmark.embeddings import Embedder

    with pytest.raises(ValueError, match="allow-paid"):
        Embedder(
            "titan",
            allow_download=False,
            allow_paid=False,
            region="us-east-1",
            budget=0.1,
        )


def test_budget_and_input_limits_reject_before_provider_call() -> None:
    import pytest

    from scripts.policy_benchmark.embeddings import Embedder

    adapter = object.__new__(Embedder)
    adapter.name = "titan"
    adapter.token_counts = []
    adapter.budget = 0.000001
    adapter.reserved_usd = 0
    adapter.calls = 0
    with pytest.raises(ValueError, match="budget"):
        adapter.embed(["Known input"], query=True)
    assert adapter.calls == 0
    with pytest.raises(ValueError, match="bound exceeded"):
        adapter.embed(["x" * 8193], query=False)
    assert adapter.calls == 0
