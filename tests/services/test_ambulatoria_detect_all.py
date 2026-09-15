"""Tests for app/services/ambulatoria/detect_all.py.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openpyxl import Workbook

from app.services.ambulatoria.detect_all import detect_all_problems_ambulatoria


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


@pytest.fixture
def workbook_minimal() -> Workbook:
    """Crea un workbook con headers mínimos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.cell(row=1, column=1, value="Número Factura")
    return wb


class TestDetectAllProblemsAmbulatoria:
    """Tests para detect_all_problems_ambulatoria."""

    def _run(self, ws, indices):
        result, _ = detect_all_problems_ambulatoria(ws, indices)
        return result

    def test_retorna_dict_con_key_problemas(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "problemas" in result

    def test_retorna_area_ambulatoria(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert result.get("area") == "ambulatoria"

    def test_resultado_incluye_normalizados(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "normalizados" in result["problemas"]
        assert isinstance(result["problemas"]["normalizados"], list)

    def test_missing_columns_present(self, workbook_minimal: Workbook) -> None:
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        result = self._run(ws, indices)
        assert "missing_columns" in result

    def test_engine_branch_evaluates_resolver_rules_only(
        self, workbook_minimal: Workbook
    ) -> None:
        """Dynamic discovery: only resolver-served rules evaluate (no fixed list).

        A UI-created rule unknown to the code must run; hardcoded names the
        resolver did NOT serve must never be requested.
        """
        ws = workbook_minimal.active
        ws.cell(row=2, column=1, value="FAC-001")
        indices = {"numero_factura": 0}
        served = [
            _regla("valores_decimales", "transversal", "Decimales"),
            _regla("nueva_regla_ui", "ambulatoria", "Decimales"),
        ]
        fake_resolver = MagicMock()
        fake_resolver.resolve.return_value = served
        _RecordingDetector.reset({
            "valores_decimales": [{"factura": "FAC-001", "problema": "dec"}],
            "nueva_regla_ui": [{"factura": "FAC-001", "problema": "nuevo"}],
        })
        with (
            patch("app.database.get_session", return_value=MagicMock()),
            patch(
                "app.services.engine.domain_detection.RuleResolver",
                return_value=fake_resolver,
            ),
            patch(
                "app.services.engine.rule_based_detector.RuleBasedDetector",
                _RecordingDetector,
            ),
        ):
            result, _ = detect_all_problems_ambulatoria(ws, indices)
        assert set(_RecordingDetector.instances) == {
            "valores_decimales", "nueva_regla_ui",
        }
        facturas = [p["factura"] for p in result["problemas"]["decimales"]]
        assert facturas == ["FAC-001", "FAC-001"]
        fake_resolver.resolve.assert_called_once()
