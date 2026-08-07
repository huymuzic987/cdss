"""Vocabulary for recognizing medication regimen groups."""

from __future__ import annotations

GROUP_ALIASES: dict[str, tuple[str, ...]] = {
    "A": (
        "A",
        "RAS",
        "RAS inhibitor",
        "ACE",
        "ACEI",
        "ACE inhibitor",
        "ARB",
        "ARNI",
    ),
    "B": ("B", "beta", "beta blocker", "beta-blocker"),
    "C": (
        "C",
        "CCB",
        "calcium channel",
        "calcium-channel",
        "calcium channel blocker",
        "calcium-channel blocker",
        "dihydropyridine",
        "non-DHP",
    ),
    "D": (
        "D",
        "diuretic",
        "thiazide",
        "thiazide-like",
        "loop diuretic",
    ),
    "MRA": (
        "MRA",
        "mineralocorticoid",
        "mineralocorticoid receptor antagonist",
    ),
    "SGLT2i": ("SGLT2i", "SGLT2", "SGLT2 inhibitor"),
    "GLP1RA": (
        "GLP1RA",
        "GLP-1RA",
        "GLP-1 receptor agonist",
        "GLP1 receptor agonist",
    ),
}
GROUP_ONLY_SUBGROUPS = frozenset(group.casefold() for group in GROUP_ALIASES)

# ARNI is a valid A subgroup in the decision vocabulary, even though the
# current medicine catalog has no ARNI rows. Keep it selectable so an explicit
# ARNI mention produces an empty subgroup result instead of falling back to A.
CATALOG_INDEPENDENT_SUBGROUPS = {"A": ("ARNI",)}
