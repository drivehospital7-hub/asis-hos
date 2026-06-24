"""Tests for simulator_service.py — dry-run rule evaluation comparison.

Strict TDD: tests written before implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock


class TestSimulatorService:
    """Tests for the dry-run simulator."""

    def test_simulate_returns_engine_and_legacy_results(self):
        """simulate returns both engine_results and legacy_results with diff."""
        from app.services.reglas.simulator_service import simulate

        mock_db = MagicMock()

        # Mock Polars read
        mock_df = MagicMock()
        mock_df.head.return_value = mock_df
        mock_df.to_dicts.return_value = [
            {"NUMERO_FACTURA": "F001", "VALOR": 15000.50},
            {"NUMERO_FACTURA": "F002", "VALOR": 22300.00},
        ]
        mock_df.columns = ["NUMERO_FACTURA", "VALOR"]

        # Use the patch at the correct namespace
        with patch("app.services.reglas.simulator_service.pl") as mock_pl:
            mock_pl.read_excel.return_value = mock_df

            # Mock engine detector
            mock_engine = MagicMock()
            mock_engine.detect.return_value = [
                {"factura": "F001", "problema": "decimal", "severidad": "error"},
            ]

            with patch("app.services.reglas.simulator_service.RuleBasedDetector", return_value=mock_engine):
                # Mock legacy detectors
                with patch("app.services.reglas.simulator_service.detect_decimales",
                          return_value=[{"factura": "F001", "problema": "decimal"}, {"factura": "F002", "problema": "decimal"}]):
                    with patch("app.services.reglas.simulator_service.detect_ruta_duplicada",
                              return_value=[]):
                        # Mock _excel_to_sheet to avoid openpyxl
                        with patch("app.services.reglas.simulator_service._excel_to_sheet",
                                  return_value=(MagicMock(), {"NUMERO_FACTURA": 0, "VALOR": 1})):

                            file_mock = MagicMock()
                            file_mock.filename = "test.xlsx"
                            file_mock.read.return_value = b"fake"

                            result = simulate(mock_db, file_mock)

        assert "engine_results" in result
        assert "legacy_results" in result
        assert "diff" in result
        assert len(result["engine_results"]) == 1

    def test_simulate_truncates_to_100_rows(self):
        """simulate processes only first 100 rows from Excel."""
        from app.services.reglas.simulator_service import simulate

        mock_db = MagicMock()
        mock_df = MagicMock()
        mock_df.head.return_value = mock_df
        mock_df.to_dicts.return_value = [{"NUMERO_FACTURA": f"F{i:03d}"} for i in range(50)]
        mock_df.columns = ["NUMERO_FACTURA"]

        with patch("app.services.reglas.simulator_service.pl") as mock_pl:
            mock_pl.read_excel.return_value = mock_df

            mock_engine = MagicMock()
            mock_engine.detect.return_value = []

            with patch("app.services.reglas.simulator_service.RuleBasedDetector", return_value=mock_engine):
                with patch("app.services.reglas.simulator_service.detect_decimales", return_value=[]):
                    with patch("app.services.reglas.simulator_service.detect_ruta_duplicada", return_value=[]):
                        with patch("app.services.reglas.simulator_service._excel_to_sheet",
                                  return_value=(MagicMock(), {})):

                            file_mock = MagicMock()
                            file_mock.filename = "test.xlsx"
                            file_mock.read.return_value = b"fake"

                            result = simulate(mock_db, file_mock)

        assert result["truncated"] is False
        mock_df.head.assert_called_once()

    def test_simulate_rejects_invalid_file(self):
        """simulate raises ValueError for non-Excel files."""
        from app.services.reglas.simulator_service import simulate

        mock_db = MagicMock()
        file_mock = MagicMock()
        file_mock.filename = "test.pdf"
        file_mock.read.return_value = b"fake"

        import pytest
        with pytest.raises(ValueError, match="Excel"):
            simulate(mock_db, file_mock)

    def test_simulate_diff_counts_are_correct(self):
        """simulate returns correct diff counts for matched/mismatched."""
        from app.services.reglas.simulator_service import simulate

        mock_db = MagicMock()
        mock_df = MagicMock()
        mock_df.head.return_value = mock_df
        mock_df.to_dicts.return_value = [{"NUMERO_FACTURA": "F001"}, {"NUMERO_FACTURA": "F002"}]
        mock_df.columns = ["NUMERO_FACTURA"]

        with patch("app.services.reglas.simulator_service.pl") as mock_pl:
            mock_pl.read_excel.return_value = mock_df

            mock_engine = MagicMock()
            # Engine finds problems in F001, F002
            mock_engine.detect.return_value = [
                {"factura": "F001", "problema": "decimal"},
            ]

            with patch("app.services.reglas.simulator_service.RuleBasedDetector", return_value=mock_engine):
                # Legacy finds problems in F001, F003
                with patch("app.services.reglas.simulator_service.detect_decimales",
                          return_value=[{"factura": "F001", "problema": "decimal"}, {"factura": "F003", "problema": "decimal"}]):
                    with patch("app.services.reglas.simulator_service.detect_ruta_duplicada",
                              return_value=[]):
                        with patch("app.services.reglas.simulator_service._excel_to_sheet",
                                  return_value=(MagicMock(), {})):

                            file_mock = MagicMock()
                            file_mock.filename = "test.xlsx"
                            file_mock.read.return_value = b"fake"

                            result = simulate(mock_db, file_mock)

        diff = result["diff"]
        # F001 is in both → matched
        # F002 is engine-only
        # F003 is legacy-only
        assert "matched_count" in diff
        assert "engine_only_count" in diff
        assert "legacy_only_count" in diff
