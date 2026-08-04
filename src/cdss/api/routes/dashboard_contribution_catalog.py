"""Static team metadata displayed by the contribution dashboard."""

from typing import Any

MEMBER_DETAILS: dict[str, dict[str, Any]] = {
    "huy": {
        "member_key": "huy",
        "display_name": "Huy",
        "canonical_email": "huymusic987@gmail.com",
        "github_username": "huymuzic987",
        "primary_role": "Lead Architect & Full-Stack Engineer",
        "deliverables": [
            "Core Decision Tree Traversal Walker Engine (walker.py, graph.py, conditions.py)",
            "Smart Follow-Up Evaluation & Active Target Restoration (follow_up.py)",
            "PostgreSQL Relational Schema, Models & Alembic Migrations (models.py)",
            "Single Source of Truth Tooling (backups/seed.sql, scripts/export_trees_to_jsonb.py)",
            "React 19 Shell, Showcase Theme, Connector Toggles & Preset Matrix (patientPresets/)",
            "FastAPI REST API Server & Scalar OpenAPI Docs (main.py)",
        ],
    },
    "quang_minh": {
        "member_key": "quang_minh",
        "display_name": "Quang Minh",
        "canonical_email": "phamlequangminh2411@gmail.com",
        "github_username": "Quangminh_24112005",
        "primary_role": "Full-Stack & Clinical Data Engineer",
        "deliverables": [
            "Pregnancy & Postpartum Longitudinal Pathway Engine (pregnancy_follow_up.py)",
            (
                "21 Pregnancy FHIR Bundle Presets & Synthetic Generator "
                "(generate_pregnancy_fhir_presets.py)"
            ),
            "Decision Tree SQL Authoring (Trees 6, 8, 11, 12, 14)",
            "Synthetic Patient Dataset Generator (generate_synthetic_patients.py)",
            "Analytics Dashboard Backend & Chart Components (dashboard.py, BarStat.tsx)",
            "Medication Lookup Catalog & Drug Classes (medicines.py, drug_classes.py)",
        ],
    },
    "khoa_dang": {
        "member_key": "khoa_dang",
        "display_name": "Khoa Dang",
        "canonical_email": "s4030327@rmit.edu.vn",
        "github_username": "Kh04d4n9",
        "primary_role": "Clinical Decision Tree & Feature Developer",
        "deliverables": [
            "Decision Tree SQL Authoring (Trees 7, 9, 10, 13)",
            "Dynamic Tree Layout Persistence API (/trees/{tree_key}/layout, tree_layout.py)",
            "Drug Tolerance UI Controls & Traversal Checkboxes (DrugToleranceCheckbox.tsx)",
        ],
    },
    "john_tran": {
        "member_key": "john_tran",
        "display_name": "John Tran",
        "canonical_email": "s3929597@rmit.edu.vn",
        "github_username": "John Tran",
        "primary_role": "Backend Reliability & Quality Engineer",
        "deliverables": [
            "Pre-Deployment Quality Gate Script & Pipeline Checks (deploy/run_quality_gates.sh)",
            "React Error Boundary UI Safety Component (ErrorBoundary.tsx)",
            "Modular API Types Barrel Refactoring (frontend/src/api/types/)",
            (
                "Unified Developer Test Runner Scripts (test-backend.sh, "
                "test-frontend.sh, test-all.sh)"
            ),
            "Comprehensive Project Documentation Suite (docs/api.md, docs/architecture.md, etc.)",
        ],
    },
    "uyen": {
        "member_key": "uyen",
        "display_name": "NgPhUyen",
        "canonical_email": "s4037158@rmit.edu.vn",
        "github_username": "NgPhUyen",
        "primary_role": "UI/UX & Clinical Presentation Engineer",
        "deliverables": [
            "Clinical Decision Support Alert Pop-up Modal (TraversalResultModal.tsx)",
            "Clinical Presentation & Localized Message Adapter (clinicalDecisionSupportAdapter.ts)",
            "Collapsible Sidebar Panels & Theme Contrast Improvements (App.css)",
            "Icon Standardization & Canvas Legend Controls",
        ],
    },
}

OVERLAPPING_MATRIX: list[dict[str, Any]] = [
    {
        "feature_area": "Decision Trees 1-14 Authoring & Maintenance",
        "collaborators": ["Khoa Dang", "Quang Minh", "Huy"],
        "shared_deliverables": (
            "Khoa authored Trees 7,9,10,13; Quang Minh authored Trees 6,8,11,12,14; "
            "Huy unified all into seed.sql, fixed dead-end nodes, and created JSONB exporter."
        ),
    },
    {
        "feature_area": "Clinical Evaluation & Follow-Up Engine",
        "collaborators": ["Huy", "Quang Minh", "Khoa Dang"],
        "shared_deliverables": (
            "Huy built core walker and smart follow-up; Quang Minh added pregnancy "
            "follow-up; Khoa added drug tolerance evaluation state."
        ),
    },
    {
        "feature_area": "Mock Patient Form & Presets",
        "collaborators": ["Huy", "Uyen", "Khoa Dang", "John Tran"],
        "shared_deliverables": (
            "Huy built sidebar & preset matrix; Uyen added collapsible styling & theme "
            "contrast; Khoa added tolerance section; John refactored API types."
        ),
    },
    {
        "feature_area": "Clinical Alert Pop-up Modal",
        "collaborators": ["Uyen", "Quang Minh", "John Tran", "Huy"],
        "shared_deliverables": (
            "Uyen built modal UI & rationale adapter; Quang Minh integrated drug lookup "
            "DB; John added ErrorBoundary wrapper; Huy wired modal state into traversal hooks."
        ),
    },
    {
        "feature_area": "Analytics Dashboard & Data Pipeline",
        "collaborators": ["Quang Minh", "Khoa Dang", "John Tran"],
        "shared_deliverables": (
            "Quang Minh built synthetic patient generator & charts; Khoa updated layout "
            "DB models; John refactored dashboard error route refactor."
        ),
    },
    {
        "feature_area": "CI/CD Pipeline & Quality Gates",
        "collaborators": ["John Tran", "Quang Minh", "Huy"],
        "shared_deliverables": (
            "John built run_quality_gates.sh & Jenkins gates; Quang Minh configured build "
            "email notifications; Huy authored Docker launch scripts."
        ),
    },
]
