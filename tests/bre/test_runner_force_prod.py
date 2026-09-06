"""Runner --force-prod override tests.

Owner chose flag design (not env var, not manual psql).

Contract:
- --force-prod bypasses the is_prod_database abort ONLY combined with
  --apply --confirm (all three required).
- Without the trio, prod still aborts.
- Bypass logs a loud [BACK][ERROR] warning including the DB name.
- No real DB: all connections mocked. Only asis_hos_test/scratch names used
  for non-prod; prod names are synthetic guard inputs, never connected.
"""
import logging

from app.utils.db_config import DatabaseConfig

PROD_NAME = "asis_hos_prod_guardcheck"


def _prod_config() -> DatabaseConfig:
    return DatabaseConfig(
        host="localhost", port=5433, name=PROD_NAME, user="postgres", password=""
    )


def _test_config() -> DatabaseConfig:
    return DatabaseConfig(
        host="localhost", port=5433, name="asis_hos_test", user="postgres", password=""
    )


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, sql, params=None):
        self.executed.append(str(sql))

    def fetchall(self):
        return []

    def close(self):
        pass


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.autocommit = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def close(self):
        self.closed = True


def _patch_prod(monkeypatch, tmp_path, sql_text="SELECT 1;"):
    """Patch config to prod + isolated migrations dir + mocked connect."""
    import run_migrations

    (tmp_path / "001_sample.sql").write_text(sql_text, encoding="utf-8")
    monkeypatch.setattr(
        run_migrations, "get_database_config", lambda: _prod_config()
    )
    fake = _FakeConn()
    calls: list[dict] = []

    def _fake_connect(**kwargs):
        calls.append(kwargs)
        return fake

    monkeypatch.setattr(run_migrations.psycopg2, "connect", _fake_connect)
    return run_migrations, fake, calls, tmp_path


def test_prod_gate_aborts_without_flag(monkeypatch, tmp_path) -> None:
    run_migrations, _fake, calls, _dir = _patch_prod(monkeypatch, tmp_path)

    rc = run_migrations.run_migrations(
        ["--migrations-dir", str(tmp_path)]
    )
    assert rc == 1
    assert calls == []


def test_prod_gate_aborts_without_full_trio(monkeypatch, tmp_path) -> None:
    import run_migrations as rm

    partial_argvs = [
        ["--force-prod"],
        ["--apply"],
        ["--confirm"],
        ["--apply", "--confirm"],
        ["--apply", "--force-prod"],
        ["--confirm", "--force-prod"],
    ]
    for extra in partial_argvs:
        run_migrations, _fake, calls, _dir = _patch_prod(monkeypatch, tmp_path)
        argv = [*extra, "--migrations-dir", str(tmp_path)]
        rc = rm.run_migrations(argv)
        assert rc == 1, f"prod must still abort with flags {extra}"
        assert calls == [], f"prod must not connect with flags {extra}"


def test_prod_gate_proceeds_with_full_trio_mocked(caplog, monkeypatch, tmp_path) -> None:
    run_migrations, fake, calls, _dir = _patch_prod(monkeypatch, tmp_path)

    with caplog.at_level(logging.WARNING, logger="run_migrations"):
        rc = run_migrations.run_migrations(
            ["--apply", "--confirm", "--force-prod",
             "--migrations-dir", str(tmp_path)]
        )
    assert rc == 0
    assert len(calls) == 1  # guard passed, mocked apply proceeded
    assert fake.closed is True
    loud = [r for r in caplog.records if "[BACK][ERROR]" in r.getMessage()]
    assert loud, "bypass must log a loud [BACK][ERROR] warning"
    assert any(PROD_NAME in r.getMessage() for r in loud), (
        "bypass warning must include the DB name"
    )


def test_nonprod_unaffected(monkeypatch, tmp_path) -> None:
    import run_migrations

    (tmp_path / "001_sample.sql").write_text("SELECT 1;", encoding="utf-8")
    monkeypatch.setattr(
        run_migrations, "get_database_config", lambda: _test_config()
    )

    def _forbidden_connect(*args, **kwargs):  # pragma: no cover
        raise AssertionError("dry-run must not connect")

    monkeypatch.setattr(run_migrations.psycopg2, "connect", _forbidden_connect)

    rc_plain = run_migrations.run_migrations(["--migrations-dir", str(tmp_path)])
    assert rc_plain == 0

    rc_apply_no_confirm = run_migrations.run_migrations(
        ["--apply", "--migrations-dir", str(tmp_path)]
    )
    assert rc_apply_no_confirm == 1
