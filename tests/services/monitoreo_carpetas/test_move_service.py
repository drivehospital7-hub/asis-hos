"""RED tests for bulk move service (monitoreo-mover-facturas).

Strict TDD: these tests are written BEFORE move_service.py exists.
They MUST fail (collection/import error) until the GREEN phase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.constants.monitoreo_carpetas import MOVE_MAX_BATCH
from app.services.monitoreo_carpetas.move_service import (
    execute_move,
    validate_move_request,
)


def _make_tree(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    """Build src/ + dest/ dirs with 3 invoice folders under src."""
    src = tmp_path / "src"
    dest = tmp_path / "dest"
    (src / "FEV001").mkdir(parents=True)
    (src / "FEV001" / "dummy.txt").write_text("f1")
    (src / "FEV002").mkdir(parents=True)
    (src / "FEV002" / "dummy.txt").write_text("f2")
    (src / "FEV003").mkdir(parents=True)
    (src / "FEV003" / "dummy.txt").write_text("f3")
    dest.mkdir(parents=True)
    roots = [str(tmp_path)]
    sources = [str(src / "FEV001"), str(src / "FEV002"), str(src / "FEV003")]
    return src, dest, sources, roots


class TestValidateMoveRequest:
    def test_valid_request_returns_none(self, tmp_path: Path) -> None:
        src, dest, sources, roots = _make_tree(tmp_path)
        assert validate_move_request(sources, str(dest), roots) is None

    def test_traversal_dest_rejected(self, tmp_path: Path) -> None:
        _src, _dest, sources, roots = _make_tree(tmp_path)
        evil = str(tmp_path / ".." / "evil")
        err = validate_move_request(sources, evil, roots)
        assert err is not None

    def test_dest_outside_roots_allowed(self, tmp_path: Path) -> None:
        _src, _dest, sources, roots = _make_tree(tmp_path)
        outside = str(tmp_path / "elsewhere" / "dest")
        assert validate_move_request(sources, outside, roots) is None

    def test_dest_must_be_absolute(self, tmp_path: Path) -> None:
        _src, _dest, sources, roots = _make_tree(tmp_path)
        err = validate_move_request(sources, "relative/dest", roots)
        assert err is not None

    def test_over_limit_rejected(self, tmp_path: Path) -> None:
        _src, dest, _sources, roots = _make_tree(tmp_path)
        sources = [f"/fake/src{i}" for i in range(MOVE_MAX_BATCH + 1)]
        err = validate_move_request(sources, str(dest), roots)
        assert err is not None


class TestExecuteMove:
    def test_happy_path_moves_all(self, tmp_path: Path) -> None:
        from app.services.monitoreo_carpetas.watcher import FolderWatcher

        src, dest, sources, _roots = _make_tree(tmp_path)
        watcher = FolderWatcher()
        moved, failed = execute_move(sources, str(dest), watcher)
        assert len(moved) == 3
        assert failed == []
        for name in ("FEV001", "FEV002", "FEV003"):
            assert (dest / name).exists()
            assert not (src / name).exists()

    def test_partial_failure_reports_per_item(self, tmp_path: Path) -> None:
        from app.services.monitoreo_carpetas.watcher import FolderWatcher

        src, dest, sources, _roots = _make_tree(tmp_path)
        sources = sources + [str(src / "MISSING_NOPE")]
        watcher = FolderWatcher()
        moved, failed = execute_move(sources, str(dest), watcher)
        assert len(moved) == 3
        assert len(failed) == 1
        assert failed[0]["src"] == str(src / "MISSING_NOPE")
        assert failed[0]["error"]

    def test_collision_fails_without_rename(self, tmp_path: Path) -> None:
        from app.services.monitoreo_carpetas.watcher import FolderWatcher

        src, dest, sources, _roots = _make_tree(tmp_path)
        (dest / "FEV001").mkdir()  # pre-existing collision
        watcher = FolderWatcher()
        moved, failed = execute_move([sources[0]], str(dest), watcher)
        assert moved == []
        assert len(failed) == 1
        # source must NOT have been renamed/moved
        assert (src / "FEV001").exists()

    def test_resync_sequences_watcher_calls(self, tmp_path: Path, monkeypatch) -> None:
        from app.services.monitoreo_carpetas.watcher import FolderWatcher

        src, dest, sources, _roots = _make_tree(tmp_path)
        watcher = FolderWatcher()
        calls: list[tuple[str, str]] = []
        monkeypatch.setattr(
            watcher, "remove_subtree", lambda p: calls.append(("remove", p))
        )
        monkeypatch.setattr(
            watcher, "update_subtree", lambda p: calls.append(("update", p))
        )
        moved, failed = execute_move([sources[0]], str(dest), watcher)
        assert len(moved) == 1
        kinds = [k for k, _ in calls]
        assert "remove" in kinds
        assert "update" in kinds
