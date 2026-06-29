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
| `tree_1_emergency_route_preserves_partial_state` | First clinic reading `180/80`, satisfying the stored SBP crisis threshold. | `LinkTargetNotFound`; partial context class `HYPERTENSIVE_EMERGENCY`. | None. | `hypertensive-emergency`. |
| `tree_3_lifestyle_follow_up_meets_stored_10_5_rule` | Lifestyle follow-up; pre/current readings `150/95` and `140/90`, exactly meeting stored reductions of 10/5 mmHg. | Success at terminal lifestyle ACTION. | `CONTINUE_LIFESTYLE_AND_MONITORING`. | None. |
| `tree_3_medication_follow_up_restores_and_uses_target` | Medication follow-up, `FULL_RESOURCES`, initial regimen, active target `<130/<80`, current `129/79`. | Success through Tree 5 after COPY_PATH restoration and dynamic target comparison. | `CONTINUE_MONITORING_AND_MAINTAIN_REGIMEN`. | None. |
| `tree_4_target_reached_emits_maintain_regimen_action` | Medication follow-up, `LIMITED_RESOURCES`, initial regimen, active target `<130/<80`, current `129/79`. | Success through Tree 4. | `Tiếp tục theo dõi và duy trì phác đồ` (`MAINTAIN_CURRENT_REGIMEN`). | None. |
| `tree_5_initial_regimen_not_reached_preserves_action_and_state` | Medication follow-up, `FULL_RESOURCES`, initial regimen, target `<130/<80`, current `130/80`. | `LinkTargetNotFound` with copied target, action, trace, and evidence retained. | `FIXED_DOSE_THREE_DRUG_COMBINATION` (A+C+D, one pill). | `drug-combination`. |
| `tree_5_escalated_regimen_not_reached_preserves_resistant_state` | Medication follow-up, `FULL_RESOURCES`, escalated regimen, target `<130/<80`, current `130/80`. | `LinkTargetNotFound`; partial context status `RESISTANT_HYPERTENSION`, pill count 2, and stored options retained. | None before transfer. | `resistant-hypertension`. |

## Coverage Gaps

Only Trees 1-5 are seeded. Successful behavior beyond these external targets
cannot be covered yet: `hypertensive-emergency`, `hypertension-heart-failure`,
`hypertension-older-adults`, `hypertension-coronary-artery-disease`,
`hypertension-type-2-diabetes`, `hypertension-chronic-kidney-disease`,
`drug-combination`, and `resistant-hypertension`.

The suite verifies the expected typed failure and complete partial execution
state for the emergency, drug-combination, and resistant-hypertension routes.
The other five modifier-tree dependencies remain warning-only validator
coverage until their trees are seeded.
