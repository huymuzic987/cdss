import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = "deploy/validate_env.sh"


def production_env(password: str = "safe-password", mode: str = "0600") -> str:
    return "\n".join(
        [
            "APP_ENV=production",
            "POSTGRES_USER=cdss",
            f"POSTGRES_PASSWORD={password}",
            "POSTGRES_DB=cdss",
            "APP_PORT=3000",
            "BACKUP_HOST_DIR=./persistent-backups",
            "BACKUP_RETENTION=10",
            f"BACKUP_FILE_MODE={mode}",
            "",
        ]
    )


def validate(env_file: Path) -> subprocess.CompletedProcess[str]:
    # Windows checkouts may use CRLF even though .gitattributes enforces LF in
    # committed shell scripts. Normalize a temporary copy so Git Bash matches
    # the Linux Jenkins host.
    deploy_dir = env_file.parent / "deploy"
    deploy_dir.mkdir(exist_ok=True)
    for script_name in ("lib.sh", "validate_env.sh"):
        source = (REPO_ROOT / "deploy" / script_name).read_text(encoding="utf-8")
        (deploy_dir / script_name).write_text(
            source,
            encoding="utf-8",
            newline="\n",
        )
    return subprocess.run(
        ["bash", "deploy/validate_env.sh", env_file.name],
        cwd=env_file.parent,
        check=False,
        capture_output=True,
        text=True,
    )


def test_valid_production_environment_passes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(production_env(), encoding="utf-8")

    result = validate(env_file)

    assert result.returncode == 0, result.stderr
    assert "validated" in result.stdout


def test_environment_values_are_not_executed(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    env_file = tmp_path / ".env"
    env_file.write_text(
        production_env(password=f"$(touch {marker.as_posix()})"),
        encoding="utf-8",
    )

    result = validate(env_file)

    assert result.returncode == 0, result.stderr
    assert not marker.exists()


def test_duplicate_keys_fail_closed(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        production_env() + "POSTGRES_USER=duplicate\n",
        encoding="utf-8",
    )

    result = validate(env_file)

    assert result.returncode != 0
    assert "duplicate dotenv key" in result.stderr


def test_placeholder_password_and_insecure_backup_mode_are_rejected(tmp_path: Path) -> None:
    placeholder_file = tmp_path / "placeholder.env"
    placeholder_file.write_text(production_env(password="change-me"), encoding="utf-8")
    insecure_mode_file = tmp_path / "mode.env"
    insecure_mode_file.write_text(production_env(mode="0644"), encoding="utf-8")

    placeholder_result = validate(placeholder_file)
    insecure_mode_result = validate(insecure_mode_file)

    assert placeholder_result.returncode != 0
    assert insecure_mode_result.returncode != 0
    assert "placeholder POSTGRES_PASSWORD" in placeholder_result.stderr
    assert "BACKUP_FILE_MODE must be 0600" in insecure_mode_result.stderr


def test_deployment_scripts_do_not_source_dotenv_as_shell() -> None:
    offenders = []
    for script in (REPO_ROOT / "deploy").glob("*.sh"):
        if "source .env" in script.read_text(encoding="utf-8"):
            offenders.append(script.name)

    assert offenders == []


def test_backup_defaults_are_owner_only() -> None:
    backup_script = (REPO_ROOT / "deploy" / "backup_db.sh").read_text(encoding="utf-8")
    compose_file = (REPO_ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "BACKUP_FILE_MODE:-0600" in backup_script
    assert 'chmod 0700 "$BACKUP_DIR"' in backup_script
    assert "BACKUP_FILE_MODE:-0600" in compose_file
