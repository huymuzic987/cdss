"""SQLAlchemy ORM models for the decision-tree schema.

Five tables only: decision_trees, decision_nodes, decision_edges,
node_source_references, development_runtime_logs. No patient, clinical-term,
or drug tables exist anywhere in this system.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cdss.infrastructure.db.base import Base


class NodeType(enum.Enum):
    START = "START"
    CONDITION = "CONDITION"
    INFERENCE = "INFERENCE"
    ACTION = "ACTION"
    END = "END"
    LINK = "LINK"
    GLOBAL = "GLOBAL"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class DecisionTree(Base):
    __tablename__ = "decision_trees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_en: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name_vi: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    nodes: Mapped[list[DecisionNode]] = relationship(back_populates="tree")


class DecisionNode(Base):
    __tablename__ = "decision_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tree_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_trees.id"), nullable=False
    )
    node_key: Mapped[str] = mapped_column(Text, nullable=False)
    node_type: Mapped[NodeType] = mapped_column(ENUM(NodeType, name="node_type"), nullable=False)

    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_vi: Mapped[str] = mapped_column(Text, nullable=False)

    condition_definition: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    context_patch: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    global_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    link_target_tree_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_target_node_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("tree_id", "node_key", name="uq_decision_nodes_tree_id_node_key"),
    )

    tree: Mapped[DecisionTree] = relationship(back_populates="nodes")
    outgoing_edges: Mapped[list[DecisionEdge]] = relationship(
        back_populates="from_node", foreign_keys="DecisionEdge.from_node_id"
    )
    incoming_edges: Mapped[list[DecisionEdge]] = relationship(
        back_populates="to_node", foreign_keys="DecisionEdge.to_node_id"
    )
    source_references: Mapped[list[NodeSourceReference]] = relationship(
        back_populates="decision_node"
    )


class DecisionEdge(Base):
    __tablename__ = "decision_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )
    to_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )
    traversal_order: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("from_node_id", "to_node_id", name="uq_decision_edges_from_to"),
        UniqueConstraint(
            "from_node_id", "traversal_order", name="uq_decision_edges_from_traversal_order"
        ),
        Index("ix_decision_edges_from_node_id", "from_node_id"),
        Index("ix_decision_edges_to_node_id", "to_node_id"),
    )

    from_node: Mapped[DecisionNode] = relationship(
        back_populates="outgoing_edges", foreign_keys=[from_node_id]
    )
    to_node: Mapped[DecisionNode] = relationship(
        back_populates="incoming_edges", foreign_keys=[to_node_id]
    )


class NodeSourceReference(Base):
    __tablename__ = "node_source_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False
    )

    source_title: Mapped[str] = mapped_column(Text, nullable=False)
    section_path: Mapped[Any] = mapped_column(JSONB, nullable=False)

    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    printed_page_numbers: Mapped[list[int] | None] = mapped_column(
        ARRAY(SmallInteger), nullable=True
    )
    pdf_page_numbers: Mapped[list[int] | None] = mapped_column(ARRAY(SmallInteger), nullable=True)

    reference_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        UniqueConstraint(
            "node_id", "reference_order", name="uq_node_source_references_node_id_reference_order"
        ),
        Index("ix_node_source_references_node_id", "node_id"),
    )

    decision_node: Mapped[DecisionNode] = relationship(back_populates="source_references")


class DevelopmentRuntimeLog(Base):
    __tablename__ = "development_runtime_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    environment: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    inference_context: Mapped[Any] = mapped_column(JSONB, nullable=False)
    journey: Mapped[Any] = mapped_column(JSONB, nullable=False)
    output_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    error_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "environment IN ('development', 'test')",
            name="ck_development_runtime_logs_environment",
        ),
        Index("ix_development_runtime_logs_request_id", "request_id"),
        Index("ix_development_runtime_logs_created_at", "created_at"),
    )
