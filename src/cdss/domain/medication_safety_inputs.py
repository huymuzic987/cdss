"""Clinical-fact accessors and medicine-to-safety-target classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from cdss.domain.medication_safety_contracts import fact_status, fact_value

if TYPE_CHECKING:
    from cdss.domain.decision_tree.medicine_catalog import Medicine

type JsonObject = dict[str, Any]

ABSOLUTE = "ABSOLUTE"
INSUFFICIENT = "INSUFFICIENT_DATA"
RELATIVE = "RELATIVE"
MRA_NAMES = frozenset({"spironolactone", "eplerenone"})
ACE_NAMES = frozenset(
    {
        "benazepril",
        "captopril",
        "enalapril",
        "fosinopril",
        "imidapril",
        "lisinopril",
        "perindopril",
        "quinapril",
        "ramipril",
        "trandolapril",
    }
)
ARB_NAMES = frozenset(
    {
        "azilsartan",
        "candesartan",
        "eprosartan",
        "irbesartan",
        "losartan",
        "olmesartan",
        "telmisartan",
        "valsartan",
    }
)
BETA_BLOCKER_NAMES = frozenset(
    {
        "acebutolol",
        "atenolol",
        "bisoprolol",
        "carvedilol",
        "esmolol",
        "labetalol",
        "nadolol",
        "nebivolol",
        "propranolol",
    }
)
NON_DHP_NAMES = frozenset({"diltiazem", "verapamil"})
DHP_NAMES = frozenset(
    {"amlodipine", "felodipine", "isradipine", "lercanidipine", "nifedipine", "nitrendipine"}
)
THIAZIDE_NAMES = frozenset(
    {"bendroflumethiazide", "chlorthalidone", "hydrochlorothiazide", "indapamide"}
)
NONSELECTIVE_BETA_BLOCKERS = frozenset({"propranolol", "nadolol", "carvedilol", "labetalol"})
ALIASES = {
    "pregnancy_status": ("pregnancy_status", "is_pregnant"),
    "breastfeeding_status": ("breastfeeding_status", "is_breastfeeding"),
    "serum_potassium": ("serum_potassium", "potassium"),
    "eGFR": ("eGFR", "egfr"),
    "active_bronchospasm": ("active_bronchospasm",),
    "asthma_severity": ("asthma_severity", "has_asthma"),
    "heart_rate": ("heart_rate",),
    "AV_block_grade": ("AV_block_grade", "av_block_grade"),
    "pacemaker_present": ("pacemaker_present",),
    "LVEF": ("LVEF", "lvef"),
    "gout_status": ("gout_status", "has_gout"),
    "hypercalcaemia": ("hypercalcaemia", "has_hypercalcaemia"),
    "hypokalaemia": ("hypokalaemia", "has_hypokalaemia"),
    "monitoring_plan": ("monitoring_plan",),
}


def target_for_medicine(medicine: Medicine | Mapping[str, Any], selector: str | None = None) -> str:
    name = str(medicine.get("name", "") if isinstance(medicine, Mapping) else medicine.name)
    subgroup = str(
        medicine.get("subgroup", "") if isinstance(medicine, Mapping) else medicine.subgroup
    )
    lowered = f"{name} {subgroup}".casefold()
    selector = selector or (
        medicine.get("drug_class") if isinstance(medicine, Mapping) else medicine.drug_class
    )
    if selector in {"MRA", "MINERALOCORTICOID_RECEPTOR_ANTAGONIST"} or name.casefold() in MRA_NAMES:
        return "MRA"
    if "sodium-glucose" in lowered or "sglt2" in lowered or selector == "SGLT2i":
        return "SGLT2_INHIBITOR"
    if name.casefold() == "nicardipine":
        return "NICARDIPINE"
    if name.casefold() in NON_DHP_NAMES or "non-dhp" in lowered or "non-dihydropyridine" in lowered:
        return "NON_DIHYDROPYRIDINE_CCB"
    if name.casefold() in DHP_NAMES or "dhp" in lowered or "dihydropyridine" in lowered:
        return "DIHYDROPYRIDINE_CCB"
    if name.casefold() in ACE_NAMES or "ace" in lowered:
        return "ACE_INHIBITOR"
    if (
        name.casefold() in ARB_NAMES
        or "angiotensin ii" in lowered
        or "arb" in lowered
        or "ctta" in lowered
    ):
        return "ARB"
    if selector == "A":
        return "ARB"
    if "renin" in lowered or name.casefold() == "aliskiren":
        return "DIRECT_RENIN_INHIBITOR"
    if name.casefold() in BETA_BLOCKER_NAMES or selector == "B" or "beta" in lowered:
        return "BETA_BLOCKER"
    if (
        name.casefold() in THIAZIDE_NAMES
        or "thiazide" in lowered
        or "thiazide-like" in lowered
        or (selector == "D" and not name.strip() and not subgroup.strip())
    ):
        return "THIAZIDE_LIKE_DIURETIC"
    if selector == "D":
        return "OTHER"
    return str(selector or "OTHER")


def facts(runtime: Mapping[str, Any]) -> Mapping[str, Any]:
    structured = runtime.get("clinical_facts")
    return structured if isinstance(structured, Mapping) else runtime


def fact(runtime: Mapping[str, Any], key: str) -> object:
    source = facts(runtime)
    for alias in ALIASES.get(key, (key,)):
        if alias in source:
            value = source[alias]
            if isinstance(value, Mapping) and "status" in value:
                return value
            if isinstance(value, bool):
                return {"status": "present" if value else "absent", "value": value}
            return {"status": "present", "value": value}
    return {"status": "unknown", "evidence": []}


def present(runtime: Mapping[str, Any], key: str) -> bool:
    value = fact(runtime, key)
    return fact_status(value) == "present" and bool(fact_value(value))


def number(runtime: Mapping[str, Any], key: str) -> float | None:
    raw = fact_value(fact(runtime, key))
    return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None


def evidence(runtime: Mapping[str, Any], keys: Sequence[str]) -> list[JsonObject]:
    for key in keys:
        value = fact(runtime, key)
        raw = value.get("evidence") if isinstance(value, Mapping) else None
        if isinstance(raw, (list, tuple)):
            return deepcopy(list(raw))
    return []


def fact_known(runtime: Mapping[str, Any], key: str) -> bool:
    value = fact(runtime, key)
    return fact_status(value) == "present" and fact_value(value) is not None
