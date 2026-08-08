"""Evaluate catalog contraindications against a canonical FHIR R4 Bundle."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cdss.domain.contraindications.contraindication_catalog import (
    ContraindicationDrug,
    ContraindicationDrugRepository,
)
from cdss.domain.contraindications.contraindication_matching import (
    code_evidence,
    condition_codings,
    fact_matches,
    reason_code,
    row_value,
    target_for_group,
    unique_evidence,
    unique_findings,
)
from cdss.domain.medication_safety.medication_safety_contracts import finding
from cdss.domain.medication_safety.medication_safety_inputs import evidence

type JsonObject = dict[str, Any]


def prepare_contraindication_input(
    runtime_input: JsonObject,
    bundle: Mapping[str, Any],
    repository: ContraindicationDrugRepository | Sequence[ContraindicationDrug],
) -> JsonObject:
    """Add catalog matches to the input that will seed traversal."""

    rules = list(repository) if isinstance(repository, Sequence) else list(repository.list_all())
    findings = evaluate_contraindications(runtime_input, bundle, rules)
    existing = runtime_input.get("contraindication_findings")
    prior_findings = (
        existing
        if isinstance(existing, list) and all(isinstance(item, Mapping) for item in existing)
        else []
    )
    runtime_input["contraindication_findings"] = unique_findings([*prior_findings, *findings])
    existing_targets = runtime_input.get("contraindicated_drug_classes")
    targets = {
        str(item.get("target"))
        for item in runtime_input["contraindication_findings"]
        if isinstance(item, Mapping) and isinstance(item.get("target"), str)
    }
    if isinstance(existing_targets, list):
        targets.update(item for item in existing_targets if isinstance(item, str))
    runtime_input["contraindicated_drug_classes"] = sorted(targets)
    runtime_input["contraindication_catalog_loaded"] = True
    return runtime_input


def evaluate_contraindications(
    runtime_input: Mapping[str, Any],
    bundle: Mapping[str, Any],
    rules: Sequence[ContraindicationDrug],
) -> list[JsonObject]:
    """Return every absolute or relative catalog rule matched by the patient."""

    codings = condition_codings(bundle)
    matches: list[JsonObject] = []
    for rule in rules:
        target = str(row_value(rule, "target") or target_for_group(row_value(rule, "drug_group")))
        if not target:
            continue
        matched_evidence = code_evidence(rule, codings)
        fact_key = row_value(rule, "fact_key")
        if fact_key and fact_matches(
            runtime_input, str(fact_key), row_value(rule, "operator"), row_value(rule, "threshold")
        ):
            matched_evidence.extend(evidence(runtime_input, (str(fact_key),)))
            if not matched_evidence:
                matched_evidence.append({"source": f"clinical_facts/{fact_key}"})
        if not matched_evidence:
            continue
        severity = str(row_value(rule, "contraindication_type") or "").upper()
        if severity not in {"ABSOLUTE", "RELATIVE"}:
            continue
        finding_item = finding(
            target=target,
            severity=severity,  # type: ignore[arg-type]
            reason_code=reason_code(row_value(rule, "finding_key"), rule),
            reason_en=str(
                row_value(rule, "disease_finding_eng")
                or row_value(rule, "disease_finding_vn")
                or "Catalog contraindication"
            ),
            evidence=unique_evidence(matched_evidence),
            override_allowed=severity == "RELATIVE",
        )
        finding_item["source_rule"] = str(row_value(rule, "contraindication_id") or "")
        finding_item["finding_key"] = str(row_value(rule, "finding_key") or "")
        finding_item["drug_group"] = str(row_value(rule, "drug_group") or "")
        drug_name = row_value(rule, "drugs")
        if isinstance(drug_name, str) and drug_name.strip():
            finding_item["drugs"] = drug_name.strip()
        matches.append(finding_item)
    return unique_findings(matches)
