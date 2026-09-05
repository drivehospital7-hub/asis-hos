"""Tests for app/services/monitoreo_carpetas/name_validator.py."""

from __future__ import annotations

import pytest

from app.services.monitoreo_carpetas.name_validator import validate_name


class TestValidateName:
    """Tests for validate_name()."""

    def test_valid_fev_basic(self) -> None:
        """validate_name returns ('FEV', True) for FEV followed by digits."""
        result = validate_name("FEV12345.pdf")
        assert result == ("FEV", True)

    def test_valid_fev_case_insensitive(self) -> None:
        """validate_name is case-insensitive for FEV."""
        result = validate_name("fev001.pdf")
        assert result == ("FEV", True)

    def test_valid_fev_large_number(self) -> None:
        """validate_name handles large FEV numbers."""
        result = validate_name("FEV99999.pdf")
        assert result == ("FEV", True)

    def test_invalid_fev_non_digit_suffix(self) -> None:
        """validate_name returns ('FEV', False) for FEV with non-digit suffix."""
        result = validate_name("FEV_ABC.pdf")
        assert result == ("FEV", False)

    def test_invalid_fev_with_underscore(self) -> None:
        """validate_name returns ('FEV', False) for FEV with underscore."""
        result = validate_name("FEV_123.pdf")
        assert result == ("FEV", False)

    def test_valid_cap_basic(self) -> None:
        """validate_name returns ('CAP', True) for valid CAP pattern."""
        result = validate_name("CAP1234_ABC567.pdf")
        assert result == ("CAP", True)

    def test_valid_cap_case_insensitive(self) -> None:
        """validate_name is case-insensitive for CAP."""
        result = validate_name("cap001_def002.pdf")
        assert result == ("CAP", True)

    def test_valid_cap_prefix_inv(self) -> None:
        """validate_name handles CAP with INV_ prefix."""
        result = validate_name("INV_CAP567_DEF890.pdf")
        assert result == ("CAP", True)

    def test_invalid_cap_no_letters(self) -> None:
        """validate_name returns ('CAP', False) for CAP with missing letters."""
        result = validate_name("CAP_ABC.pdf")
        assert result == ("CAP", False)

    def test_invalid_cap_no_digits(self) -> None:
        """validate_name returns ('CAP', False) for CAP without digits."""
        result = validate_name("CAPABC.pdf")
        assert result == ("CAP", False)

    def test_unknown_no_match(self) -> None:
        """validate_name returns ('Unknown', False) for non-matching names."""
        result = validate_name("factura_generica.pdf")
        assert result == ("Unknown", False)

    def test_unknown_wrong_extension(self) -> None:
        """validate_name returns ('Unknown', False) for non-invoice files."""
        result = validate_name("notas.txt")
        assert result == ("Unknown", False)

    def test_no_extension(self) -> None:
        """validate_name handles filenames without extension."""
        result = validate_name("FEV12345")
        assert result == ("FEV", True)

    def test_cap_with_prefix_inv_case_insensitive(self) -> None:
        """validate_name handles inv_CAP with lowercase prefix."""
        result = validate_name("inv_CAP567_def890.pdf")
        assert result == ("CAP", True)
