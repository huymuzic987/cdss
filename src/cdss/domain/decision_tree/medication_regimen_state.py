"""Reduce ordered regimen steps into a non-flattened effective state."""

from cdss.domain.decision_tree.medication_regimen_contracts import (
    EffectiveMedicationRegimen,
    RegimenAlternative,
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
)


def derive_effective_regimen(steps: list[RegimenUpdateStep]) -> EffectiveMedicationRegimen:
    effective = EffectiveMedicationRegimen()
    for step in steps:
        if step.keyword is RegimenKeyword.START:
            incoming = step.alternatives or [
                RegimenAlternative(components=step.components)
            ]
            effective.base_options = _merge_alternative_choices(
                effective.base_options, incoming
            )
        elif step.keyword is RegimenKeyword.SELECT:
            if step.alternatives:
                effective.base_options = _merge_alternative_choices(
                    effective.base_options, step.alternatives
                )
                if len(effective.base_options) > 1:
                    effective.status = "choice_required"
            else:
                effective.additions.extend(step.components)
        elif step.keyword in {RegimenKeyword.ADD, RegimenKeyword.COMBINE}:
            effective.additions.extend(step_components(step))
        elif step.keyword in {
            RegimenKeyword.ADJUST,
            RegimenKeyword.CHANGE,
            RegimenKeyword.ESCALATE,
            RegimenKeyword.REDUCE,
            RegimenKeyword.KEEP,
            RegimenKeyword.MONITOR,
            RegimenKeyword.RESTORE,
        }:
            effective.adjustments.append(step)
        elif step.keyword is RegimenKeyword.MAINTAIN:
            continue
        elif step.keyword is RegimenKeyword.STOP:
            effective.stopped_components.extend(step_components(step))
        elif step.keyword is RegimenKeyword.AVOID:
            effective.constraints.extend(step_components(step))
    effective.additions = _unique_components(effective.additions)
    effective.stopped_components = _unique_components(effective.stopped_components)
    effective.constraints = _unique_components(effective.constraints)
    return effective


def step_components(step: RegimenUpdateStep) -> list[RegimenComponent]:
    return [
        *step.components,
        *(component for alternative in step.alternatives for component in alternative.components),
    ]


def _unique_components(components: list[RegimenComponent]) -> list[RegimenComponent]:
    output: list[RegimenComponent] = []
    seen: set[tuple[str | None, ...]] = set()
    for component in components:
        identity = (
            component.selector_kind,
            component.code,
            component.medicine_id,
            component.name,
            component.dose_strategy,
            component.dose,
            component.route,
            component.frequency,
            component.duration,
        )
        if identity not in seen:
            seen.add(identity)
            output.append(component)
    return output


def _merge_alternative_choices(
    existing: list[RegimenAlternative],
    incoming: list[RegimenAlternative],
) -> list[RegimenAlternative]:
    """Preserve independent OR choices without duplicating an existing choice."""

    incoming = [option for option in incoming if option.components]
    if not incoming:
        return existing
    if not existing:
        return incoming
    if all(
        any(_contains_components(option.components, choice.components) for choice in incoming)
        for option in existing
    ):
        return existing

    merged = [
        RegimenAlternative(
            components=_unique_components([*base.components, *choice.components])
        )
        for base in existing
        for choice in incoming
    ]
    output: list[RegimenAlternative] = []
    seen: set[tuple[tuple[str | None, ...], ...]] = set()
    for option in merged:
        signature = tuple(_component_identity(item) for item in option.components)
        if signature not in seen:
            seen.add(signature)
            output.append(option)
    return output


def _contains_components(
    available: list[RegimenComponent],
    required: list[RegimenComponent],
) -> bool:
    identities = {_choice_identity(item) for item in available}
    return all(_choice_identity(item) in identities for item in required)


def _choice_identity(component: RegimenComponent) -> tuple[str | None, ...]:
    """Identify a selected drug independently of its step-specific dose."""

    return (
        component.selector_kind,
        component.code,
        component.medicine_id,
        component.name,
    )


def _component_identity(component: RegimenComponent) -> tuple[str | None, ...]:
    return (
        component.selector_kind,
        component.code,
        component.medicine_id,
        component.name,
        component.dose_strategy,
        component.dose,
        component.route,
        component.frequency,
        component.duration,
    )
