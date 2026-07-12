"""Unit tests for RowStore — build_row_store() and row_from_dict()."""

from __future__ import annotations

import pytest


class TestBuildRowStore:
    """Tests for build_row_store() — converts 2D list to list[dict]."""

    def test_import_exists(self):
        from app.services.engine.row_store import build_row_store

        assert build_row_store is not None

    def test_builds_list_of_dicts_from_2d_list(self):
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],                                    # row 0 unused
            [None, "FAC-001", 15000.50, "ODONTOLOGIA"],  # row 1 (header)
            [None, "FAC-002", 22300.00, "URGENCIAS"],    # row 2 (data)
            [None, "FAC-003", 8750.25, None],             # row 3 (data)
        ]
        indices = {
            "numero_factura": 0,
            "vlr_procedimiento": 1,
            "convenio_facturado": 2,
        }

        result = build_row_store(rows_2d, indices)

        assert len(result) == 2
        assert result[0] == {
            "numero_factura": "FAC-002",
            "vlr_procedimiento": 22300.00,
            "convenio_facturado": "URGENCIAS",
        }
        assert result[1] == {
            "numero_factura": "FAC-003",
            "vlr_procedimiento": 8750.25,
            "convenio_facturado": None,
        }

    def test_keys_match_snake_case_column_names(self):
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],
            [None, "F001", "John", 30],
            [None, "F002", "Jane", 25],
            [None, "F003", "Bob", 40],
        ]
        indices = {
            "numero_factura": 0,
            "nombre_paciente": 1,
            "edad": 2,
        }

        result = build_row_store(rows_2d, indices)

        assert list(result[0].keys()) == ["numero_factura", "nombre_paciente", "edad"]
        assert list(result[1].keys()) == ["numero_factura", "nombre_paciente", "edad"]

    def test_skips_missing_index_columns(self):
        """Keys with None index are excluded from result dicts."""
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],
            [None, "F001", 100.0],
            [None, "F002", 200.0],
        ]
        indices = {
            "numero_factura": 0,
            "vlr_procedimiento": None,  # None → skip this key
        }

        result = build_row_store(rows_2d, indices)

        assert "numero_factura" in result[0]
        assert "vlr_procedimiento" not in result[0]
        assert len(result[0]) == 1

    def test_empty_data_rows_returns_empty_list(self):
        """Only header row, no data rows."""
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],  # row 0 unused
            [None, "FAC", "VALOR"],  # only header
        ]
        indices = {"numero_factura": 0, "vlr_procedimiento": 1}

        result = build_row_store(rows_2d, indices)

        assert result == []

    def test_none_values_in_data_become_none_in_dict(self):
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],
            [None, "header1", "header2"],
            [None, "F001", None],
            [None, None, 500.0],
        ]
        indices = {"numero_factura": 0, "vlr_procedimiento": 1}

        result = build_row_store(rows_2d, indices)

        assert result[0]["numero_factura"] == "F001"
        assert result[0]["vlr_procedimiento"] is None
        assert result[1]["numero_factura"] is None
        assert result[1]["vlr_procedimiento"] == 500.0

    def test_only_single_row_returns_one_dict(self):
        """Single data row should return a list with one dict."""
        from app.services.engine.row_store import build_row_store

        rows_2d = [
            [None],
            [None, "header"],
            [None, "F001"],
        ]
        indices = {"numero_factura": 0}

        result = build_row_store(rows_2d, indices)

        assert len(result) == 1
        assert result[0] == {"numero_factura": "F001"}


class TestRowFromDict:
    """Tests for row_from_dict() — identity function for dict rows.

    Exists for interface consistency so the engine can swap between
    build_row_store output and pre-existing dict rows transparently.
    """

    def test_import_exists(self):
        from app.services.engine.row_store import row_from_dict

        assert row_from_dict is not None

    def test_returns_same_dict(self):
        from app.services.engine.row_store import row_from_dict

        row = {"numero_factura": "F001", "vlr_procedimiento": 15000.0}
        indices = {"numero_factura": 0, "vlr_procedimiento": 1}

        result = row_from_dict(row, indices)

        assert result is row  # same object reference
        assert result == {"numero_factura": "F001", "vlr_procedimiento": 15000.0}

    def test_handles_empty_dict(self):
        from app.services.engine.row_store import row_from_dict

        result = row_from_dict({}, {})

        assert result == {}
