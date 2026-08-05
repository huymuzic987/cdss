# CDSS repository instructions

Read this file before changing repository files. These checks are part of the
Jenkins quality gate and must remain passing before a commit or pull request.

## Python formatting and checks

- Format changed Python files with `uv run ruff format <files>`.
- Verify formatting with `uv run ruff format --check`.
- Run `uv run ruff check` after Python changes.
- Run `uv run pyright` and the relevant `uv run pytest` tests when the change
  affects Python behavior.

Do not hand-format Python as a substitute for Ruff. If the quality gate lists
files as reformatted, run Ruff on those files and review the resulting diff.

## Frontend checks

From `frontend/`, run the relevant Vitest tests, `pnpm exec oxlint`,
`pnpm exec tsc --noEmit`, and `pnpm run build` when frontend code changes.
The CI image uses Node 24 and pnpm 9.15.9.

## Before handoff

Run `git diff --check`, inspect the complete diff, and run
`deploy/run_quality_gates.sh` when Docker is available. Do not leave generated
artifacts or unrelated formatter changes in the pull request.
