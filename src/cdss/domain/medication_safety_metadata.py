"""Action metadata for auditable candidate-regimen safety evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

type JsonObject = dict[str, Any]


def candidate_regimens(
    payload: Mapping[str, object], context: Mapping[str, object], options: list[JsonObject]
) -> list[list[str]]:
    explicit = payload.get("candidate_regimens")
    if isinstance(explicit, list):
        return [
            [item for item in regimen if isinstance(item, str)]
            for regimen in explicit
            if isinstance(regimen, list)
        ]
    combination_options = payload.get("combination_options")
    if isinstance(combination_options, list):
        return [
            list(regimen)
            for regimen in combination_options
            if isinstance(regimen, list) and all(isinstance(item, str) for item in regimen)
        ]
    from_options = [
        [item for item in option.get("classes", []) if isinstance(item, str)]
        for option in options
        if isinstance(option.get("classes"), list)
    ]
    preferences = context.get("treatment_preferences")
    if isinstance(preferences, Mapping):
        combinations = preferences.get("combination_options")
        if isinstance(combinations, list):
            from_options.extend(
                [item for item in combination if isinstance(item, str)]
                for combination in combinations
                if isinstance(combination, list)
            )
        escalation = preferences.get("escalation_options")
        if isinstance(escalation, list):
            from_options.extend(
                [item for item in item.get("classes", []) if isinstance(item, str)]
                for item in escalation
                if isinstance(item, Mapping) and isinstance(item.get("classes"), list)
            )
    return [list(regimen) for regimen in dict.fromkeys(tuple(regimen) for regimen in from_options)]
