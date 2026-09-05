"""Prod-checksum gate re-verification (Slice 3.2, strict TDD).

Re-runs ``scripts/prod_baseline.py`` dry-run: asserts pinned digests match
live files, rerun stability, prod-name guard, and zero prod connections.
Pure file reads — no DB access. Pinned record: ``prod_digests.json``.
"""
import inspect
import json
from pathlib import Path

from scripts.prod_baseline import (
    PROD_SUBSTRINGS,
    capture_baseline,
    is_prod_connection,
)

REPO = Path(__file__).resolve().parents[2]
PINNED = Path(__file__).with_name("prod_digests.json")
# AUTH=DB by design: instance/users.json is no longer a pinned prod ref
# (DB is the single source of truth for users). Only base.py is pinned.
REFS = [Path("app/constants/base.py")]


def _pinned() -> dict[str, str]:
    assert PINNED.exists(), "pinned digests missing — gate NOT green"
    return json.loads(PINNED.read_text(encoding="utf-8"))


def test_pinned_digests_match_live_files() -> None:
    pinned = _pinned()
    live = capture_baseline(REFS)
    assert set(live) == set(pinned)
    for key, digest in live.items():
        assert digest == pinned[key], f"digest drift (prod touched?): {key}"
    assert live["app/constants/base.py"].startswith("00c9f068")
    assert live["app/constants/base.py"].endswith("007bbe")


def test_baseline_rerun_is_stable() -> None:
    assert capture_baseline(REFS) == capture_baseline(REFS)


def test_guard_aborts_on_prod_names() -> None:
    assert len(PROD_SUBSTRINGS) >= 1
    for alias in ("control_system_prod", "asis_hos_prod", "prod", "PROD", "production"):
        assert is_prod_connection(alias) is True
    assert is_prod_connection("asis_hos") is False


def test_zero_prod_connections() -> None:
    import scripts.prod_baseline as baseline

    source = inspect.getsource(baseline)
    for token in ("psycopg", "connect(", "socket", "get_session", "create_engine"):
        assert token not in source, f"DB access token in dry-run module: {token}"
