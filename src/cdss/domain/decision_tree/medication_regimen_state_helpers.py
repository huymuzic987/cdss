"""Matching and merging helpers for effective medication regimens."""

from collections.abc import Iterable

from cdss.domain.decision_tree.medication_regimen_contracts import (
    RegimenAlternative,
    RegimenComponent,
)


def unique_components(components: list[RegimenComponent]) -> list[RegimenComponent]:
    output: list[RegimenComponent] = []
    for component in components:
        matching_index = next(
            (
                index
                for index, existing in enumerate(output)
                if components_match(existing, component)
            ),
            None,
        )
        if matching_index is None:
            output.append(component)
        else:
            output[matching_index] = merge_component(output[matching_index], component)
    return output


def matches_removal(component: RegimenComponent, removed: RegimenComponent) -> bool:
    """Match final class removals without confusing A/B/C/D subgroups."""

    if removed.selector_kind != component.selector_kind:
        return False
    if removed.selector_kind == "class":
        return component.code == removed.code and (
            removed.subgroup is None
            or (
                component.subgroup is not None
                and component.subgroup.casefold() == removed.subgroup.casefold()
            )
        )
    if removed.medicine_id and component.medicine_id:
        return removed.medicine_id == component.medicine_id
    return bool(
        removed.name and component.name and removed.name.casefold() == component.name.casefold()
    )


def merge_alternative_choices(
    existing: list[RegimenAlternative],
    incoming: list[RegimenAlternative],
) -> list[RegimenAlternative]:
    """Preserve independent OR choices without duplicating an existing choice."""

    existing = unique_alternatives(existing)
    incoming = unique_alternatives(option for option in incoming if option.components)
    if not incoming:
        return existing
    if not existing:
        return incoming
    if all(
        any(contains_components(option.components, choice.components) for choice in incoming)
        for option in existing
    ):
        return [merge_equivalent_choice(option, incoming) for option in existing]

    merged = [
        RegimenAlternative(components=unique_components([*base.components, *choice.components]))
        for base in existing
        for choice in incoming
    ]
    return unique_alternatives(merged)


def unique_alternatives(
    alternatives: Iterable[RegimenAlternative],
) -> list[RegimenAlternative]:
    """Deduplicate alternatives without treating component order as meaningful."""

    output: list[RegimenAlternative] = []
    seen: set[tuple[tuple[str | None, ...], ...]] = set()
    for alternative in alternatives:
        components = unique_components(alternative.components)
        if not components:
            continue
        signature = tuple(
            sorted(
                (component_identity(item) for item in components),
                key=lambda identity: tuple(value or "" for value in identity),
            )
        )
        if signature in seen:
            continue
        seen.add(signature)
        output.append(RegimenAlternative(components=components))
    return output


def merge_equivalent_choice(
    existing: RegimenAlternative,
    incoming: list[RegimenAlternative],
) -> RegimenAlternative:
    """Refine a generic existing choice when the same choice is more specific later."""

    match = next(
        (
            option
            for option in incoming
            if contains_components(existing.components, option.components)
            and contains_components(option.components, existing.components)
        ),
        None,
    )
    if match is None:
        return existing
    return RegimenAlternative(
        components=unique_components([*existing.components, *match.components])
    )


def contains_components(
    available: list[RegimenComponent],
    required: list[RegimenComponent],
) -> bool:
    remaining = list(available)
    for required_component in required:
        match_index = next(
            (
                index
                for index, available_component in enumerate(remaining)
                if components_match(available_component, required_component)
            ),
            None,
        )
        if match_index is None:
            return False
        remaining.pop(match_index)
    return True


def components_match(first: RegimenComponent, second: RegimenComponent) -> bool:
    if first.selector_kind != second.selector_kind:
        return False
    if first.selector_kind == "class":
        if (first.code or "").casefold() != (second.code or "").casefold():
            return False
        return (
            not first.subgroup
            or not second.subgroup
            or (first.subgroup.casefold() == second.subgroup.casefold())
        )
    if first.medicine_id and second.medicine_id:
        return first.medicine_id == second.medicine_id
    return bool(first.name and second.name and first.name.casefold() == second.name.casefold())


def merge_component(first: RegimenComponent, second: RegimenComponent) -> RegimenComponent:
    if first.subgroup and second.subgroup:
        subgroups = [
            value.strip()
            for value in (*first.subgroup.split("/"), *second.subgroup.split("/"))
            if value.strip()
        ]
        subgroup = " / ".join(dict.fromkeys(subgroups))
    else:
        subgroup = first.subgroup or second.subgroup
    return first.model_copy(update={"subgroup": subgroup})


def component_identity(component: RegimenComponent) -> tuple[str | None, ...]:
    return (
        component.selector_kind,
        component.code,
        component.medicine_id,
        component.name,
        component.subgroup,
        component.dose_strategy,
        component.dose,
        component.route,
        component.frequency,
        component.duration,
    )
