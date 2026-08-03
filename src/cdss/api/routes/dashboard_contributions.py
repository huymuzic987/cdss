"""API route for self-hosted live team contribution tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_db
from cdss.api.schemas.dashboard import (
    ContributionSummaryResponse,
    ContributionsResponse,
    ContributorMetricResponse,
    OverlappingTaskResponse,
    RecentCommitItem,
)
from scripts.update_contributions_db import parse_git_history

router = APIRouter()

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
            "21 Pregnancy FHIR Bundle Presets & Synthetic Generator (generate_pregnancy_fhir_presets.py)",
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
            "Unified Developer Test Runner Scripts (test-backend.sh, test-frontend.sh, test-all.sh)",
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
        "shared_deliverables": "Khoa authored Trees 7,9,10,13; Quang Minh authored Trees 6,8,11,12,14; Huy unified all into seed.sql, fixed dead-end nodes, and created JSONB exporter.",
    },
    {
        "feature_area": "Clinical Evaluation & Follow-Up Engine",
        "collaborators": ["Huy", "Quang Minh", "Khoa Dang"],
        "shared_deliverables": "Huy built core walker and smart follow-up; Quang Minh added pregnancy follow-up; Khoa added drug tolerance evaluation state.",
    },
    {
        "feature_area": "Mock Patient Form & Presets",
        "collaborators": ["Huy", "Uyen", "Khoa Dang", "John Tran"],
        "shared_deliverables": "Huy built sidebar & preset matrix; Uyen added collapsible styling & theme contrast; Khoa added tolerance section; John refactored API types.",
    },
    {
        "feature_area": "Clinical Alert Pop-up Modal",
        "collaborators": ["Uyen", "Quang Minh", "John Tran", "Huy"],
        "shared_deliverables": "Uyen built modal UI & rationale adapter; Quang Minh integrated drug lookup DB; John added ErrorBoundary wrapper; Huy wired modal state into traversal hooks.",
    },
    {
        "feature_area": "Analytics Dashboard & Data Pipeline",
        "collaborators": ["Quang Minh", "Khoa Dang", "John Tran"],
        "shared_deliverables": "Quang Minh built synthetic patient generator & charts; Khoa updated layout DB models; John refactored dashboard error route refactor.",
    },
    {
        "feature_area": "CI/CD Pipeline & Quality Gates",
        "collaborators": ["John Tran", "Quang Minh", "Huy"],
        "shared_deliverables": "John built run_quality_gates.sh & Jenkins gates; Quang Minh configured build email notifications; Huy authored Docker launch scripts.",
    },
]


@router.get("/contributions", response_model=ContributionsResponse)
def get_contributions(
    scope: str = Query("main", pattern="^(main|all)$"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:

    """Fetch live contributor statistics, deliverable catalog, and overlapping task matrix."""
    raw_stats: dict[str, dict[str, Any]] = {}

    # Try fetching from PostgreSQL database table first
    try:
        rows = db.execute(
            text(
                "SELECT member_key, display_name, canonical_email, commit_count, lines_added, lines_deleted, total_loc_changes FROM public.git_contributions ORDER BY commit_count DESC"
            )
        ).fetchall()

        if rows:
            for r in rows:
                raw_stats[r.member_key] = {
                    "member_key": r.member_key,
                    "display_name": r.display_name,
                    "canonical_email": r.canonical_email,
                    "commit_count": r.commit_count,
                    "lines_added": r.lines_added,
                    "lines_deleted": r.lines_deleted,
                    "total_loc_changes": r.total_loc_changes,
                }
    except Exception:
        pass

    # Fallback to parsing local git log if DB table is unseeded
    if not raw_stats:
        git_parsed = parse_git_history(scope=scope)
        for key, pdata in git_parsed.items():
            raw_stats[key] = {
                "member_key": pdata["member_key"],
                "display_name": pdata["display_name"],
                "canonical_email": pdata["canonical_email"],
                "commit_count": pdata["commit_count"],
                "lines_added": pdata["lines_added"],
                "lines_deleted": pdata["lines_deleted"],
                "total_loc_changes": pdata["lines_added"] + pdata["lines_deleted"],
            }

    # Ensure all 5 canonical members exist in final results
    for key, meta in MEMBER_DETAILS.items():
        if key not in raw_stats:
            raw_stats[key] = {
                "member_key": key,
                "display_name": meta["display_name"],
                "canonical_email": meta["canonical_email"],
                "commit_count": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "total_loc_changes": 0,
            }

    total_commits = sum(s["commit_count"] for s in raw_stats.values()) or 1
    total_added = sum(s["lines_added"] for s in raw_stats.values()) or 1
    total_deleted = sum(s["lines_deleted"] for s in raw_stats.values())
    total_loc = sum(s["total_loc_changes"] for s in raw_stats.values()) or 1

    contributors = []
    for key, data in sorted(
        raw_stats.items(), key=lambda item: item[1]["commit_count"], reverse=True
    ):
        meta = MEMBER_DETAILS.get(
            key,
            {
                "display_name": data["display_name"],
                "github_username": data["display_name"],
                "primary_role": "Contributor",
                "deliverables": ["Code maintenance and general commits"],
            },
        )


        contributors.append(
            ContributorMetricResponse(
                member_key=key,
                display_name=meta.get("display_name", data["display_name"]),
                canonical_email=data["canonical_email"],
                github_username=meta.get("github_username"),
                commits=data["commit_count"],
                commits_percentage=round((data["commit_count"] / total_commits * 100), 1),
                lines_added=data["lines_added"],
                lines_added_percentage=round((data["lines_added"] / total_added * 100), 1),
                lines_deleted=data["lines_deleted"],
                total_loc_changes=data["total_loc_changes"],
                total_loc_percentage=round((data["total_loc_changes"] / total_loc * 100), 1),
                primary_role=meta.get("primary_role", "Contributor"),
                deliverables=meta.get("deliverables", []),
            )
        )

    # Sample recent commits
    recent_commits = [
        RecentCommitItem(
            hash="010d9c7",
            author="huymuzic987",
            message="refactor: remove legacy bp_target_reached boolean from decision trees and frontend",
            timestamp=1754104800,
        ),
        RecentCommitItem(
            hash="72b8e37",
            author="John Tran",
            message="ci: add pre-deployment quality gate script and Jenkins checks",
            timestamp=1754018400,
        ),
        RecentCommitItem(
            hash="cda39d4",
            author="NgPhUyen",
            message="[Fix]: modify detail of pop up alert modal",
            timestamp=1753932000,
        ),
        RecentCommitItem(
            hash="8358e75",
            author="Kh04d4n9",
            message="Fix: display drug tolerance checkbox during full traversal",
            timestamp=1753552800,
        ),
        RecentCommitItem(
            hash="78fca52",
            author="Quangminh_24112005",
            message="Med lookup database & drug class mapping",
            timestamp=1752948000,
        ),
    ]

    return ContributionsResponse(
        summary=ContributionSummaryResponse(
            total_commits=total_commits,
            total_lines_added=total_added,
            total_lines_deleted=total_deleted,
            total_loc_changes=total_loc,
            active_contributors=len(contributors),
        ),
        contributors=contributors,
        overlapping_matrix=[
            OverlappingTaskResponse(
                feature_area=item["feature_area"],
                collaborators=item["collaborators"],
                shared_deliverables=item["shared_deliverables"],
            )
            for item in OVERLAPPING_MATRIX
        ],
        recent_commits=recent_commits,
        scope=scope,
        updated_at=datetime.now(timezone.utc),
    )
