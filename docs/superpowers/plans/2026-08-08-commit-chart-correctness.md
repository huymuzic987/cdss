# Commit Chart Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make both contribution charts use every real non-merge commit reachable from `main`, with no hard-coded samples or fabricated chart values.

**Architecture:** Parse Git once into a typed snapshot containing contributor aggregates and canonical commit records. Expose the complete history through the existing contributions API, then use pure TypeScript transformations to derive the type-breakdown and daily/cumulative velocity series.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, pytest, React 19, TypeScript 6, Recharts 3, Vitest 4.

## Global Constraints

- The production chart source is the complete non-merge history reachable from `main`.
- Contributor aggregates and commit history must come from the same Git parse.
- The database is an aggregate fallback only when Git history cannot be read.
- `recent_commits` contains the actual newest five commits; `commit_history` contains all commits.
- Commit types are Feature, Fix, Refactor, and Maintenance; unknown subjects are Maintenance.
- Velocity groups unique commits by UTC calendar date and cumulative totals start at zero.
- No fabricated chart data is allowed when history is empty.

---

### Task 1: Parse a canonical Git history snapshot

**Files:**
- Create: `tests/infrastructure/test_git_contributions.py`
- Modify: `src/cdss/infrastructure/git_contributions.py`

**Interfaces:**
- Produces: `CommitRecord(hash, author, message, timestamp, member_keys)`.
- Produces: `GitHistorySnapshot(contributors, commits)`.
- Produces: `parse_git_history_snapshot(scope: str = "main") -> GitHistorySnapshot`.
- Preserves: `parse_git_history(scope: str = "main") -> dict[str, dict[str, Any]]` for the database sync script.

- [ ] **Step 1: Write the failing parser test**

Add a subprocess fixture representing two real Git records, including a `Co-authored-by` trailer and numstat data. The production mutation caught by this test is returning aggregates without canonical per-commit metadata.

```python
from cdss.infrastructure.git_contributions import parse_git_history_snapshot


RAW_LOG = """\x1eabc1234\x1fHuy\x1fhuymusic987@gmail.com\x1f1782691200\x1ffeat: add chart history\n\nCo-authored-by: Quang Minh <phamlequangminh2411@gmail.com>\n\x1f\n10\t2\tfrontend/chart.tsx\n\x1edef5678\x1fHuy\x1fhuymusic987@gmail.com\x1f1782777600\x1ffix: correct velocity\n\x1f\n4\t1\tfrontend/velocity.tsx\n"""


def test_parse_git_history_snapshot_keeps_real_commits_and_canonical_authors(monkeypatch):
    monkeypatch.setattr(
        "cdss.infrastructure.git_contributions.subprocess.check_output",
        lambda *args, **kwargs: RAW_LOG,
    )
    monkeypatch.setattr(
        "cdss.infrastructure.git_contributions.subprocess.call",
        lambda *args, **kwargs: 0,
    )

    snapshot = parse_git_history_snapshot("main")

    assert [commit.hash for commit in snapshot.commits] == ["abc1234", "def5678"]
    assert snapshot.commits[0].message == "feat: add chart history"
    assert snapshot.commits[0].member_keys == ("huy", "quang_minh")
    assert snapshot.contributors["huy"]["commit_count"] == 2
    assert snapshot.contributors["quang_minh"]["commit_count"] == 1
    assert snapshot.contributors["huy"]["lines_added"] == 9
    assert snapshot.contributors["quang_minh"]["lines_added"] == 5
```

- [ ] **Step 2: Run the parser test and verify RED**

Run: `uv run pytest tests/infrastructure/test_git_contributions.py -q`

Expected: FAIL because `parse_git_history_snapshot` and the snapshot types do not exist.

- [ ] **Step 3: Implement the typed snapshot parser**

In `git_contributions.py`, add frozen dataclasses and use record/unit separators so commit bodies cannot collide with field delimiters:

