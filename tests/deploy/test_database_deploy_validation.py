import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def normalized_script(tmp_path: Path, name: str) -> Path:
    source = (REPO_ROOT / "deploy" / name).read_text(encoding="utf-8")
    target = tmp_path / name
    target.write_text(source, encoding="utf-8", newline="\n")
    return target


def sample_seed(layout_markers: bool = True) -> str:
    lines = ["BEGIN;", "-- ordinary seed row"]
    if layout_markers:
        lines.extend(
            [
                "-- 5. TREE LAYOUTS (1 layout)",
                "SELECT 'layout-payload';",
                "-- 6. MEDICINES REFERENCE CATALOG (1 drug)",
            ]
        )
    lines.extend(
        [
            "SELECT 'medicine-payload';",
            "UPDATE public.tree_layouts SET node_positions = '{}'::jsonb;",
            "COMMIT;",
            "",
        ]
    )
    return "\n".join(lines)


def test_preserve_layout_seed_filter_is_fail_closed(tmp_path: Path) -> None:
    script = normalized_script(tmp_path, "seed_database.sh")
    valid_seed = tmp_path / "valid.sql"
    valid_seed.write_text(sample_seed(), encoding="utf-8", newline="\n")
    missing_markers = tmp_path / "missing.sql"
    missing_markers.write_text(
        sample_seed(layout_markers=False),
        encoding="utf-8",
        newline="\n",
    )

    valid = subprocess.run(
        ["bash", script.name, "preserve-layouts", valid_seed.name],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    invalid = subprocess.run(
        ["bash", script.name, "preserve-layouts", missing_markers.name],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert valid.returncode == 0, valid.stderr
    assert "layout-payload" not in valid.stdout
    assert "medicine-payload" in valid.stdout
    assert "UPDATE public.tree_layouts SET node_positions" in valid.stdout
    assert (
        "CREATE TEMP TABLE cdss_preserved_tree_layouts ON COMMIT DROP AS TABLE public.tree_layouts;"
    ) in valid.stdout
    assert "DELETE FROM public.tree_layouts;" in valid.stdout
    assert (
        "INSERT INTO public.tree_layouts SELECT * FROM cdss_preserved_tree_layouts;"
    ) in valid.stdout
    assert valid.stdout.index("BEGIN;") < valid.stdout.index(
        "CREATE TEMP TABLE cdss_preserved_tree_layouts"
    )
    assert valid.stdout.index("INSERT INTO public.tree_layouts SELECT *") < (
        valid.stdout.index("COMMIT;")
    )
    assert valid.stdout.index("UPDATE public.tree_layouts SET node_positions") < (
        valid.stdout.index("INSERT INTO public.tree_layouts SELECT *")
    )
    assert invalid.returncode != 0
    assert "markers" in invalid.stderr


def test_candidate_validator_emits_bounded_fail_closed_sql(tmp_path: Path) -> None:
    script = normalized_script(tmp_path, "validate_candidate_db.sh")

    result = subprocess.run(
        [
            "bash",
            script.name,
            "9f7c2d4a1b6e",
            "preserve-layouts",
            "3:d41d8cd98f00b204e9800998ecf8427e",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "statement_timeout = '30s'" in result.stdout
    assert "lock_timeout = '5s'" in result.stdout
    assert "candidate seed row counts" in result.stdout
    assert "unresolved LINK" in result.stdout
    assert "tree layouts changed" in result.stdout


def test_candidate_validator_uses_materialized_seed_counts(tmp_path: Path) -> None:
    script = normalized_script(tmp_path, "validate_candidate_db.sh")

    result = subprocess.run(
        ["bash", script.name, "9f7c2d4a1b6e", "all"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "actual_node_count < 383" in result.stdout
    assert "actual_edge_count < 426" in result.stdout
    assert "actual_medicine_count < 66" in result.stdout


def test_database_validation_precedes_candidate_service_start() -> None:
    provision = (REPO_ROOT / "deploy" / "provision_stack.sh").read_text(encoding="utf-8")

    migration = provision.index('run_timed "candidate-alembic-migration"')
    seed = provision.index('run_timed "candidate-database-seed"')
    validation = provision.index('run_timed "candidate-database-validation"')
    services = provision.index('run_timed "candidate-services-start"')

    assert migration < seed < validation < services


def test_candidate_database_readiness_is_frequent_but_bounded() -> None:
    provision = (REPO_ROOT / "deploy" / "provision_stack.sh").read_text(encoding="utf-8")
    readiness_start = provision.index('echo "Waiting for database to be ready..."')
    readiness_end = provision.index('if [ "$db_ready" != "true" ]', readiness_start)
    readiness_block = provision[readiness_start:readiness_end]

    assert "for i in $(seq 1 120); do" in readiness_block
    assert "sleep 1" in readiness_block
    assert "sleep 5" not in readiness_block
    assert "db_ready_deadline=$((db_ready_started_at + 120))" in readiness_block
    assert 'if [ "$(date +%s)" -ge "$db_ready_deadline" ]; then' in readiness_block

    probe_start = readiness_block.index("pg_isready")
    probe_end = readiness_block.index("\n", probe_start)
    assert "--timeout=1" in readiness_block[probe_start:probe_end]
