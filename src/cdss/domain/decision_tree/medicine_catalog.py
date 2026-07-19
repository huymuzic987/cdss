"""Immutable in-memory representation of the medicine reference catalog."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Medicine:
    drug_id: str
    name: str
    drug_class: str | None
    subgroup: str | None
    route: str | None
    dose_low: str | None
    dose_usual: str | None
    dose_max: str | None
    source: str | None
    link: str | None
    available: bool


class MedicineRepository(Protocol):
    """Loading boundary for the medicine catalog, replaceable by in-memory fakes."""

    def get_by_id(self, drug_id: str) -> Medicine | None:
        """Look up one medicine by its drug_id."""
        ...

    def list_by_class(self, drug_class: str) -> Sequence[Medicine]:
        """List every medicine in an A/B/C/D-style drug class."""
        ...

    def list_all(self) -> Sequence[Medicine]:
        """List the full catalog, unfiltered."""
        ...
