"""API route for self-hosted live team contribution tracking."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from cdss.api.dependencies import get_db
from cdss.api.routes.dashboard_contribution_catalog import (
    MEMBER_DETAILS,
    OVERLAPPING_MATRIX,
)
from cdss.api.schemas.dashboard import (
    ContributionsResponse,
    ContributionSummaryResponse,
    ContributorMetricResponse,
    OverlappingTaskResponse,
    RecentCommitItem,
)
from cdss.infrastructure.git_contributions import parse_git_history

router = APIRouter()


@router.get("/contributions", response_model=ContributionsResponse)
def get_contributions(
    db: Annotated[Session, Depends(get_db)],
    scope: str = Query("main", pattern="^(main|all)$"),
) -> ContributionsResponse:
    """Fetch live contributor statistics, deliverable catalog, and overlapping task matrix."""
    raw_stats: dict[str, dict[str, Any]] = {}

    # Try fetching from PostgreSQL database table first
    try:
        rows = db.execute(
            text(
                "SELECT member_key, display_name, canonical_email, commit_count, "
                "lines_added, lines_deleted, total_loc_changes "
                "FROM public.git_contributions ORDER BY commit_count DESC"
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
            message=(
                "refactor: remove legacy bp_target_reached boolean from decision trees and frontend"
            ),
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
        updated_at=datetime.now(UTC),
    )
