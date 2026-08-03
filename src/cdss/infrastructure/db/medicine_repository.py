"""SQLAlchemy loader for the medicine reference catalog."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.domain.decision_tree.medicine_catalog import Medicine, MedicineRepository
from cdss.infrastructure.db.models import Medicine as MedicineModel


def _to_domain(row: MedicineModel) -> Medicine:
    return Medicine(
        drug_id=row.drug_id,
        name=row.name,
        drug_class=row.drug_class,
        subgroup=row.subgroup,
        route=row.route,
        dose_low=row.dose_low,
        dose_usual=row.dose_usual,
        dose_max=row.dose_max,
        source=row.source,
        link=row.link,
        available=row.available,
        snomed_code=getattr(row, "snomed_code", None),
    )


class SqlAlchemyMedicineRepository(MedicineRepository):
    """Load medicines from the ``medicines`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, drug_id: str) -> Medicine | None:
        row = self._session.execute(
            select(MedicineModel).where(MedicineModel.drug_id == drug_id)
        ).scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    def list_by_class(self, drug_class: str) -> Sequence[Medicine]:
        rows = (
            self._session.execute(
                select(MedicineModel).where(MedicineModel.drug_class == drug_class)
            )
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]

    def list_all(self) -> Sequence[Medicine]:
        rows = (
            self._session.execute(select(MedicineModel).order_by(MedicineModel.drug_id))
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]
