# Mock-Patient Integration Test Matrix

Status: verified against the populated Trees 1-5 database on 2026-06-29 using
read-only PostgreSQL transactions.

The fixtures and exact trace/reference expectations are frozen in
`tests/db/test_mock_patient_scenarios.py`. All values below were selected from
the stored condition boundaries, context patches, LINK predicates, and action
payloads.

| Fixture | Purpose and key input fields | Expected terminal status | Expected actions | Unresolved target |
| --- | --- | --- | --- | --- |
| `tree_1_normal_bp_route` | Essential route: clinic readings `120/80` for visits 1-3; no out-of-office fields. | Success at `T1_END_ESSENTIAL_NORMAL_BP`; context class `NORMAL_BP`. | None. | None. |
| `tree_1_emergency_route_now_needs_pregnancy_status` | First clinic reading `180/80`, satisfying the stored SBP crisis threshold. | `MissingRuntimePath` on `input.is_pregnant`, raised at the very first candidate evaluation (non-short-circuit `any`/`all`), before the LINK is reached. | None. | None (fails before reaching `hypertensive-emergency`). |
| `tree_3_lifestyle_follow_up_meets_stored_10_5_rule` | Lifestyle follow-up; pre/current readings `150/95` and `140/90`, exactly meeting stored reductions of 10/5 mmHg. | Success at terminal lifestyle ACTION. | `CONTINUE_LIFESTYLE_AND_MONITORING`. | None. |
| `tree_3_medication_follow_up_restores_and_uses_target` | Medication follow-up, `FULL_RESOURCES`, initial regimen, active target `<130/<80`, current `129/79`. | Success through Tree 5 after COPY_PATH restoration and dynamic target comparison. | `CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN`. | None. |
| `tree_4_target_reached_emits_maintain_regimen_action` | Medication follow-up, `LIMITED_RESOURCES`, initial regimen, active target `<130/<80`, current `129/79`. | Success through Tree 4. | `Tiếp tục theo dõi và duy trì phác đồ` (`MAINTAIN_CURRENT_REGIMEN`). | None. |
| `tree_5_initial_regimen_not_reached_resolves_link_then_needs_more_input` | Medication follow-up, `FULL_RESOURCES`, initial regimen, target `<130/<80`, current `130/80`. | LINK resolves into `drug-combination` and executes 4 of its ACTION nodes, then `MissingRuntimePath` on `input.has_heart_failure`. | `FIXED_DOSE_THREE_DRUG_COMBINATION` (A+C+D, one pill) plus 4 `drug-combination` ACTIONs (compare prescription, maintain x2, check duplicate class). | None (fully resolved). |
| `tree_5_escalated_regimen_resolves_link_and_reaches_resistant_hypertension_terminal` | Medication follow-up, `FULL_RESOURCES`, escalated regimen, target `<130/<80`, current `130/80`. | Success; LINK resolves into `resistant-hypertension` and reaches `T13_END_REFER`. Context status `RESISTANT_HYPERTENSION`, pill count 2, additional options retained. | 3 `resistant-hypertension` ACTIONs: lifestyle changes, consider device intervention, refer to specialized center. | None (fully resolved). |

## Coverage Gaps

As of 2026-07-05, `hypertensive-emergency`, `hypertension-heart-failure`,
`hypertension-coronary-artery-disease`, `hypertension-type-2-diabetes`,
`hypertension-chronic-kidney-disease`, `hypertension-in-pregnancy`,
`drug-combination`, and `resistant-hypertension` are also seeded (see
`backups/cdss_merged.sql`). Only `hypertension-older-adults` remains an
external, unseeded LINK target and still produces a typed `LinkTargetNotFound`
failure.

Because the emergency, drug-combination, and heart-failure/coronary/CKD
modifier trees require runtime input fields (e.g. `is_pregnant`,
`has_target_organ_damage`, `has_heart_failure`) that the Trees 1-5 fixtures in
this matrix never had to supply, traversing into them with these existing
fixtures now resolves the LINK and continues, then fails with a typed
`MissingRuntimePath` instead of `LinkTargetNotFound`. The `resistant-hypertension`
route (Tree 5's escalated-regimen-not-reached fixture) is unaffected by this
and now runs to a full successful terminal action inside
`resistant-hypertension`.
