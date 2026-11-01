"""Bounded direct evidence expansion preserves source identities and ranking seeds."""

from scripts.policy_benchmark.expansion import expand


def test_returns_include_exclusions_without_recursively_loading_manual() -> None:
    sections = {s: s for s in ["4.1", "4.4", "4.3", "4.2", "8.1", "8.2", "8.3"]}
    assert expand(["4.1"], sections) == ["4.1", "4.4"]
    assert expand(["4.2"], sections) == ["4.2", "8.1", "8.2", "8.3"]


def test_expansion_keeps_three_seeds_and_obeys_budget() -> None:
    sections = {
        s: s
        for s in ["3", "3.1", "6.2", "7", "1.2", "cover", "4.2", "8.1", "8.2", "8.3"]
    }
    result = expand(["3", "7", "4.2", "8.3"], sections)
    assert result[:3] == ["3", "7", "4.2"]
    assert len(result) == len(set(result)) == 8
