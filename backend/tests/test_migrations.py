
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _module_available("alembic"), reason="alembic not installed in this environment"
)


def _run_alembic(args: list[str], db_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_alembic_upgrade_head_creates_every_model_table(tmp_path):
    db_path = tmp_path / "migration_test.db"

    result = _run_alembic(["upgrade", "head"], db_path)
    assert result.returncode == 0, result.stderr

    import sqlite3

    con = sqlite3.connect(db_path)
    try:
        tables = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        con.close()

    for expected in ("users", "messages", "workflow_runs", "workflow_step_records", "alembic_version"):
        assert expected in tables, f"migration did not create table '{expected}'"


def test_alembic_autogenerate_reports_no_further_changes(tmp_path):
    """If this fails, a model was changed without a matching migration —
    the whole point of this test.
    """
    db_path = tmp_path / "drift_check.db"
    _run_alembic(["upgrade", "head"], db_path)

    result = _run_alembic(
        ["revision", "--autogenerate", "-m", "drift_check_should_be_empty"], db_path
    )
    assert result.returncode == 0, result.stderr

    versions_dir = BACKEND_ROOT / "alembic" / "versions"
    generated = sorted(
        versions_dir.glob("*_drift_check_should_be_empty.py"),
        key=lambda p: p.stat().st_mtime,
    )
    assert generated, "expected alembic to generate a (hopefully empty) revision file"
    new_revision_file = generated[-1]

    try:
        content = new_revision_file.read_text()
        # An in-sync schema produces "pass" bodies for both upgrade/downgrade —
        # any real op.* call here means the migration is missing something.
        assert "op." not in content.split("def upgrade")[1].split("def downgrade")[0]
    finally:
        new_revision_file.unlink()
        pycache = versions_dir / "__pycache__"
        if pycache.exists():
            for f in pycache.glob("*drift_check_should_be_empty*"):
                f.unlink()


def test_alembic_downgrade_base_removes_every_table(tmp_path):
    db_path = tmp_path / "downgrade_test.db"
    _run_alembic(["upgrade", "head"], db_path)

    result = _run_alembic(["downgrade", "base"], db_path)
    assert result.returncode == 0, result.stderr

    import sqlite3

    con = sqlite3.connect(db_path)
    try:
        tables = {
            row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        con.close()

    assert tables == {"alembic_version"}