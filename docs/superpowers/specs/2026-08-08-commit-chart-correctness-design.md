# Commit Chart Correctness Design

## Objective

Make the contribution dashboard's Commit Type Breakdown and Commit Activity
Velocity charts represent the complete non-merge Git history reachable from
`main`. The charts must use the same source of truth as the contributor totals
and must never fabricate missing commit data.

## Scope

- Keep the existing `GET /dashboard/contributions` endpoint and scope switch.
- Add a canonical `commit_history` response field containing every commit in
  the selected scope. The requested production behavior is the complete
  non-merge history of `main`.
- Replace the hard-coded recent-commit examples with the actual five newest
  commits from that history.
- Preserve the existing contributor cards, contribution matrix, and chart
  layout.

Merge commits remain excluded because contributor totals already use
`git log --no-merges`; the history and aggregates must use the same rule.

## Data flow

The contribution endpoint will parse Git history once for the requested scope.
Each commit record will contain:

- short hash;
- primary author display name;
- commit subject/message;
- Unix commit timestamp;
- canonical contributor keys for the primary author and any distinct
  `Co-authored-by` authors.

Contributor aggregates and commit history will be derived from this same parse.
The persisted `git_contributions` table may be used only when Git history is
unavailable, so stale database aggregates cannot be paired with a different
commit stream. Existing canonical-member zero rows remain in the response.

The API will return all history in `commit_history` and the newest five actual
records in `recent_commits`. The recent-commit feed continues to consume the
small recent list; both charts consume `commit_history`.

## Chart behavior

### Commit Type Breakdown

For each contributor, count history records whose canonical contributor key
contains that member. Classify the commit subject as:

- `Feature`: `feat` or `feature` prefixes;
- `Fix`: `fix` or `bugfix` prefixes;
- `Refactor`: `refactor` prefix;
- `Maintenance`: every other subject, including chore, CI, build, docs, test,
  performance, style, revert, and unrecognised messages.

Prefix matching accepts the conventional `type:`, `type(scope):`, and the
repository's bracketed `[Fix]` form. Category totals for a contributor must
equal that contributor's real commit count, including co-authored commits.
The fabricated 45/25/20 fallback and the misleading `DevOps` series are
removed.

### Commit Activity Velocity

Sort the complete history by timestamp and group unique commits by UTC calendar
date. Daily mode displays the exact count for each date represented in the
history. Cumulative mode starts at zero and adds each daily count, so its final
point equals the number of unique commits in `commit_history`. It must not use
the contributor-total minus recent-sample baseline.

## Compatibility and error handling

The existing endpoint shape remains compatible apart from the added
`commit_history` field and corrected actual `recent_commits` values. If Git
history parsing returns no records, the endpoint preserves the existing
database fallback for contributor aggregates and returns empty history rather
than inventing chart values. Empty history renders empty charts without
errors.

## Testing

- Backend parser/API tests verify that `main` history includes real commit
  metadata, that recent commits are derived from the newest records, and that
  aggregate totals and history share the same scope.
- Frontend chart-data tests verify canonical-key matching, all four type
  classifications, no synthetic fallback, chronological daily counts, and
  cumulative totals starting at zero.
- Existing backend and frontend quality gates must remain green.

