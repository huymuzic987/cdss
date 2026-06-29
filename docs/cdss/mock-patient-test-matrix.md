# Mock-Patient Integration Test Matrix

Status: blocked pending access to the seeded Trees 1-5 definitions.

## Audit boundary

This checkout contains no seed SQL, JSON fixture, data migration, or seed
loader. `DATABASE_URL` is not configured, and PostgreSQL is not listening on
the documented local port. The schema migration creates no decision-tree rows.
The condition examples in `tree-json-dialect.md` are explicitly syntax-only.

Prompt 9 requires fixture inputs and stable trace sequences to be derived from
the actual stored `condition_definition` values. Supplying concrete inputs from
the examples would invent clinical rules, so the missing values below are left
blocked rather than guessed. The expected outcomes are requirements from Prompt
9, not claims that this checkout's unavailable seeds were inspected.

## Scenario matrix

| Fixture | Purpose | Key input fields | Expected terminal status | Expected actions | Intentionally unresolved target |
| --- | --- | --- | --- | --- | --- |
| `tree1_normal_bp` | Traverse Tree 1 to the node that sets `context.diagnosis.hypertension_class` to `NORMAL_BP`. | Blocked: derive every required path and boundary value from conditions on the selected route. | Success at the seeded terminal node. | Preserve any seeded action payloads on entered ACTION/END nodes. | None. |
| `tree1_emergency` | Traverse Tree 1 to its emergency LINK. | Blocked: derive the emergency branch operands and thresholds from stored conditions. | `LinkTargetNotFound` with partial state. | Preserve all actions emitted before the LINK. | `hypertensive-emergency`. |
| `tree3_lifestyle_follow_up` | Select lifestyle follow-up and satisfy the stored 10/5 improvement rule. | Blocked: derive the follow-up discriminator and subtraction operand paths; choose values satisfying the stored 10 and 5 comparisons. | Success at the seeded lifestyle-monitoring terminal action. | The existing seeded lifestyle-monitoring action. | None. |
| `tree3_medication_follow_up` | Restore the active target, transfer to Tree 4 or 5, and prove downstream comparisons use the restored context value. | `input.active_bp_target`; all route-selection and current-BP paths remain blocked pending seed inspection. | Seed-derived downstream terminal status in Tree 4 or 5. | Preserve actions from the selected downstream route. | None unless the inspected route deliberately terminates at an external LINK. |
| `tree4_target_reached` | Select the target-reached route in the essential treatment strategy. | Blocked: derive current BP paths and the exact target object shape from stored conditions and patches. | Success at the matching ACTION/END node. | `Tiếp tục theo dõi và duy trì phác đồ`. | None. |
| `tree5_initial_regimen_not_at_target` | Follow the initial-regimen, target-not-reached route through its escalation action. | Blocked: derive regimen-state, current-BP, and target paths and values from stored conditions. | `LinkTargetNotFound` with partial state. | The seeded three-drug fixed-dose action. | `drug-combination`. |
| `tree4_or_5_escalated_not_at_target` | Follow an escalated-regimen route that remains above target. | Blocked: derive strategy, regimen-state, current-BP, and target paths and values from stored conditions. | `LinkTargetNotFound` with partial state. | Preserve every seeded action emitted before the LINK. | `resistant-hypertension`. |

## Assertions required once seeds are available

Each fixture must independently load fresh graphs and must assert the exact
ordered node-entry/candidate trace, resulting context, ordered actions, and the
ordered references copied from every entered node. Unresolved-link fixtures
must assert those records on `partial_run_state`. Expected trace and reference
identities must be computed during seed audit and then frozen in test
expectations; deriving expected values from the traversal result itself would
be tautological.

## Coverage gaps

The immediate blocker is broader than the expected external dependencies:
Trees 1-5 themselves are not present in this checkout or an accessible test
database. Therefore none of the seven deterministic mock-patient scenarios can
currently be authored or executed from actual clinical definitions.

Even after Trees 1-5 are supplied, successful execution beyond
`hypertensive-emergency`, `drug-combination`, and `resistant-hypertension`
remains intentionally uncovered until those target trees are seeded. The other
declared external targets are likewise outside this matrix:
`hypertension-heart-failure`, `hypertension-older-adults`,
`hypertension-coronary-artery-disease`, `hypertension-type-2-diabetes`, and
`hypertension-chronic-kidney-disease`.
