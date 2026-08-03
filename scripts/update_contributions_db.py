"""Script executed in Jenkins pipeline or standalone to sync Git stats to PostgreSQL."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Database Connection Settings
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "54321")
DB_NAME = os.getenv("POSTGRES_DB", "cdss")
DB_USER = os.getenv("POSTGRES_USER", "cdss")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "cdss")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Alias dictionary mapping email & author strings to canonical member identities
ALIAS_MAP: dict[str, tuple[str, str, str]] = {
    "huymusic987@gmail.com": ("huy", "Huy", "huymuzic987"),
    "huymuzic987": ("huy", "Huy", "huymuzic987"),
    "phamlequangminh2411@gmail.com": ("quang_minh", "Quang Minh", "Quangminh_24112005"),
    "quangminh_24112005": ("quang_minh", "Quang Minh", "Quangminh_24112005"),
    "s4030327@rmit.edu.vn": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "153248299+kh04d4n9@users.noreply.github.com": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "kh04d4n9": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "khoadang": ("khoa_dang", "Khoa Dang", "Kh04d4n9"),
    "s3929597@rmit.edu.vn": ("john_tran", "John Tran", "John Tran"),
    "john tran": ("john_tran", "John Tran", "John Tran"),
    "s4037158@rmit.edu.vn": ("uyen", "NgPhUyen", "NgPhUyen"),
    "ngphuyen": ("uyen", "NgPhUyen", "NgPhUyen"),
}


def resolve_canonical(name: str, email: str) -> tuple[str, str, str]:
    clean_email = email.strip().lower()
    clean_name = name.strip().lower()
    if clean_email in ALIAS_MAP:
        return ALIAS_MAP[clean_email]
    if clean_name in ALIAS_MAP:
        return ALIAS_MAP[clean_name]
    for key, val in ALIAS_MAP.items():
        if key in clean_email or key in clean_name:
            return val
    # Fallback to name/email
    key = re.sub(r"\W+", "_", clean_name)
    return key, name, email


def parse_git_history(scope: str = "main") -> dict[str, dict]:
    ref = "main" if scope == "main" else "--all"
    cmd = [
        "git",
        "log",
        ref,
        "--numstat",
        "--no-merges",
        "--pretty=format:COMMIT_START|%h|%an|%ae|%at|%B|COMMIT_END",
    ]

    try:
        raw_output = subprocess.check_output(
            cmd, cwd=PROJECT_ROOT, encoding="utf-8", errors="ignore"
        )
    except Exception as err:
        print(f"Error executing git log: {err}")
        return {}

    authors: dict[str, dict] = {}

    def get_author_dict(m_key: str, d_name: str, c_email: str) -> dict:
        if m_key not in authors:
            authors[m_key] = {
                "member_key": m_key,
                "display_name": d_name,
                "canonical_email": c_email,
                "commit_count": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "last_hash": None,
            }
        return authors[m_key]

    blocks = raw_output.split("COMMIT_START|")
    for block in blocks:
        if not block.strip():
            continue

        parts = block.split("|COMMIT_END", 1)
        commit_header = parts[0]
        numstat_lines = parts[1].splitlines() if len(parts) > 1 else []

        header_fields = commit_header.split("|", 4)
        if len(header_fields) < 5:
            continue

        hash_str, name, email, ts, body = header_fields
        m_key, d_name, c_email = resolve_canonical(name, email)

        # Identify co-authors from commit body
        co_author_keys = set()
        for line in body.splitlines():
            line_str = line.strip()
            if line_str.lower().startswith("co-authored-by:"):
                co_match = re.search(r"co-authored-by:\s*(.*?)\s*<(.*?)>", line_str, re.IGNORECASE)
                if co_match:
                    co_name, co_email = co_match.group(1), co_match.group(2)
                    c_k, c_d, c_e = resolve_canonical(co_name, co_email)
                    if c_k != m_key:
                        co_author_keys.add((c_k, c_d, c_e))

        all_commit_authors = [(m_key, d_name, c_email)] + list(co_author_keys)
        weight = 1.0 / len(all_commit_authors)

        # Credit commits
        for ak, ad, ae in all_commit_authors:
            adict = get_author_dict(ak, ad, ae)
            adict["commit_count"] += 1
            if not adict["last_hash"]:
                adict["last_hash"] = hash_str

        # Parse numstat
        for line in numstat_lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
            num_parts = line.split()
            if len(num_parts) >= 2 and num_parts[0] != "-" and num_parts[1] != "-":
                added = int(num_parts[0])
                deleted = int(num_parts[1])
                for ak, ad, ae in all_commit_authors:
                    adict = get_author_dict(ak, ad, ae)
                    adict["lines_added"] += int(added * weight)
                    adict["lines_deleted"] += int(deleted * weight)

    return authors


def sync_to_db(authors: dict[str, dict]) -> None:
    if not authors:
        print("No author statistics parsed.")
        return

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            with conn.begin():
                for data in authors.values():
                    total_loc = data["lines_added"] + data["lines_deleted"]
                    stmt = text(
                        """
                        INSERT INTO public.git_contributions 
                            (id, member_key, display_name, canonical_email, commit_count, lines_added, lines_deleted, total_loc_changes, last_commit_hash, updated_at)
                        VALUES (gen_random_uuid(), :member_key, :display_name, :canonical_email, :commit_count, :lines_added, :lines_deleted, :total_loc_changes, :last_commit_hash, NOW())
                        ON CONFLICT (member_key) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            canonical_email = EXCLUDED.canonical_email,
                            commit_count = EXCLUDED.commit_count,
                            lines_added = EXCLUDED.lines_added,
                            lines_deleted = EXCLUDED.lines_deleted,
                            total_loc_changes = EXCLUDED.total_loc_changes,
                            last_commit_hash = EXCLUDED.last_commit_hash,
                            updated_at = NOW();
                    """
                    )
                    conn.execute(stmt, {
                        "member_key": data["member_key"],
                        "display_name": data["display_name"],
                        "canonical_email": data["canonical_email"],
                        "commit_count": data["commit_count"],
                        "lines_added": data["lines_added"],
                        "lines_deleted": data["lines_deleted"],
                        "total_loc_changes": total_loc,
                        "last_commit_hash": data["last_hash"],
                    })
        print(f"Successfully synced stats for {len(authors)} contributors to DB.")
    except Exception as err:
        print(f"Error syncing git stats to database: {err}")


if __name__ == "__main__":
    stats = parse_git_history(scope="main")
    sync_to_db(stats)
