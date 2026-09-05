"""Prod immutability baseline tests (Slice 0, strict TDD).

No prod connection is opened here. Baseline is file checksums only
(dry-run mechanism). Real DB guard lands in Slice 1 runner hardening.
"""
from pathlib import Path

from scripts.prod_baseline import (
    PROD_SUBSTRINGS,
    capture_baseline,
    is_prod_connection,
    sha256_file,
)


def test_prod_guard_aborts_on_control_system_prod() -> None:
    assert is_prod_connection("control_system_prod") is True


def test_prod_guard_allows_dev_database() -> None:
    assert is_prod_connection("asis_hos") is False


def test_prod_guard_is_case_insensitive() -> None:
    assert is_prod_connection("ASIS_HOS_PROD") is True
    assert is_prod_connection("Production") is True


def test_prod_substring_list_covers_aliases() -> None:
    aliases = ["control_system_prod", "asis_hos_prod", "prod", "PROD", "production"]
    assert len(PROD_SUBSTRINGS) >= 1
    for alias in aliases:
        assert is_prod_connection(alias) is True


def test_sha256_is_stable_and_content_sensitive(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("baseline-v1", encoding="utf-8")
    first = sha256_file(target)
    assert sha256_file(target) == first
    target.write_text("baseline-v2", encoding="utf-8")
    assert sha256_file(target) != first


def test_baseline_capture_is_byte_identical_on_rerun() -> None:
    # AUTH=DB by design: users.json is not a pinned prod ref (DB is source
    # of truth). Only base.py is pinned; see tests/bre/prod_digests.json.
    refs = [
        Path("app/constants/base.py"),
    ]
    first = capture_baseline(refs)
    second = capture_baseline(refs)
    assert first == second
    assert set(first) == {"app/constants/base.py"}
    assert all(len(digest) == 64 for digest in first.values())
