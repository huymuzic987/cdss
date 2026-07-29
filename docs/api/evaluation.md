# Clinical Evaluation API

Clinical evaluation converts a FHIR Bundle into engine input, walks one or
more database-defined decision trees, and returns recommendations plus audit
information. It is stateless and does not save a patient record.

## `POST /evaluate`

The request contains a `start_tree_key` and an HL7 FHIR R4 collection Bundle.

```json
{
  "start_tree_key": "treatment-threshold-and-bp-target",
  "input": {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": []
  }
}
```

Real evaluations require clinical resources in `entry`. See the
[complete field mapping](complete-reference.md#12-the-input-bundle-contract) for supported
Patient, Observation, Condition, and Parameters shapes.

## Request flow

```text
FHIR Bundle
  -> validate request
  -> flatten supported FHIR resources
  -> optionally infer follow-up state
  -> load and validate the start tree
  -> traverse nodes and cross-tree links
  -> select client-facing actions
  -> serialize result or typed error
```

### FHIR-to-engine mapping

- `Patient.birthDate` becomes age in years.
- Blood-pressure Observations provide readings for a named reading role.
- Supported lab Observations become numeric input fields.
- Supported Conditions become boolean clinical flags unless refuted.
- Parameters carry workflow values and explicitly named inputs.

Malformed supported resources return HTTP 422. Unknown resource types are
ignored because evaluation does not interpret the entire FHIR ecosystem.

### Follow-up inference

When previous systolic and diastolic readings are present, the API replays the
previous encounter through the diagnosis tree. It classifies the current
encounter as initial, lifestyle follow-up, or medication follow-up. A detected
follow-up can override the requested entry point with the treatment-threshold
tree.

## Successful response

The response includes normalized input, final shared context, selected
clinical actions, traversal log, references, visited-tree metadata, and
timestamps. Normal output selects the terminal recommendation; debug output
can expose the full action trail for authoring and audit work.

## `POST /evaluate/follow-up`

This narrower endpoint is for callers that already know the active blood
pressure target, medication stage, and current reading. It skips replay-based
inference and starts from the treatment-threshold tree. Use `/evaluate` unless
the caller genuinely owns that follow-up state.

## Failure behavior

| Status | Meaning |
| --- | --- |
| 404 | Requested decision tree was not found |
| 422 | FHIR input, clinical input, or traversal choice was invalid |
| 424 | A `LINK` target tree or node could not be resolved |
| 500 | Unexpected server or invalid stored-graph failure |

Traversal failures may include partial actions, context, and trace data so a
client can show how far evaluation progressed.

## Deeper references

- [Complete HTTP shapes and examples](complete-reference.md#1-evaluation)
- [Traversal engine contract](../cdss/traversal-engine-contract.md)
- [Context contract](../cdss/context-contract.md)
- [Decision-tree JSON dialect](../cdss/json-dialect.md)
