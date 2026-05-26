"""Tests for app/services/tipo_factura_registry.py.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

import pytest


class TestGetDetectors:
    """Spec R1-R5: tipo_factura_registry.get_detectors()."""

    def test_importable(self):
        """R5: Module is importable and exposes get_detectors."""
        from app.services.tipo_factura_registry import get_detectors
        assert callable(get_detectors)

    def test_known_tipo_factura_returns_list(self):
        """R1: Known tipo_factura returns a list of callables."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Urgencias")
        assert isinstance(result, list)

    def test_known_tipo_factura_returns_callables(self):
        """R5: All items in returned list must be callable."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Urgencias")
        for item in result:
            assert callable(item), f"Expected callable, got {type(item)}"

    def test_hospitalizacion_entry_exists(self):
        """R1: Hospitalización is a known entry."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Hospitalización")
        assert isinstance(result, list)

    def test_intramural_entry_exists(self):
        """R1: Intramural is a known entry."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Intramural")
        assert isinstance(result, list)

    def test_ambulatoria_entry_exists(self):
        """R1: Ambulatoria is a known entry."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Ambulatoria")
        assert isinstance(result, list)

    def test_unknown_returns_empty_list(self):
        """R2: Unknown tipo_factura → empty list, no error."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Farmacia")
        assert result == []

    def test_empty_string_returns_empty_list(self):
        """R2: Empty string → empty list."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("")
        assert result == []

    def test_none_returns_empty_list(self):
        """R2: None → empty list."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors(None)
        assert result == []

    def test_urgencias_includes_transversals(self):
        """R4: Urgencias entry includes transversal detectors."""
        from app.services.tipo_factura_registry import get_detectors
        from app.services.transversales import (
            detect_decimales,
            detect_tipo_documento_edad,
            detect_codigo_entidad_vs_entidad_afiliacion,
            detect_tipo_usuario,
        )
        result = get_detectors("Urgencias")
        assert detect_decimales in result
        assert detect_tipo_documento_edad in result
        assert detect_codigo_entidad_vs_entidad_afiliacion in result
        assert detect_tipo_usuario in result

    def test_hospitalizacion_includes_transversals(self):
        """R4: Hospitalización entry includes transversal detectors."""
        from app.services.tipo_factura_registry import get_detectors
        from app.services.transversales import (
            detect_decimales,
            detect_tipo_documento_edad,
            detect_codigo_entidad_vs_entidad_afiliacion,
            detect_tipo_usuario,
        )
        result = get_detectors("Hospitalización")
        assert detect_decimales in result
        assert detect_tipo_documento_edad in result
        assert detect_codigo_entidad_vs_entidad_afiliacion in result
        assert detect_tipo_usuario in result

    def test_no_duplicates_in_list(self):
        """Detector lists must not contain duplicate callables."""
        from app.services.tipo_factura_registry import get_detectors
        result = get_detectors("Urgencias")
        # Check by function name (or id if available)
        ids = [id(f) for f in result]
        assert len(ids) == len(set(ids)), "Duplicate detectors found"
