"""Immutable domain representation of the drug contraindication catalog."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ContraindicationDrug:
    contraindication_id: str
    disease_finding_vn: str
    disease_finding_eng: str
    contraindication_type: str
    drug_group: str
    drugs: str | None
    icd10_vn_1_decimal: str | None
    snomedct_2026_06_01: str | None
    target: str
    finding_key: str
    fact_key: str | None = None
    operator: str | None = None
    threshold: float | None = None


class ContraindicationDrugRepository(Protocol):
    """Loading boundary for the static contraindication catalog."""

    def list_all(self) -> Sequence[ContraindicationDrug]:
        """Return every catalog rule in deterministic order."""
        ...
