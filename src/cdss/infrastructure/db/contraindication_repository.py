"""SQLAlchemy loader for the drug contraindication reference catalog."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from cdss.domain.contraindication_catalog import (
    ContraindicationDrug,
    ContraindicationDrugRepository,
)
from cdss.infrastructure.db.models import ContraindicationDrug as ContraindicationDrugModel


def _to_domain(row: ContraindicationDrugModel) -> ContraindicationDrug:
    return ContraindicationDrug(
        contraindication_id=row.contraindication_id,
        disease_finding_vn=row.disease_finding_vn,
        disease_finding_eng=row.disease_finding_eng,
        contraindication_type=row.contraindication_type,
        drug_group=row.drug_group,
        drugs=row.drugs,
        icd10_vn_1_decimal=row.icd10_vn_1_decimal,
        snomedct_2026_06_01=row.snomedct_2026_06_01,
        target=row.target,
        finding_key=row.finding_key,
        fact_key=row.fact_key,
        operator=row.operator,
        threshold=row.threshold,
    )


class SqlAlchemyContraindicationDrugRepository(ContraindicationDrugRepository):
    """Load contraindication rules from ``contraindication_drugs``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_all(self) -> Sequence[ContraindicationDrug]:
        rows = (
            self._session.execute(
                select(ContraindicationDrugModel).order_by(
                    ContraindicationDrugModel.contraindication_id
                )
            )
            .scalars()
            .all()
        )
        return [_to_domain(row) for row in rows]