```python
@dataclass(frozen=True)
class CommitRecord:
    hash: str
    author: str
    message: str
    timestamp: int
    member_keys: tuple[str, ...]


@dataclass(frozen=True)
class GitHistorySnapshot:
    contributors: dict[str, dict[str, Any]]
    commits: tuple[CommitRecord, ...]
```

Build the log with:

```python
"--pretty=format:%x1e%h%x1f%an%x1f%ae%x1f%at%x1f%B%x1f"
```

Split records on `\x1e`, split each record on `\x1f` with `maxsplit=5`, canonicalize the primary author and distinct co-authors, append one `CommitRecord`, and apply numstat totals to every canonical author using the existing equal line-weight rule. Keep Git's newest-first order. Return `GitHistorySnapshot({}, ())` on command failure.

Implement the compatibility wrapper exactly as:

```python
def parse_git_history(scope: str = "main") -> dict[str, dict[str, Any]]:
    return parse_git_history_snapshot(scope).contributors
```

- [ ] **Step 4: Run parser tests and verify GREEN**

Run: `uv run pytest tests/infrastructure/test_git_contributions.py -q`

Expected: PASS.

- [ ] **Step 5: Verify the database sync compatibility**

Run: `uv run python scripts/update_contributions_db.py --scope main --print-sql`

Expected: exit 0 and generated SQL for real contributors.

- [ ] **Step 6: Commit the parser unit**

```bash
git add tests/infrastructure/test_git_contributions.py src/cdss/infrastructure/git_contributions.py
git commit -m "fix: parse canonical commit history"
```

---

### Task 2: Expose complete history from the contributions API

**Files:**
- Modify: `tests/api/test_dashboard_contributions.py`
- Modify: `src/cdss/api/schemas/dashboard.py`
- Modify: `src/cdss/api/routes/dashboard_contributions.py`

**Interfaces:**
- Consumes: `parse_git_history_snapshot(scope) -> GitHistorySnapshot` from Task 1.
- Produces: `CommitHistoryItem` with `hash`, `author`, `message`, `timestamp`, and `member_keys`.
- Produces: `ContributionsResponse.commit_history: list[CommitHistoryItem]`.
- Preserves: `ContributionsResponse.recent_commits: list[RecentCommitItem]` as the newest five real commits.

- [ ] **Step 1: Write the failing endpoint contract test**

Monkeypatch `parse_git_history_snapshot` with a literal six-commit snapshot and call `get_contributions` using a database double that fails if queried. The production mutations caught are querying stale aggregates before Git and returning hard-coded recent records.

```python
def test_contributions_uses_one_git_snapshot_for_totals_history_and_recent(monkeypatch):
    commits = tuple(
        CommitRecord(
            hash=f"hash{i}",
            author="Huy",
            message=f"fix: commit {i}",
            timestamp=100 - i,
            member_keys=("huy",),
        )
        for i in range(6)
    )
    snapshot = GitHistorySnapshot(
        contributors={
            "huy": {
                "member_key": "huy",
                "display_name": "Huy",
                "canonical_email": "huymuzic987",
                "commit_count": 6,
                "lines_added": 12,
                "lines_deleted": 3,
                "last_hash": "hash0",
            }
        },
        commits=commits,
    )
    monkeypatch.setattr(
        "cdss.api.routes.dashboard_contributions.parse_git_history_snapshot",
        lambda scope: snapshot,
    )

    response = get_contributions(db=DatabaseMustNotBeQueried(), scope="main")

    assert response.summary.total_commits == 6
    assert [item.hash for item in response.commit_history] == [f"hash{i}" for i in range(6)]
    assert [item.hash for item in response.recent_commits] == [f"hash{i}" for i in range(5)]
    assert response.commit_history[0].member_keys == ["huy"]
```

Define `DatabaseMustNotBeQueried.execute()` in the test to raise `AssertionError`.

- [ ] **Step 2: Run the endpoint test and verify RED**

Run: `uv run pytest tests/api/test_dashboard_contributions.py::test_contributions_uses_one_git_snapshot_for_totals_history_and_recent -q`

