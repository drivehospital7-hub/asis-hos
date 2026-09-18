"""Unit tests for the disk-backed procesar export cache (strict TDD).

Covers tasks 1.3 + 4.1: put/get roundtrip, expiry, caps/eviction,
traversal rejection and sweep of ``app.utils.procesar_export_store``.
"""

from __future__ import annotations

import json
import re
import time

import pytest

from app.utils import procesar_export_store as store


@pytest.fixture
def isolated_dir(tmp_path, monkeypatch):
    """Point the store at a hermetic tmp dir for the whole test."""
    monkeypatch.setattr(
        store, "temp_export_directory", lambda *, create=True: tmp_path
    )
    return tmp_path


def _rows(n: int = 3) -> list[dict]:
    return [{"factura": f"F-{i:03d}", "detalle": f"detalle-{i}"} for i in range(n)]


def _payload_path(isolated_dir, export_id: str):
    return isolated_dir / f"{export_id}.json"


class TestPutGetRoundtrip:
    def test_put_returns_opaque_id(self, isolated_dir):
        export_id = store.put(_rows(2))
        assert re.match(r"^[A-Za-z0-9_-]{16,64}$", export_id)

    def test_get_returns_same_rows(self, isolated_dir):
        rows = _rows(3)
        export_id = store.put(rows)
        assert store.get(export_id) == rows

    def test_empty_rows_roundtrip(self, isolated_dir):
        export_id = store.put([])
        assert store.get(export_id) == []

    def test_write_is_atomic_json(self, isolated_dir):
        export_id = store.put(_rows(1))
        payload = json.loads(_payload_path(isolated_dir, export_id).read_text())
        assert payload["id"] == export_id
        assert payload["rows"] == _rows(1)
        assert isinstance(payload["created"], (int, float))


class TestUnknownAndTraversal:
    def test_unknown_id_returns_none(self, isolated_dir):
        assert store.get("AAAAAAAAAAAAAAAAAAAAAA") is None

    def test_path_traversal_rejected(self, isolated_dir):
        assert store.get("../secret") is None
        assert store.get("..%2Fsecret") is None

    def test_malformed_ids_rejected(self, isolated_dir):
        assert store.get("") is None
        assert store.get("short") is None
        assert store.get("has space in it !!!!") is None

    def test_rejected_ids_do_not_touch_disk(self, isolated_dir):
        store.get("../secret")
        assert list(isolated_dir.iterdir()) == []


class TestExpiry:
    def _expire(self, isolated_dir, export_id: str) -> None:
        path = _payload_path(isolated_dir, export_id)
        payload = json.loads(path.read_text())
        payload["created"] = time.time() - store.PROCESAR_EXPORT_TTL_SECONDS - 1
        path.write_text(json.dumps(payload))

    def test_expired_returns_none(self, isolated_dir):
        export_id = store.put(_rows(2))
        self._expire(isolated_dir, export_id)
        assert store.get(export_id) is None

    def test_expired_file_is_removed(self, isolated_dir):
        export_id = store.put(_rows(2))
        self._expire(isolated_dir, export_id)
        store.get(export_id)
        assert not _payload_path(isolated_dir, export_id).exists()

    def test_unexpired_still_readable(self, isolated_dir):
        export_id = store.put(_rows(2))
        assert store.get(export_id) == _rows(2)


class TestCapsAndEviction:
    def test_oldest_first_eviction_over_max_entries(
        self, isolated_dir, monkeypatch
    ):
        monkeypatch.setattr(store, "PROCESAR_EXPORT_MAX_ENTRIES", 3)
        ids = [store.put([{"n": i}]) for i in range(4)]
        assert store.get(ids[0]) is None
        assert store.get(ids[3]) == [{"n": 3}]

    def test_sweep_removes_only_expired(self, isolated_dir):
        valid_id = store.put(_rows(1))
        expired_id = store.put(_rows(1))
        path = _payload_path(isolated_dir, expired_id)
        payload = json.loads(path.read_text())
        payload["created"] = time.time() - store.PROCESAR_EXPORT_TTL_SECONDS - 1
        path.write_text(json.dumps(payload))

        removed = store.sweep_expired()

        assert removed == 1
        assert not path.exists()
        assert store.get(valid_id) == _rows(1)

    def test_sweep_empty_dir_returns_zero(self, isolated_dir):
        assert store.sweep_expired() == 0
