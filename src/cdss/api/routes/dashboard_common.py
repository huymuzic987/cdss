"""Shared dashboard route filters and date helpers."""

from datetime import UTC, date, datetime
from typing import TypedDict

from cdss.infrastructure.db.models import Patient, Visit


def dashboard_today() -> date:
    return datetime.now(UTC).date()


def rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator) if denominator else 0.0


def last_visit(patient: Patient) -> Visit | None:
    return max(patient.visits, key=lambda v: v.visit_number) if patient.visits else None


class DashboardFilterKwargs(TypedDict):
    department: str | None
    min_age: int | None
    max_age: int | None
    gender: str | None
    comorbidity_icd10: str | None
    adherent_to_cdss: bool | None


class DashboardFilters:
    """Bundles the dashboard's shared filter set so every ``_build_*``
    helper and the repository calls below take the same six params."""

    def __init__(
        self,
        department: str | None,
        min_age: int | None,
        max_age: int | None,
        gender: str | None,
        comorbidity_icd10: str | None,
        adherent_to_cdss: bool | None,
    ) -> None:
        self.department = department
        self.min_age = min_age
        self.max_age = max_age
        self.gender = gender
        self.comorbidity_icd10 = comorbidity_icd10
        self.adherent_to_cdss = adherent_to_cdss

    def as_kwargs(self) -> DashboardFilterKwargs:
        return {
            "department": self.department,
            "min_age": self.min_age,
            "max_age": self.max_age,
            "gender": self.gender,
            "comorbidity_icd10": self.comorbidity_icd10,
            "adherent_to_cdss": self.adherent_to_cdss,
        }
