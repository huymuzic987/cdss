"""Tests for FHIR identifier conversion used by decision-tree exports."""

from __future__ import annotations

import re

from cdss.api.schemas.fhir import _node_key_to_id


def test_long_node_keys_have_deterministic_schema_safe_ids() -> None:
    node_key = (
        "T14_INFERENCE_SELECT_LABETALOL_NICARDIPINE_OR_NITROPRUSSIDE_FOR_"
        "HYPERTENSIVE_ENCEPHALOPATHY"
    )

    identifier = _node_key_to_id(node_key)

    assert identifier == _node_key_to_id(node_key)
    assert len(identifier) <= 64
    assert re.fullmatch(r"[A-Za-z0-9.-]+", identifier)
    assert identifier != node_key.lower().replace("_", "-")
