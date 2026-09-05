"""Tests for app/constants/monitoreo_carpetas.py."""

from __future__ import annotations

import json

import pytest

from app.constants.monitoreo_carpetas import (
    CAP_REGEX,
    ENV_MONITOREO_ROOTS,
    FEV_REGEX,
    MAX_CONCURRENT_SCANS,
    SCAN_TIMEOUT_PER_FACTURADOR,
    STATUS_KEYWORDS,
    STATUS_EN_REVISION,
    STATUS_POR_CORREGIR,
    STATUS_VERIFICADA,
)


class TestConstantsMonitoreoCarpetas:
    """Constants module integrity tests."""

    def test_status_keywords_has_all_three_statuses(self) -> None:
        """STATUS_KEYWORDS must have keys Verificada, Por corregir, En revisión."""
        assert STATUS_VERIFICADA in STATUS_KEYWORDS
        assert STATUS_POR_CORREGIR in STATUS_KEYWORDS
        assert STATUS_EN_REVISION in STATUS_KEYWORDS

    def test_status_verificada_keywords_list(self) -> None:
        """Verificada must include FACTURAS CAPITA OK and LISTAS PARA PASAR."""
        keywords = STATUS_KEYWORDS[STATUS_VERIFICADA]
        assert isinstance(keywords, list)
        assert len(keywords) >= 2
        assert "FACTURAS CAPITA OK" in keywords
        assert "LISTAS PARA PASAR" in keywords

    def test_status_por_corregir_keywords_list(self) -> None:
        """Por corregir must include CORREGIR and CORRECCION."""
        keywords = STATUS_KEYWORDS[STATUS_POR_CORREGIR]
        assert isinstance(keywords, list)
        assert len(keywords) >= 2
        assert "CORREGIR" in keywords
        assert "CORRECCION" in keywords

    def test_status_en_revision_is_default_fallback(self) -> None:
        """En revisión is the fallback status (mapped to 'default')."""
        assert STATUS_EN_REVISION in STATUS_KEYWORDS
        assert "default" in STATUS_KEYWORDS[STATUS_EN_REVISION]

    def test_fev_regex_matches_valid(self) -> None:
        """FEV regex must match FEV followed by digits."""
        import re
        pattern = re.compile(FEV_REGEX, re.IGNORECASE)
        assert pattern.fullmatch("FEV12345")
        assert pattern.fullmatch("fev001")
        assert pattern.fullmatch("FEV99999")

    def test_fev_regex_rejects_invalid(self) -> None:
        """FEV regex must reject non-digit suffixes."""
        import re
        pattern = re.compile(FEV_REGEX, re.IGNORECASE)
        assert not pattern.fullmatch("FEV_ABC")
        assert not pattern.fullmatch("FEV_123")
        assert not pattern.fullmatch("FEV")

    def test_cap_regex_matches_valid(self) -> None:
        """CAP regex must match CAP digits_letters digits."""
        import re
        pattern = re.compile(CAP_REGEX, re.IGNORECASE)
        assert pattern.fullmatch("CAP1234_ABC567")
        assert pattern.fullmatch("cap001_def002")
        assert pattern.fullmatch("CAP99999_ZZZ000")

    def test_cap_regex_rejects_invalid(self) -> None:
        """CAP regex must reject malformed patterns."""
        import re
        pattern = re.compile(CAP_REGEX, re.IGNORECASE)
        assert not pattern.fullmatch("CAP_ABC")
        assert not pattern.fullmatch("CAP123_")
        assert not pattern.fullmatch("CAP_123_ABC")

    def test_env_var_name_is_string(self) -> None:
        """ENV_MONITOREO_ROOTS must be a non-empty string."""
        assert isinstance(ENV_MONITOREO_ROOTS, str)
        assert len(ENV_MONITOREO_ROOTS) > 0

    def test_scan_timeout_is_positive_int(self) -> None:
        """SCAN_TIMEOUT_PER_FACTURADOR must be a positive int."""
        assert isinstance(SCAN_TIMEOUT_PER_FACTURADOR, int)
        assert SCAN_TIMEOUT_PER_FACTURADOR > 0

    def test_max_concurrent_is_positive_int(self) -> None:
        """MAX_CONCURRENT_SCANS must be a positive int."""
        assert isinstance(MAX_CONCURRENT_SCANS, int)
        assert MAX_CONCURRENT_SCANS > 0

    def test_env_var_must_be_json_parsable_list(self) -> None:
        """ENV var value, if set, must be a JSON list of strings."""
        sample = '["\\\\server\\billing1", "\\\\server\\billing2"]'
        parsed = json.loads(sample)
        assert isinstance(parsed, list)
        assert all(isinstance(p, str) for p in parsed)
