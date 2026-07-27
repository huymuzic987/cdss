"""Raise the lifestyle BP response threshold to 15/10 mmHg.

Revision ID: c7a41e92d830
Revises: 9f7c2d4a1b6e
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7a41e92d830"
down_revision: str | None = "9f7c2d4a1b6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _set_thresholds(*, sbp: int, dbp: int) -> None:
    op.execute(
        f"""
        UPDATE decision_nodes
        SET condition_definition = jsonb_set(
                jsonb_set(condition_definition, '{{all,0,value}}', to_jsonb({sbp})),
                '{{all,1,value}}', to_jsonb({dbp})
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE node_key = 'T3_C_LIFESTYLE_RESPONSE_ADEQUATE'
        """
    )
    op.execute(
        f"""
        UPDATE decision_nodes
        SET condition_definition = jsonb_set(
                jsonb_set(condition_definition, '{{not,all,0,value}}', to_jsonb({sbp})),
                '{{not,all,1,value}}', to_jsonb({dbp})
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE node_key = 'T3_C_LIFESTYLE_RESPONSE_INADEQUATE'
        """
    )
    op.execute(
        f"""
        UPDATE decision_nodes
        SET action_payload = jsonb_set(
                jsonb_set(
                    action_payload,
                    '{{lifestyle_response_threshold_mmhg,minimum_sbp_reduction}}',
                    to_jsonb({sbp})
                ),
                '{{lifestyle_response_threshold_mmhg,minimum_dbp_reduction}}',
                to_jsonb({dbp})
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE node_key = 'T3_ACTION_LIFESTYLE_FOLLOW_UP_CONTINUE_MONITORING'
        """
    )


def upgrade() -> None:
    _set_thresholds(sbp=15, dbp=10)


def downgrade() -> None:
    _set_thresholds(sbp=10, dbp=5)