Expected: FAIL because the API still imports aggregate-only parsing and has no `commit_history` field.

- [ ] **Step 3: Add the response schema**

```python
class CommitHistoryItem(RecentCommitItem):
    member_keys: list[str]


class ContributionsResponse(ApiModel):
    # existing fields
    recent_commits: list[RecentCommitItem]
    commit_history: list[CommitHistoryItem]
```

- [ ] **Step 4: Build the endpoint from one snapshot**

Parse Git before consulting the database. If snapshot contributors are present, normalize them into `raw_stats`; otherwise execute the existing database query. Convert every snapshot commit to `CommitHistoryItem`, preserve newest-first order, and derive `recent_commits` from `commit_history[:5]`.

Use separate values for the actual total and percentage denominator:

```python
total_commits = sum(item["commit_count"] for item in raw_stats.values())
commit_denominator = total_commits or 1
```

Return the actual `total_commits`, and use only `commit_denominator` for percentages.

- [ ] **Step 5: Run endpoint tests and verify GREEN**

Run: `uv run pytest tests/api/test_dashboard_contributions.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the API unit**

```bash
git add tests/api/test_dashboard_contributions.py src/cdss/api/schemas/dashboard.py src/cdss/api/routes/dashboard_contributions.py
git commit -m "fix: expose complete main commit history"
```

---

### Task 3: Derive truthful chart series from commit history

**Files:**
- Create: `frontend/src/dashboard/sections/contribution/commitChartData.ts`
- Create: `frontend/src/dashboard/sections/contribution/commitChartData.test.ts`
- Modify: `frontend/src/api/types/contribution.ts`
- Modify: `frontend/src/dashboard/sections/contribution/CommitTypeBreakdownChart.tsx`
- Modify: `frontend/src/dashboard/sections/contribution/CommitVelocityChart.tsx`
- Modify: `frontend/src/dashboard/sections/contribution/ContributionCharts.tsx`
- Modify: `frontend/src/dashboard/sections/ContributionSection.tsx`
- Modify: `frontend/src/dashboard/sections/ContributionSection.test.tsx`

**Interfaces:**
- Consumes: `ContributionResponse.commit_history` from Task 2.
- Produces: `classifyCommitType(message: string): CommitType`.
- Produces: `buildCommitTypeData(contributors, commits): CommitTypeDatum[]`.
- Produces: `buildCommitVelocityData(commits): CommitVelocityDatum[]`.

- [ ] **Step 1: Add the frontend API type and failing pure-data tests**

Add:

```typescript
export interface CommitHistoryItem extends RecentCommitItem {
  member_keys: string[]
}

