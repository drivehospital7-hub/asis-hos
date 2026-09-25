"""Tests for engine path in hospitalizacion/detect_all.py.

NOTE: the legacy/OFF path was removed by design (is_rule_engine_enabled()
returns True hard-coded — "Engine always on"). Tests mocking engine OFF
(test_legacy_path_*) were deleted; only engine-ON tests remain.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openpyxl import Workbook

from app.constants import AREA_HOSPITALIZACION


def _regla(nombre: str, dominio: str, grupo: str | None):
    from app.models import Regla

    return Regla(
        id=abs(hash(nombre)) % 10_000 + 1, nombre=nombre, dominio=dominio,
        estado="active", version=1, prioridad=10, severidad="error",
        activo=True, grupo_error=grupo,
    )


class _RecordingDetector:
    """Fake RuleBasedDetector: records requested names, serves payloads."""

    instances: list[str] = []
    payloads: dict[str, list[dict]] = {}

    def __init__(self, name: str, session, **kwargs):
        type(self).instances.append(name)
        self._name = name

    def detect(self, *args, **kwargs):
        return [dict(p) for p in type(self).payloads.get(self._name, [])]

    @classmethod
    def reset(cls, payloads: dict | None = None) -> None:
        cls.instances = []
        cls.payloads = dict(payloads or {})


_HOSP_KEYS = {
    "normalizados", "centros_de_costos", "ide_contrato",
    "cups_equivalentes", "decimales", "tipo_identificacion_edad",
    "tipo_identificacion_entidad", "codigo_entidad_vs_afiliacion",
    "tipo_usuario", "cantidades_hospitalizacion",
    "cantidades_soat_hospitalizacion", "copago_entidad",
    "profesionales", "cups_sin_contrato",
}


def _build_simple_sheet() -> tuple[Workbook, dict[str, int | None]]:
    """Build a workbook with minimal columns for testing."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"

    headers = [
        "Número Factura", "Código", "Cantidad", "Vlr. Unitario",
        "Vlr. Procedimiento", "Tipo Doc.", "Edad", "Tipo Identificación",
        "Código Entidad Cobrar", "Entidad Afiliación", "Tipo Usuario",
        "Vlr. Copago", "Código CUPS", "Fec Factura", "Fecha Cierre",
        "Responsable Cierra",
    ]
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=header)

    ws.cell(row=2, column=1, value="FAC-001")
    ws.cell(row=2, column=3, value=5)
    ws.cell(row=2, column=4, value=100.50)
    ws.cell(row=2, column=5, value=100.50)

    indices = {h: i for i, h in enumerate(headers)}
    return wb, indices


class TestHospitalizacionEngineToggle:
    """Tests for the engine toggle in detect_all_problems_hospitalizacion."""

    def _make_mock_session(self) -> MagicMock:
        """Create a mock DB session that returns empty results."""
        session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None  # No rule found => empty result
        mock_query.all.return_value = []
        session.query.return_value = mock_query
        return session

    @patch("app.database.get_session")
    @patch("app.services.engine.rule_based_detector.RuleBasedDetector")
    @patch("app.services.hospitalizacion.detect_all.is_rule_engine_enabled", return_value=True)
    def test_engine_path_evaluates_resolver_rules_only(
        self, mock_enabled: MagicMock, mock_detector_cls: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """Dynamic discovery: only resolver-served rules evaluate (no fixed list)."""
        served = [
            _regla("cantidades_hospitalizacion", "hospitalizacion", "Cantidades Hospitalización"),
            _regla("nueva_regla_ui", "hospitalizacion", "Cantidades Hospitalización"),
        ]
        fake_resolver = MagicMock()
        fake_resolver.resolve.return_value = served
        _RecordingDetector.reset({
            "cantidades_hospitalizacion": [{"factura": "FAC-001", "problema": "c"}],
            "nueva_regla_ui": [{"factura": "FAC-001", "problema": "nuevo"}],
        })
        mock_get_session.return_value = MagicMock()
        mock_detector_cls.side_effect = _RecordingDetector

        from app.services.hospitalizacion.detect_all import (
            detect_all_problems_hospitalizacion,
        )
        with patch(
            "app.services.engine.domain_detection.RuleResolver",
            return_value=fake_resolver,
        ):
            wb, indices = _build_simple_sheet()
            result, responsables = detect_all_problems_hospitalizacion(
                wb.active, indices,
            )

        assert set(_RecordingDetector.instances) == {
            "cantidades_hospitalizacion", "nueva_regla_ui",
        }

        assert "problemas" in result
        assert isinstance(result["problemas"], dict)
        assert "totales" in result
        assert result["area"] == AREA_HOSPITALIZACION
        assert len(result["problemas"]["cantidades_hospitalizacion"]) == 2
        assert responsables == {}

    # NOTE: legacy/OFF path removed — engine is always on, so tests mocking
    # is_rule_engine_enabled → False were deleted (no OFF branch exists).

    @patch("app.database.get_session")
    @patch("app.services.engine.rule_based_detector.RuleBasedDetector")
    @patch("app.services.hospitalizacion.detect_all.is_rule_engine_enabled", return_value=True)
    def test_engine_path_with_all_detectors(
        self, mock_enabled: MagicMock, mock_detector_cls: MagicMock,
        mock_get_session: MagicMock,
    ) -> None:
        """Engine path must produce problems dict with all keys present."""
        served = [
            _regla("centro_costo_hospitalizacion_valido", "hospitalizacion", "Centros de Costo"),
            _regla("ide_contrato_hospitalizacion_valido", "hospitalizacion", "IDE Contrato"),
            _regla("cantidades_hospitalizacion", "hospitalizacion", "Cantidades Hospitalización"),
            _regla("cantidades_soat_hospitalizacion", "hospitalizacion", "Cantidades SOAT Hospitalización"),
            _regla("valores_decimales", "transversal", "Decimales"),
            _regla("codigo_entidad", "transversal", "Codigo-Entidad-vs-Afiliacion"),
            _regla("tipo_usuario_valido", "transversal", "Tipo Usuario"),
            _regla("copago_entidad_valido", "transversal", "Copago vs Entidad"),
            _regla("profesional_hospitalizacion_valido", "hospitalizacion", "Profesionales"),
            _regla("cups_sin_contrato", "transversal", "Cups Sin Contrato"),
        ]
        fake_resolver = MagicMock()
        fake_resolver.resolve.return_value = served
        _RecordingDetector.reset()
        mock_get_session.return_value = MagicMock()
        mock_detector_cls.side_effect = _RecordingDetector

        from app.services.hospitalizacion.detect_all import (
            detect_all_problems_hospitalizacion,
        )
        with patch(
            "app.services.engine.domain_detection.RuleResolver",
            return_value=fake_resolver,
        ):
            wb, indices = _build_simple_sheet()
            result, _ = detect_all_problems_hospitalizacion(wb.active, indices)

        assert set(_RecordingDetector.instances) == {r.nombre for r in served}

        problemas = result["problemas"]

        for key in _HOSP_KEYS:
            assert key in problemas, f"Missing key: {key}"
