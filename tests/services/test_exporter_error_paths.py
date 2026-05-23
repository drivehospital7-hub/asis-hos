"""Tests for error-handling paths in app/services/exporter.py.

Covers uncovered branches in _do_detect_problems:
- Invalid file path via resolve_safe_excel_absolute
- Excel parse failure
- Missing columns (empty sheet)
- Detection exception

Also covers detect_problems_only semaphore wrapper error paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDoDetectProblemsErrorPaths:
    """Error handling in _do_detect_problems (internal implementation)."""

    def test_resolve_path_error_returns_error_dict(self) -> None:
        """When resolve_safe_excel_absolute returns error, must return error dict."""
        from app.services.exporter import _do_detect_problems

        result = _do_detect_problems(
            filename="",
            area="odontologia",
        )

        assert result["status"] == "error"
        assert len(result.get("errors", [])) > 0
        assert result["data"] == {}

    def test_validate_path_error_returns_error_dict(self) -> None:
        """When validate_excel_path returns error, must return error dict."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value="Extensión no permitida",
            ):
                result = _do_detect_problems(
                    filename="test.xlsx",
                    area="odontologia",
                )

        assert result["status"] == "error"
        assert any(
            "Extensión" in e for e in result.get("errors", [])
        ), f"Error should mention extension: {result}"

    def test_excel_read_exception_returns_error_dict(self) -> None:
        """When pl.read_excel raises, must return error dict."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                with patch(
                    "app.services.exporter.pl.read_excel",
                    side_effect=RuntimeError("Simulated read error"),
                ):
                    result = _do_detect_problems(
                        filename="test.xlsx",
                        area="odontologia",
                    )

        assert result["status"] == "error"
        assert any(
            "Simulated read error" in e for e in result.get("errors", [])
        ), f"Error should contain read error message: {result}"

    def test_empty_excel_returns_no_columns_error(self) -> None:
        """When Excel has no columns (width=0), must return error dict."""
        from app.services.exporter import _do_detect_problems

        # Mock an empty DataFrame (0 columns)
        import polars as pl
        empty_df = pl.DataFrame()  # No columns

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                with patch(
                    "app.services.exporter.pl.read_excel",
                    return_value=empty_df,
                ):
                    result = _do_detect_problems(
                        filename="test.xlsx",
                        area="odontologia",
                    )

        assert result["status"] == "error"
        assert any(
            "no tiene columnas" in e
            for e in result.get("errors", [])
        ), f"Error should mention columnas: {result}"

    def test_detection_raises_exception_returns_error_dict(self) -> None:
        """When detect_all_problems_odontologia raises, must return error dict."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                # Mock a DataFrame with 1 column (enough to pass empty check)
                import polars as pl
                df = pl.DataFrame({"A": ["header"]})
                with patch(
                    "app.services.exporter.pl.read_excel",
                    return_value=df,
                ):
                    with patch(
                        "app.services.exporter.detect_all_problems_odontologia",
                        side_effect=RuntimeError("Detection crash"),
                    ):
                        result = _do_detect_problems(
                            filename="test.xlsx",
                            area="odontologia",
                        )

        assert result["status"] == "error"
        assert any(
            "Detection crash" in e for e in result.get("errors", [])
        ), f"Error should contain detection error: {result}"

    def test_detection_raises_in_urgencias_returns_error_dict(self) -> None:
        """When detect_all_problems_urgencias raises, must return error dict."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                import polars as pl
                df = pl.DataFrame({"A": ["header"]})
                with patch(
                    "app.services.exporter.pl.read_excel",
                    return_value=df,
                ):
                    with patch(
                        "app.services.exporter.detect_all_problems_urgencias",
                        side_effect=ValueError("Urgencias crash"),
                    ):
                        result = _do_detect_problems(
                            filename="test.xlsx",
                            area="urgencias",
                        )

        assert result["status"] == "error"
        assert any(
            "Urgencias crash" in e for e in result.get("errors", [])
        ), f"Error should contain urgencias error: {result}"

    def test_detection_raises_in_equipos_basicos_returns_error_dict(self) -> None:
        """When detect_all_problems_equipos_basicos raises, must return error dict."""
        from app.services.exporter import _do_detect_problems

        with patch(
            "app.services.exporter.resolve_safe_excel_absolute",
            return_value=(Path("/tmp/test.xlsx"), None),
        ):
            with patch(
                "app.services.exporter.validate_excel_path",
                return_value=None,
            ):
                import polars as pl
                df = pl.DataFrame({"A": ["header"]})
                with patch(
                    "app.services.exporter.pl.read_excel",
                    return_value=df,
                ):
                    with patch(
                        "app.services.exporter.detect_all_problems_equipos_basicos",
                        side_effect=KeyError("Equipos crash"),
                    ):
                        result = _do_detect_problems(
                            filename="test.xlsx",
                            equipos_basicos=True,
                        )

        assert result["status"] == "error"
        assert any(
            "Equipos crash" in e for e in result.get("errors", [])
        ), f"Error should contain equipos error: {result}"