export interface ContributionResponse {
  // existing fields
  recent_commits: RecentCommitItem[]
  commit_history: CommitHistoryItem[]
}
```

Write table-driven classification and literal chart expectations. The production mutations caught are substring author matching, fabricated percentages, date-label collisions, and non-zero cumulative baselines.

```typescript
expect([
  classifyCommitType('feat(ui): add chart'),
  classifyCommitType('[Fix]: repair chart'),
  classifyCommitType('bugfix: repair parser'),
  classifyCommitType('refactor: split helper'),
  classifyCommitType('docs: explain chart'),
]).toEqual(['Feature', 'Fix', 'Fix', 'Refactor', 'Maintenance'])
```

Use a Huy contributor, a Quang Minh contributor, and an unmatched contributor. Supply four history records where one Fix has both canonical keys. Assert Huy receives one count in every category, Quang Minh receives one Fix, and the unmatched contributor receives four zeroes.

For velocity, supply three unsorted records on two UTC dates and assert exactly:

```typescript
[
  { date: 'Jun 28, 2026', commits: 2, cumulative: 2 },
  { date: 'Jun 29, 2026', commits: 1, cumulative: 3 },
]
```

- [ ] **Step 2: Run frontend data tests and verify RED**

Run: `pnpm --dir frontend test -- commitChartData.test.ts`

Expected: FAIL because the chart-data module does not exist.

- [ ] **Step 3: Implement the pure chart transformations**

In `commitChartData.ts`, use an anchored, case-insensitive prefix expression accepting `type:`, `type(scope):`, `[type]:`, whitespace, or end-of-string. Map `feat`/`feature`, `fix`/`bugfix`, and `refactor`; return Maintenance otherwise.

`buildCommitTypeData` must initialize all four categories to zero and increment only when `commit.member_keys.includes(contributor.member_key)`.

`buildCommitVelocityData` must:

```typescript
const dateKey = new Date(commit.timestamp * 1000).toISOString().slice(0, 10)
```

Group by `dateKey`, sort keys lexically, format labels with `Intl.DateTimeFormat` using `timeZone: 'UTC'`, and accumulate from zero.

- [ ] **Step 4: Run frontend data tests and verify GREEN**

Run: `pnpm --dir frontend test -- commitChartData.test.ts`

Expected: PASS.

- [ ] **Step 5: Wire both charts to the canonical history**

- `CommitTypeBreakdownChart` accepts `commitHistory`, calls `buildCommitTypeData`, removes all local filtering/fallback math, and renames the `DevOps` bar to `Maintenance`.
- `CommitVelocityChart` accepts only `commitHistory`, calls `buildCommitVelocityData`, and removes contributor totals and baseline logic.
- `ContributionCharts` accepts and forwards `commitHistory`.
- `ContributionSection` passes `data.commit_history` to `ContributionCharts` while continuing to pass `data.recent_commits` to `RecentCommitsFeed`.
- Add a complete `commit_history` entry to the existing contribution-section test fixture.

- [ ] **Step 6: Run focused frontend tests and build**

Run: `pnpm --dir frontend test -- commitChartData.test.ts ContributionSection.test.tsx`

Expected: PASS.

Run: `pnpm --dir frontend build`

Expected: exit 0.

- [ ] **Step 7: Commit the frontend unit**

```bash
git add frontend/src/api/types/contribution.ts frontend/src/dashboard/sections/ContributionSection.tsx frontend/src/dashboard/sections/ContributionSection.test.tsx frontend/src/dashboard/sections/contribution/CommitTypeBreakdownChart.tsx frontend/src/dashboard/sections/contribution/CommitVelocityChart.tsx frontend/src/dashboard/sections/contribution/ContributionCharts.tsx frontend/src/dashboard/sections/contribution/commitChartData.ts frontend/src/dashboard/sections/contribution/commitChartData.test.ts
git commit -m "fix(frontend): derive contribution charts from history"
```

---

### Task 4: Full verification

**Files:**
- Verify only; no planned production edits.

**Interfaces:**
- Consumes the complete backend and frontend behavior from Tasks 1–3.
- Produces fresh evidence that the corrected charts and existing quality gates pass.

- [ ] **Step 1: Run backend verification**

Run: `uv run pytest tests/infrastructure/test_git_contributions.py tests/api/test_dashboard_contributions.py -q`

Expected: PASS with zero failures.

Run: `uv run ruff check src/cdss/infrastructure/git_contributions.py src/cdss/api/routes/dashboard_contributions.py src/cdss/api/schemas/dashboard.py tests/infrastructure/test_git_contributions.py tests/api/test_dashboard_contributions.py`

Expected: exit 0.

Run: `uv run pyright src/cdss/infrastructure/git_contributions.py src/cdss/api/routes/dashboard_contributions.py`

Expected: zero errors.

- [ ] **Step 2: Run frontend verification**

Run: `pnpm --dir frontend test -- commitChartData.test.ts ContributionSection.test.tsx`

Expected: PASS with zero failures.

Run: `pnpm --dir frontend lint`

Expected: exit 0.

Run: `pnpm --dir frontend build`

Expected: exit 0.

- [ ] **Step 3: Inspect final scope**

Run: `git diff --check`

Expected: no output.

Run: `git status --short`

Expected: only the implementation-plan document is uncommitted, or no output if it was committed before execution.

