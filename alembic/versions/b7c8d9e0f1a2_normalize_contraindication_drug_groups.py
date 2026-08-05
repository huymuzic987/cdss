"""normalize contraindication groups to medicine subgroups

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7c8d9e0f1a2"
down_revision: str | None = "a6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_GROUPS = {
    "CD0001": "LT Thiazide",
    "CD0002": "LT Thiazide",
    "CD0003": "CB",
    "CD0004": "LT Thiazide",
    "CD0005": "CB",
    "CD0006": "LT Thiazide",
    "CD0007": "ƯCMC",
    "CD0008": "CTTA",
    "CD0009": "Ức chế Renin trực tiếp",
    "CD0010": "LT Thiazide",
    "CD0011": "LT Thiazide",
    "CD0012": "CB",
    "CD0013": "CB",
    "CD0014": "CKCa Non-DHP",
    "CD0015": "CB",
    "CD0016": "CKCa Non-DHP",
    "CD0017": "CB",
    "CD0018": "CKCa Non-DHP",
    "CD0019": "CB",
    "CD0020": "CKCa DHP",
    "CD0021": "CKCa DHP",
    "CD0022": "CKCa DHP",
    "CD0023": "CKCa Non-DHP",
    "CD0024": "CKCa Non-DHP",
    "CD0025": "ƯCMC",
    "CD0026": "ƯCMC",
    "CD0027": "CTTA",
    "CD0028": "MRA (LT giữ Kali)",
    "CD0029": "ƯCMC",
    "CD0030": "CTTA",
    "CD0031": "MRA (LT giữ Kali)",
    "CD0032": "MRA (LT giữ Kali)",
    "CD0033": "ƯCMC",
    "CD0034": "CTTA",
}

_THIAZIDE_LIKE_COPIES = {
    "CD0035": "CD0001",
    "CD0036": "CD0002",
    "CD0037": "CD0004",
    "CD0038": "CD0006",
    "CD0039": "CD0010",
    "CD0040": "CD0011",
}


def upgrade() -> None:
    connection = op.get_bind()
    for contraindication_id, drug_group in _GROUPS.items():
        connection.execute(
            sa.text(
                """
                UPDATE contraindication_drugs
                SET drug_group = :drug_group
                WHERE contraindication_id = :contraindication_id
                """
            ),
            {
                "contraindication_id": contraindication_id,
                "drug_group": drug_group,
            },
        )

    for new_id, source_id in _THIAZIDE_LIKE_COPIES.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO contraindication_drugs (
                    contraindication_id, disease_finding_vn, disease_finding_eng,
                    contraindication_type, drug_group, drugs, icd10_vn_1_decimal,
                    snomedct_2026_06_01, target, finding_key, fact_key, operator, threshold
                )
                SELECT
                    :new_id, disease_finding_vn, disease_finding_eng,
                    contraindication_type, 'LT Thiazide-like', drugs,
                    icd10_vn_1_decimal, snomedct_2026_06_01, target, finding_key,
                    fact_key, operator, threshold
                FROM contraindication_drugs
                WHERE contraindication_id = :source_id
                ON CONFLICT (contraindication_id) DO UPDATE SET
                    disease_finding_vn = EXCLUDED.disease_finding_vn,
                    disease_finding_eng = EXCLUDED.disease_finding_eng,
                    contraindication_type = EXCLUDED.contraindication_type,
                    drug_group = EXCLUDED.drug_group,
                    drugs = EXCLUDED.drugs,
                    icd10_vn_1_decimal = EXCLUDED.icd10_vn_1_decimal,
                    snomedct_2026_06_01 = EXCLUDED.snomedct_2026_06_01,
                    target = EXCLUDED.target,
                    finding_key = EXCLUDED.finding_key,
                    fact_key = EXCLUDED.fact_key,
                    operator = EXCLUDED.operator,
                    threshold = EXCLUDED.threshold
                """
            ),
            {"new_id": new_id, "source_id": source_id},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for new_id in _THIAZIDE_LIKE_COPIES:
        connection.execute(
            sa.text(
                "DELETE FROM contraindication_drugs "
                "WHERE contraindication_id = :contraindication_id"
            ),
            {"contraindication_id": new_id},
        )
