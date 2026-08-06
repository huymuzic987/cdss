"""Recognize regimen subgroups from the configured medicine catalog."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from unicodedata import combining, normalize

from cdss.domain.decision_tree.medication_regimen_contracts import RegimenComponent
from cdss.domain.decision_tree.medication_regimen_groups import (
    CATALOG_INDEPENDENT_SUBGROUPS,
    GROUP_ALIASES,
    GROUP_ONLY_SUBGROUPS,
)
from cdss.domain.decision_tree.medicine_catalog import Medicine

_TOKEN_PATTERN = re.compile(r"[\w]+(?:-[\w]+)*", re.UNICODE)


def catalog_subgroups(
    text: str | None,
    drug_class: str | None,
    catalog: Sequence[Medicine],
) -> str | None:
    """Return catalog subgroup values mentioned by ``text``.

    Subgroups are deliberately not translated or enumerated here. The
    medicine catalog is the vocabulary, so adding a subgroup only requires a
    catalog row and a matching term in the decision-tree text.
    """

    if not text or not drug_class:
        return None
    catalog_candidates = _unique(
        medicine.subgroup
        for medicine in catalog
        if _belongs_to_class(medicine, drug_class) and medicine.subgroup
    )
    matches = [
        subgroup
        for subgroup in catalog_candidates
        if _mentions(text, subgroup) and not _is_group_only_subgroup(subgroup)
    ]
    if not matches:
        matches = [
            subgroup
            for subgroup in CATALOG_INDEPENDENT_SUBGROUPS.get(drug_class, ())
            if _mentions(text, subgroup)
        ]
    return " / ".join(matches) if matches else None


def catalog_group_matches(
    text: str | None,
    catalog: Sequence[Medicine] = (),
) -> list[tuple[str, str | None]]:
    """Recognize catalog-driven groups and subgroups from text."""

    if not text:
        return []
    text_tokens = _tokens(text)
    matches: list[tuple[int, int, str, str | None]] = []
    for order, group in enumerate(GROUP_ALIASES):
        subgroup = catalog_subgroups(text, group, catalog)
        position = _group_position(text_tokens, group)
        if position is None and subgroup:
            position = _subgroup_position(text_tokens, subgroup)
        if position is not None:
            matches.append((position, order, group, subgroup))
    matches.sort(key=lambda item: (item[0], item[1]))
    return [(group, subgroup) for _, _, group, subgroup in matches]


def subgroup_matches(actual: str | None, expected: str) -> bool:
    """Match one catalog value against one or more recognized values."""

    if not actual:
        return False
    actual_tokens = _tokens(actual)
    return any(
        all(_term_matches(term, actual_tokens) for term in _tokens(value.strip()))
        for value in expected.split("/")
    )


def catalog_subgroups_for_components(
    components: Sequence[RegimenComponent],
    text: str,
    catalog: Sequence[Medicine],
) -> list[RegimenComponent]:
    if not catalog:
        return list(components)
    return [
        component.model_copy(
            update={
                "subgroup": component.subgroup
                or catalog_subgroups(
                    " ".join(value for value in (text, component.name) if value),
                    component.code,
                    catalog,
                )
            }
        )
        for component in components
    ]


def catalog_for_regimen_components(
    components: Sequence[RegimenComponent],
    catalog: Sequence[Medicine],
) -> list[Medicine]:
    """Filter class catalog rows only when a subgroup is explicitly selected."""

    subgroup_filters: dict[str, list[str]] = {}
    for component in components:
        if component.selector_kind != "class" or not component.code or not component.subgroup:
            continue
        subgroup_filters.setdefault(component.code.casefold(), []).append(component.subgroup)
    if not subgroup_filters:
        return list(catalog)
    return [
        medicine
        for medicine in catalog
        if not subgroup_filters.get(drug_class := (medicine.drug_class or "").casefold())
        or any(
            subgroup_matches(medicine.subgroup, subgroup)
            for subgroup in subgroup_filters[drug_class]
        )
    ]


def _belongs_to_class(medicine: Medicine, drug_class: str) -> bool:
    if medicine.drug_class and medicine.drug_class.casefold() == drug_class.casefold():
        return True
    return any(token.casefold() == drug_class.casefold() for token in _tokens(medicine.subgroup))


def _is_group_only_subgroup(subgroup: str) -> bool:
    """Do not treat a top-level group name as a subgroup filter.

    Some catalog rows use values such as ``MRA (LT giữ Kali)`` to describe
    the MRA group. If that value is scanned from a node mentioning ``D +
    MRA``, it must not turn the D component into ``D (MRA ...)``.
    """

    return bool(GROUP_ONLY_SUBGROUPS.intersection(_tokens(subgroup)))


def _mentions(text: str, subgroup: str) -> bool:
    text_tokens = _tokens(text)
    return any(_term_matches(term, text_tokens) for term in _tokens(subgroup))


def _group_position(text_tokens: list[str], group: str) -> int | None:
    positions = [
        position
        for alias in GROUP_ALIASES[group]
        for position in _phrase_positions(text_tokens, _tokens(alias))
    ]
    compact_position = _compact_group_position(text_tokens, group)
    if compact_position is not None:
        positions.append(compact_position)
    return min(positions) if positions else None


def _subgroup_position(text_tokens: list[str], subgroup: str) -> int | None:
    positions = [
        position
        for term in _tokens(subgroup)
        for position, token in enumerate(text_tokens)
        if _term_matches(term, [token])
    ]
    return min(positions) if positions else None


def _phrase_positions(tokens: list[str], phrase: list[str]) -> list[int]:
    if not phrase or len(phrase) > len(tokens):
        return []
    return [
        position
        for position in range(len(tokens) - len(phrase) + 1)
        if all(term == tokens[position + offset] for offset, term in enumerate(phrase))
    ]


def _compact_group_position(text_tokens: list[str], group: str) -> int | None:
    if group not in {"A", "B", "C", "D"}:
        return None
    for position, token in enumerate(text_tokens):
        if (
            2 <= len(token) <= 4
            and len(set(token)) == len(token)
            and set(token) <= set("abcd")
            and group.casefold() in token
        ):
            return position
    return None


def _term_matches(term: str, text_tokens: list[str]) -> bool:
    if term in text_tokens:
        return True
    if "-" in term or not _is_abbreviation(term):
        return False
    return any(
        _is_subsequence(term, word)
        for word in text_tokens
        if "-" not in word and len(word) > len(term)
    )


def _tokens(value: str | None) -> list[str]:
    normalized = (value or "").replace("_", " ")
    return [_fold(token) for token in _TOKEN_PATTERN.findall(normalized)]


def _fold(value: str) -> str:
    return "".join(
        character for character in normalize("NFKD", value.casefold()) if not combining(character)
    )


def _is_abbreviation(value: str) -> bool:
    return len(value) >= 3 and value.isalpha()


def _is_subsequence(short: str, long: str) -> bool:
    position = 0
    for character in long:
        if position < len(short) and character == short[position]:
            position += 1
    return position == len(short)


def _unique(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output
