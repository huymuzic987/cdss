"""Clinician-authored regimen decisions and the selectable medicine catalog."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_db, get_medicine_repository
from cdss.api.schemas.regimen_decisions import (
    CatalogGroup,
    CatalogMedicine,
    CatalogSubgroup,
    MedicineCatalogResponse,
    RegimenDecisionCreateRequest,
    RegimenDecisionResponse,
)
from cdss.domain.decision_tree.medicine_catalog import MedicineRepository
from cdss.infrastructure.db.regimen_decision_service import (
    RegimenDecisionValidationError,
    create_regimen_decision,
)

router = APIRouter(tags=["regimen-decisions"])

_GROUP_LABELS = {
    "A": ("RAS: ACE inhibitor / ARB / ARNI", "RAS: thuốc ức chế men chuyển / ARB / ARNI"),
    "B": ("Beta-blocker", "Chẹn beta"),
    "C": ("Calcium-channel blocker", "Chẹn kênh canxi"),
    "D": ("Diuretic", "Lợi tiểu"),
    "MRA": ("Mineralocorticoid receptor antagonist", "Đối kháng thụ thể mineralocorticoid"),
    "SGLT2i": ("SGLT2 inhibitor", "Ức chế SGLT2"),
    "GLP1RA": ("GLP-1 receptor agonist", "Đồng vận thụ thể GLP-1"),
    "Others": ("Other medicine", "Thuốc khác"),
}
_GROUP_ORDER = tuple(_GROUP_LABELS)


@router.get("/medicines/catalog", response_model=MedicineCatalogResponse)
def get_medicine_catalog(
    repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
) -> MedicineCatalogResponse:
    groups: dict[str, dict[str, list[CatalogMedicine]]] = {code: {} for code in _GROUP_ORDER}
    for medicine in repository.list_all():
        if not medicine.available:
            continue
        group_code = _medicine_group(medicine)
        subgroup = medicine.subgroup or "Unclassified"
        groups[group_code].setdefault(subgroup, []).append(
            CatalogMedicine(
                drug_id=medicine.drug_id,
                name=medicine.name,
                group_code=group_code,
                subgroup=medicine.subgroup,
                route=medicine.route,
                dose_low=medicine.dose_low,
                dose_usual=medicine.dose_usual,
                dose_max=medicine.dose_max,
                available=medicine.available,
                snomed_code=medicine.snomed_code,
            )
        )

    return MedicineCatalogResponse(
        groups=[
            CatalogGroup(
                code=code,
                label_en=_GROUP_LABELS[code][0],
                label_vi=_GROUP_LABELS[code][1],
                subgroups=[
                    CatalogSubgroup(name=name, medicines=sorted(items, key=lambda item: item.name))
                    for name, items in sorted(subgroups.items())
                ],
            )
            for code in _GROUP_ORDER
            if (subgroups := groups[code])
        ]
    )


@router.post("/regimen-decisions", response_model=RegimenDecisionResponse, status_code=201)
def save_regimen_decision(
    body: RegimenDecisionCreateRequest,
    session: Annotated[Session, Depends(get_db)],
    repository: Annotated[MedicineRepository, Depends(get_medicine_repository)],
) -> RegimenDecisionResponse | JSONResponse:
    try:
        decision = create_regimen_decision(session, body, repository.list_all())
    except RegimenDecisionValidationError as error:
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_regimen_decision",
                "message": str(error),
                "details": {},
            },
        )
    return RegimenDecisionResponse(
        id=decision.id,
        outcome=decision.outcome,  # type: ignore[arg-type]
        patient_fhir_id=decision.patient_fhir_id,
        encounter_fhir_id=decision.encounter_fhir_id,
        created_at=decision.created_at,
    )


def _medicine_group(medicine: object) -> str:
    drug_class = str(getattr(medicine, "drug_class", None) or "").casefold()
    subgroup = str(getattr(medicine, "subgroup", None) or "").casefold()
    name = str(getattr(medicine, "name", "")).casefold()
    if drug_class == "mra" or "mra" in subgroup or name in {"spironolactone", "eplerenone"}:
        return "MRA"
    if drug_class == "sglt2i":
        return "SGLT2i"
    if drug_class == "glp1ra":
        return "GLP1RA"
    if drug_class in {"a", "b", "c", "d"}:
        return drug_class.upper()
    return "Others"
