"""Dashboard seed-data endpoint."""

import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cdss.api.schemas.fhir_clinical import ImportResult
from cdss.core.database import get_db
from cdss.infrastructure.db.clinical_import import import_bundle
from cdss.infrastructure.db.dashboard.dashboard_repository import invalidate_cache

router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DATA_DIR = _REPO_ROOT / "data" / "fhir"
_TEST_CASE_DIR = _DATA_DIR / "test_case"


@router.post("/seed", response_model=ImportResult)
def seed_dashboard_data(
    session: Annotated[Session, Depends(get_db)],
    source: Literal["preset", "synthetic", "real_test_case"] = Query(...),
) -> ImportResult:
    if source == "real_test_case":
        # backups/test_case/*.json -- the project's real reference data, one
        # single-snapshot Bundle per patient (see clinical_import.py's
        # implicit-visit handling for bundles with no Encounter resource).
        paths = sorted(_TEST_CASE_DIR.glob("*.json"))
        if not paths:
            raise HTTPException(status_code=404, detail=f"no test cases found in {_TEST_CASE_DIR}")
        patients_imported = visits_imported = error_count = 0
        errors: list[dict[str, str]] = []
        for path in paths:
            result = import_bundle(
                session, json.loads(path.read_text(encoding="utf-8")), source_label=source
            )
            patients_imported += result.patients_imported
            visits_imported += result.visits_imported
            error_count += result.error_count
            errors.extend(result.errors)
        invalidate_cache()
        return ImportResult(
            source_label=source,
            patients_imported=patients_imported,
            visits_imported=visits_imported,
            error_count=error_count,
            errors=errors,
        )

    path = _DATA_DIR / f"{source}_patients.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"seed file not found: {path.name}")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    result = import_bundle(session, bundle, source_label=source)
    invalidate_cache()
    return result
