"""Fixed related-condition expansion, authored from the manual before new runs."""

# Direct semantic relationships, not recursively traversed and never gold-derived.
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


def expand(ranked: list[str], sections: dict[str, str]) -> list[str]:
    """Keep top three seeds first, append direct conditions, cap at eight records."""
    seeds = list(dict.fromkeys(ranked))[:3]
    by_section = {section: key for key, section in sections.items()}
    result = list(seeds)
    for seed in seeds:
        for section in RELATED.get(sections[seed], []):
            key = by_section[section]
            if key not in result:
                result.append(key)
    return result[:8]
