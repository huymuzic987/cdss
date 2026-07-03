"""Hand-written HL7 FHIR R4 schemas for the decision-tree knowledge base export.

Only the resource shapes actually needed to represent a decision tree
(`PlanDefinition`, its companion `Library` for GLOBAL nodes, and a `Bundle`
wrapper) are modeled here -- this is not a general-purpose FHIR library.
Field names follow the FHIR R4 JSON element names exactly (via Pydantic
aliases) so responses validate against the official R4 JSON Schema.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from cdss.domain.decision_tree import (
    NodeDefinition,
    NodeType,
    SourceReferenceDefinition,
    TreeGraph,
    validate_condition_definition,
)
from cdss.domain.decision_tree.contracts import JsonValue, copy_json_value

_EXT_BASE = "http://cdss.local/fhir/StructureDefinition"
_EXT_NODE_KEY = f"{_EXT_BASE}/node-key"
_EXT_NAME_VI = f"{_EXT_BASE}/name-vi"
_EXT_TEXT_VI = f"{_EXT_BASE}/text-vi"
_EXT_CONDITION_SOURCE = f"{_EXT_BASE}/condition-definition-source"
_EXT_CONTEXT_PATCH = f"{_EXT_BASE}/context-patch"
_EXT_ACTION_PAYLOAD = f"{_EXT_BASE}/action-payload"
_EXT_LINK_TARGET_NODE = f"{_EXT_BASE}/link-target-node"
_EXT_TRAVERSAL_ORDER = f"{_EXT_BASE}/traversal-order"

_CS_NODE_TYPE = "http://cdss.local/fhir/CodeSystem/node-type"
_CS_PLAN_DEFINITION_TYPE = "http://terminology.hl7.org/CodeSystem/plan-definition-type"
_CS_LIBRARY_TYPE = "http://terminology.hl7.org/CodeSystem/library-type"


class FhirModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# --- Condition DSL -> FHIRPath translation -----------------------------------

_COMPARISON_OPERATOR_SYMBOLS = {"eq": "=", "lt": "<", "lte": "<=", "gt": ">", "gte": ">="}


def condition_to_fhirpath(condition: Mapping[str, Any]) -> str:
    """Translate one validated condition-DSL document into a FHIRPath expression."""

    validate_condition_definition(condition)
    return _translate_condition(condition)


def _translate_condition(expression: Mapping[str, Any]) -> str:
    if "not" in expression:
        return f"(({_translate_condition(expression['not'])}).not())"
    if "all" in expression:
        joined = " and ".join(_translate_condition(child) for child in expression["all"])
        return f"({joined})"
    if "any" in expression:
        joined = " or ".join(_translate_condition(child) for child in expression["any"])
        return f"({joined})"
    return _translate_comparison(expression)


def _translate_comparison(expression: Mapping[str, Any]) -> str:
    operator = expression["op"]
    if operator == "exists":
        return f"({_path_to_fhirpath(expression['path'])}.exists())"

    if "path" in expression:
        left = _path_to_fhirpath(expression["path"])
    else:
        left_expression = expression["left"]
        left = (
            f"({_path_to_fhirpath(left_expression['left_path'])}"
            f" - {_path_to_fhirpath(left_expression['right_path'])})"
        )

    if operator == "in":
        values = " | ".join(_literal_to_fhirpath(value) for value in expression["value"])
        return f"({left} in ({values}))"

    if "value_from_path" in expression:
        right = _path_to_fhirpath(expression["value_from_path"])
    else:
        right = _literal_to_fhirpath(expression["value"])

    return f"({left} {_COMPARISON_OPERATOR_SYMBOLS[operator]} {right})"


def _path_to_fhirpath(path: str) -> str:
    return f"%{path}"


def _literal_to_fhirpath(value: JsonValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    raise ValueError(f"unsupported FHIRPath literal type: {type(value).__name__}")


def _node_key_to_id(node_key: str) -> str:
    return node_key.lower().replace("_", "-")


def _json_extension_value(value: Any) -> str:
    return json.dumps(copy_json_value(value), sort_keys=True)


# --- Shared FHIR datatypes ----------------------------------------------------


class Extension(FhirModel):
    url: str
    value_string: str | None = Field(default=None, alias="valueString")
    value_integer: int | None = Field(default=None, alias="valueInteger")


class Coding(FhirModel):
    system: str
    code: str
    display: str | None = None


class CodeableConcept(FhirModel):
    coding: list[Coding] = Field(default_factory=list)
    text: str | None = None


class RelatedArtifact(FhirModel):
    type: Literal["citation"] = "citation"
    display: str | None = None
    citation: str | None = None


class Expression(FhirModel):
    language: Literal["text/fhirpath"] = "text/fhirpath"
    expression: str


class Attachment(FhirModel):
    content_type: str = Field(alias="contentType")
    data: str


# --- PlanDefinition ------------------------------------------------------------


class PlanDefinitionActionCondition(FhirModel):
    kind: Literal["applicability"] = "applicability"
    expression: Expression


class PlanDefinitionActionRelatedAction(FhirModel):
    action_id: str = Field(alias="actionId")
    relationship: Literal["before-start"] = "before-start"
    extension: list[Extension] | None = None


class PlanDefinitionAction(FhirModel):
    id: str
    extension: list[Extension] | None = None
    code: list[CodeableConcept] | None = None
    title: str | None = None
    condition: list[PlanDefinitionActionCondition] | None = None
    related_action: list[PlanDefinitionActionRelatedAction] | None = Field(
        default=None, alias="relatedAction"
    )
    definition_canonical: str | None = Field(default=None, alias="definitionCanonical")
    documentation: list[RelatedArtifact] | None = None


class PlanDefinition(FhirModel):
    resource_type: Literal["PlanDefinition"] = Field(default="PlanDefinition", alias="resourceType")
    id: str
    extension: list[Extension] | None = None
    status: Literal["active"] = "active"
    type: CodeableConcept | None = None
    name: str | None = None
    title: str | None = None
    library: list[str] | None = None
    action: list[PlanDefinitionAction] = Field(default_factory=list)

    @classmethod
    def from_graph(cls, graph: TreeGraph) -> PlanDefinition:
        actions = [
            _build_action(node, graph)
            for node in sorted(graph.nodes_by_id.values(), key=lambda node: node.display_order)
            if node.node_type is not NodeType.GLOBAL
        ]
        library = [f"Library/{graph.tree.tree_key}-config"] if graph.global_nodes else None
        return cls(
            id=graph.tree.tree_key,
            type=CodeableConcept(
                coding=[Coding(system=_CS_PLAN_DEFINITION_TYPE, code="clinical-protocol")]
            ),
            name=graph.tree.tree_key.replace("-", "_"),
            title=graph.tree.name_en,
            extension=[Extension(url=_EXT_NAME_VI, valueString=graph.tree.name_vi)],
            library=library,
            action=actions,
        )


def _build_action(node: NodeDefinition, graph: TreeGraph) -> PlanDefinitionAction:
    extensions = [Extension(url=_EXT_NODE_KEY, valueString=node.node_key)]
    if node.text_vi:
        extensions.append(Extension(url=_EXT_TEXT_VI, valueString=node.text_vi))

    condition = None
    if node.condition_definition is not None:
        condition = [
            PlanDefinitionActionCondition(
                expression=Expression(
                    expression=condition_to_fhirpath(node.condition_definition),
                ),
            )
        ]
        extensions.append(
            Extension(
                url=_EXT_CONDITION_SOURCE,
                valueString=_json_extension_value(node.condition_definition),
            )
        )

    if node.context_patch is not None:
        extensions.append(
            Extension(url=_EXT_CONTEXT_PATCH, valueString=_json_extension_value(node.context_patch))
        )
    if node.action_payload is not None:
        extensions.append(
            Extension(
                url=_EXT_ACTION_PAYLOAD, valueString=_json_extension_value(node.action_payload)
            )
        )

    related_actions = [
        PlanDefinitionActionRelatedAction(
            actionId=_node_key_to_id(graph.nodes_by_id[edge.to_node_id].node_key),
            extension=[Extension(url=_EXT_TRAVERSAL_ORDER, valueInteger=edge.traversal_order)],
        )
        for edge in graph.outgoing_edges_by_node_id.get(node.id, ())
    ]

    definition_canonical = None
    if node.node_type is NodeType.LINK and node.link_target_tree_key:
        definition_canonical = f"PlanDefinition/{node.link_target_tree_key}"
        if node.link_target_node_key:
            extensions.append(
                Extension(url=_EXT_LINK_TARGET_NODE, valueString=node.link_target_node_key)
            )

    documentation = [
        _reference_to_related_artifact(reference)
        for reference in graph.references_by_node_id.get(node.id, ())
    ]

    return PlanDefinitionAction(
        id=_node_key_to_id(node.node_key),
        extension=extensions,
        code=[CodeableConcept(coding=[Coding(system=_CS_NODE_TYPE, code=node.node_type.value)])],
        title=node.text_en,
        condition=condition,
        relatedAction=related_actions or None,
        definitionCanonical=definition_canonical,
        documentation=documentation or None,
    )


def _reference_to_related_artifact(reference: SourceReferenceDefinition) -> RelatedArtifact:
    locator_parts = [
        part for part in (reference.locator, reference.locator_detail) if part is not None
    ]
    display = reference.source_title
    if locator_parts:
        display = f"{display} ({', '.join(locator_parts)})"
    return RelatedArtifact(
        display=display,
        citation=json.dumps(copy_json_value(reference.section_path), sort_keys=True),
    )


# --- Library (GLOBAL nodes) ----------------------------------------------------


class Library(FhirModel):
    resource_type: Literal["Library"] = Field(default="Library", alias="resourceType")
    id: str
    status: Literal["active"] = "active"
    type: CodeableConcept
    content: list[Attachment] = Field(default_factory=list)

    @classmethod
    def from_graph(cls, graph: TreeGraph) -> Library | None:
        if not graph.global_nodes:
            return None

        payload = [
            {
                "node_key": node.node_key,
                "text_en": node.text_en,
                "text_vi": node.text_vi,
                "global_config": copy_json_value(node.global_config)
                if node.global_config is not None
                else None,
            }
            for node in graph.global_nodes
        ]
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        data = base64.b64encode(encoded).decode("ascii")

        return cls(
            id=f"{graph.tree.tree_key}-config",
            type=CodeableConcept(coding=[Coding(system=_CS_LIBRARY_TYPE, code="logic-library")]),
            content=[Attachment(contentType="application/json", data=data)],
        )


# --- Bundle --------------------------------------------------------------------


class BundleEntry(FhirModel):
    full_url: str | None = Field(default=None, alias="fullUrl")
    resource: PlanDefinition


class Bundle(FhirModel):
    resource_type: Literal["Bundle"] = Field(default="Bundle", alias="resourceType")
    type: Literal["searchset"] = "searchset"
    entry: list[BundleEntry] = Field(default_factory=list)

    @classmethod
    def from_plan_definitions(cls, plan_definitions: Sequence[PlanDefinition]) -> Bundle:
        return cls(
            entry=[
                BundleEntry(fullUrl=f"PlanDefinition/{item.id}", resource=item)
                for item in plan_definitions
            ]
        )
