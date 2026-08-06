"""Reduce ordered regimen steps into a non-flattened effective state."""

from cdss.domain.decision_tree.medication_regimen_contracts import (
    EffectiveMedicationRegimen,
    RegimenAlternative,
    RegimenComponent,
    RegimenKeyword,
    RegimenUpdateStep,
)
from cdss.domain.decision_tree.medication_regimen_state_helpers import (
    matches_removal,
    merge_alternative_choices,
    unique_components,
)


def derive_effective_regimen(steps: list[RegimenUpdateStep]) -> EffectiveMedicationRegimen:
    effective = EffectiveMedicationRegimen()
    for step in steps:
        if step.keyword is RegimenKeyword.START:
            incoming = step.alternatives or [RegimenAlternative(components=step.components)]
            effective.base_options = merge_alternative_choices(effective.base_options, incoming)
        elif step.keyword is RegimenKeyword.SELECT:
            if step.alternatives:
                effective.base_options = merge_alternative_choices(
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
        elif step.keyword is RegimenKeyword.REMOVE:
            removed = step_components(step)
            effective.stopped_components.extend(removed)
            effective.base_options = [
                RegimenAlternative(
                    components=[
                        component
                        for component in option.components
                        if not any(matches_removal(component, item) for item in removed)
                    ]
                )
                for option in effective.base_options
            ]
            effective.base_options = [
                option for option in effective.base_options if option.components
            ]
            effective.additions = [
                component
                for component in effective.additions
                if not any(matches_removal(component, item) for item in removed)
            ]
            effective.status = "choice_required" if len(effective.base_options) > 1 else "complete"
        elif step.keyword is RegimenKeyword.AVOID:
            effective.constraints.extend(step_components(step))
    effective.additions = unique_components(effective.additions)
    effective.stopped_components = unique_components(effective.stopped_components)
    effective.constraints = unique_components(effective.constraints)
    return effective


def step_components(step: RegimenUpdateStep) -> list[RegimenComponent]:
    return [
        *step.components,
        *(component for alternative in step.alternatives for component in alternative.components),
    ]
