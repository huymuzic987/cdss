"""Database-free tests for the SQLAlchemy medicine repository."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable

from cdss.infrastructure.db.medicine_repository import SqlAlchemyMedicineRepository
from cdss.infrastructure.db.models import Medicine as MedicineModel


class StubResult:
    def __init__(self, *, scalar: Any = None, rows: Sequence[Any] = ()) -> None:
        self._scalar = scalar
        self._rows = list(rows)

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalars(self) -> StubResult:
        return self

    def all(self) -> list[Any]:
        return self._rows


class ScriptedSession:
    def __init__(self, results: Sequence[StubResult]) -> None:
        self._results = iter(results)
        self.executed_statements: list[Executable] = []

    def execute(self, statement: Executable) -> StubResult:
        self.executed_statements.append(statement)
        return next(self._results)


def _row(**overrides: Any) -> MedicineModel:
    defaults: dict[str, Any] = {
        "drug_id": "DRUG0003",
        "name": "Amlodipine",
        "drug_class": "C",
        "subgroup": "CKCa DHP",
        "route": "Thuốc Uống",
        "dose_low": "2.5 mg",
        "dose_usual": "5 - 10 mg",
        "dose_max": "10 mg",
        "source": "Bảng 10",
        "link": None,
        "available": True,
    }
    defaults.update(overrides)
    return MedicineModel(**defaults)


def test_get_by_id_returns_domain_medicine() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=_row())])
    repository = SqlAlchemyMedicineRepository(cast(Session, scripted_session))

    medicine = repository.get_by_id("DRUG0003")

    assert medicine is not None
    assert medicine.drug_id == "DRUG0003"
    assert medicine.name == "Amlodipine"
    assert medicine.drug_class == "C"
    assert medicine.available is True
    assert len(scripted_session.executed_statements) == 1


def test_get_by_id_returns_none_when_missing() -> None:
    scripted_session = ScriptedSession([StubResult(scalar=None)])
    repository = SqlAlchemyMedicineRepository(cast(Session, scripted_session))

    assert repository.get_by_id("MISSING") is None


def test_list_by_class_maps_every_row() -> None:
    rows = [_row(drug_id="DRUG0003"), _row(drug_id="DRUG0004", name="Felodipine")]
    scripted_session = ScriptedSession([StubResult(rows=rows)])
    repository = SqlAlchemyMedicineRepository(cast(Session, scripted_session))

    medicines = repository.list_by_class("C")

    assert [m.drug_id for m in medicines] == ["DRUG0003", "DRUG0004"]


def test_list_all_maps_every_row() -> None:
    rows = [_row(drug_id="DRUG0001"), _row(drug_id="DRUG0002")]
    scripted_session = ScriptedSession([StubResult(rows=rows)])
    repository = SqlAlchemyMedicineRepository(cast(Session, scripted_session))

    medicines = repository.list_all()

    assert [m.drug_id for m in medicines] == ["DRUG0001", "DRUG0002"]
