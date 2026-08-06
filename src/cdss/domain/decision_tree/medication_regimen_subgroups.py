"""Recognize regimen subgroups from the configured medicine catalog."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from unicodedata import combining, normalize

from cdss.domain.decision_tree.medication_regimen_contracts import RegimenComponent
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
    candidates = _unique(
        medicine.subgroup
        for medicine in catalog
        if _belongs_to_class(medicine, drug_class) and medicine.subgroup
    )
    matches = [subgroup for subgroup in candidates if _mentions(text, subgroup)]
    return " / ".join(matches) if matches else None


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


def _belongs_to_class(medicine: Medicine, drug_class: str) -> bool:
    if medicine.drug_class and medicine.drug_class.casefold() == drug_class.casefold():
        return True
    return any(token.casefold() == drug_class.casefold() for token in _tokens(medicine.subgroup))


def _mentions(text: str, subgroup: str) -> bool:
    text_tokens = _tokens(text)
    return any(_term_matches(term, text_tokens) for term in _tokens(subgroup))


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
    return [_fold(token) for token in _TOKEN_PATTERN.findall(value or "")]


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
