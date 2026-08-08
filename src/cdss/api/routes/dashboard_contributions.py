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
    CommitHistoryItem,
    ContributionsResponse,
    ContributionSummaryResponse,
    ContributorMetricResponse,
    OverlappingTaskResponse,
    RecentCommitItem,
)
from cdss.infrastructure.git_contributions import parse_git_history_snapshot

router = APIRouter()


@router.get("/contributions", response_model=ContributionsResponse)
def get_contributions(
    db: Annotated[Session, Depends(get_db)],
    scope: str = Query("main", pattern="^(main|all)$"),
) -> ContributionsResponse:
    """Fetch live contributor statistics, deliverable catalog, and overlapping task matrix."""
    raw_stats: dict[str, dict[str, Any]] = {}
    history = parse_git_history_snapshot(scope=scope)

    if history.contributors:
        for key, pdata in history.contributors.items():
            raw_stats[key] = {
                "member_key": pdata["member_key"],
                "display_name": pdata["display_name"],
                "canonical_email": pdata["canonical_email"],
                "commit_count": pdata["commit_count"],
                "lines_added": pdata["lines_added"],
                "lines_deleted": pdata["lines_deleted"],
                "total_loc_changes": pdata["lines_added"] + pdata["lines_deleted"],
            }
    else:
        try:
            rows = db.execute(
                text(
                    "SELECT member_key, display_name, canonical_email, commit_count, "
                    "lines_added, lines_deleted, total_loc_changes "
                    "FROM public.git_contributions ORDER BY commit_count DESC"
                )
            ).fetchall()
            for row in rows:
                raw_stats[row.member_key] = {
                    "member_key": row.member_key,
                    "display_name": row.display_name,
                    "canonical_email": row.canonical_email,
                    "commit_count": row.commit_count,
                    "lines_added": row.lines_added,
                    "lines_deleted": row.lines_deleted,
                    "total_loc_changes": row.total_loc_changes,
                }
        except Exception:
            pass

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

    total_commits = sum(s["commit_count"] for s in raw_stats.values())
    total_added = sum(s["lines_added"] for s in raw_stats.values())
    total_deleted = sum(s["lines_deleted"] for s in raw_stats.values())
    total_loc = sum(s["total_loc_changes"] for s in raw_stats.values())
    commit_denominator = total_commits or 1
    added_denominator = total_added or 1
    loc_denominator = total_loc or 1

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
                commits_percentage=round((data["commit_count"] / commit_denominator * 100), 1),
                lines_added=data["lines_added"],
                lines_added_percentage=round((data["lines_added"] / added_denominator * 100), 1),
                lines_deleted=data["lines_deleted"],
                total_loc_changes=data["total_loc_changes"],
                total_loc_percentage=round((data["total_loc_changes"] / loc_denominator * 100), 1),
                primary_role=meta.get("primary_role", "Contributor"),
                deliverables=meta.get("deliverables", []),
            )
        )

    commit_history = [
        CommitHistoryItem(
            hash=commit.hash,
            author=commit.author,
            message=commit.message,
            timestamp=commit.timestamp,
            member_keys=list(commit.member_keys),
        )
        for commit in history.commits
    ]
    if not commit_history and scope == "main":
        try:
            rows = db.execute(
                text(
                    "SELECT commit_hash, author, message, committed_at, member_keys "
                    "FROM public.git_commit_history "
                    "ORDER BY committed_at DESC, commit_hash DESC"
                )
            ).fetchall()
            commit_history = [
                CommitHistoryItem(
                    hash=row.commit_hash,
                    author=row.author,
                    message=row.message,
                    timestamp=row.committed_at,
                    member_keys=list(row.member_keys or []),
                )
                for row in rows
            ]
        except Exception:
            pass
    recent_commits = [
        RecentCommitItem(
            hash=commit.hash,
            author=commit.author,
            message=commit.message,
            timestamp=commit.timestamp,
        )
        for commit in commit_history[:5]
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
        commit_history=commit_history,
        scope=scope,
        updated_at=datetime.now(UTC),
    )
