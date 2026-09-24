"""Tests for simulator_service.py — dry-run of the real /procesar pipeline.

The simulator runs detect_problems_only (area unificada, ALL rows) inside
a no-persist scope, optionally filtered to selected rule ids, and returns
a /procesar-shaped payload. No legacy detectors are used.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _norm_row(factura: str, regla: str, tipo_error: str = "Decimales",
              tipo_factura: str = "Urgencias") -> dict:
    return {
        "tipo_error": tipo_error,
        "tipo_factura": tipo_factura,
        "factura": factura,
        "fec_factura": "2026-01-01",
        "responsable_cierra": "Resp",
        "descripcion": f"desc {factura}",
        "procedimiento": "proc",
        "detalle": "det",
        "fecha_cierre_vacia": False,
        "regla": regla,
    }


def _pipeline_result(rows: list[dict]) -> tuple[dict, int]:
    return ({
        "status": "success",
        "data": {
            "problemas": {"problemas": {"normalizados": rows}, "missing_columns": []},
            "tipos_procesados": ["Urgencias"],
        },
        "errors": [],
    }, 200)


def _file_mock(filename: str = "test.xlsx") -> MagicMock:
    file_mock = MagicMock()
    file_mock.filename = filename
    return file_mock


class TestSimulate:
    """simulate() contract: /procesar-shaped payload, rule filter, no persist."""

    def _run(self, file_mock, pipeline, rule_ids=None, sheet_name=None):
        from app.services.reglas import simulator_service as sim

        with patch.object(sim, "save_temp_excel",
                          return_value=(Path("/tmp/x.xlsx"), None)) as m_save, \
             patch.object(sim, "detect_problems_only",
                          return_value=pipeline) as m_detect, \
             patch.object(sim, "cleanup_temp_excel") as m_cleanup, \
             patch.object(sim.export_store, "put", return_value="exp-1") as m_put:
            result = sim.simulate(None, file_mock, rule_ids=rule_ids,
                                  sheet_name=sheet_name)
        return result, m_save, m_detect, m_cleanup, m_put

    def test_rejects_non_excel_extension(self):
        """Invalid extension from save_temp_excel raises ValueError."""
        from app.services.reglas import simulator_service as sim

        with patch.object(sim, "save_temp_excel",
                          return_value=(None, "Formato no permitido. Usar: .xlsx")):
            with pytest.raises(ValueError, match="Formato no permitido"):
                sim.simulate(None, _file_mock("test.pdf"))

    def test_pipeline_error_raises_value_error(self):
        """detect_problems_only error status surfaces as ValueError."""
        from app.services.reglas import simulator_service as sim

        err = ({"status": "error", "data": {}, "errors": ["boom"]}, 500)
        with patch.object(sim, "save_temp_excel",
                          return_value=(Path("/tmp/x.xlsx"), None)), \
             patch.object(sim, "detect_problems_only", return_value=err), \
             patch.object(sim, "cleanup_temp_excel"):
            with pytest.raises(ValueError, match="boom"):
                sim.simulate(None, _file_mock())

    def test_missing_columns_raise_value_error(self):
        """Missing Excel columns surface as ValueError (same as /procesar)."""
        from app.services.reglas import simulator_service as sim

        res = ({
            "status": "success",
            "data": {"problemas": {"problemas": {}, "missing_columns": ["Código"]}},
            "errors": [],
        }, 200)
        with patch.object(sim, "save_temp_excel",
                          return_value=(Path("/tmp/x.xlsx"), None)), \
             patch.object(sim, "detect_problems_only", return_value=res), \
             patch.object(sim, "cleanup_temp_excel"):
            with pytest.raises(ValueError, match="Columnas no encontradas"):
                sim.simulate(None, _file_mock())

    def test_returns_procesar_shaped_payload_with_all_rows(self):
        """No 100-row cap: every normalized row flows into the payload."""
        rows = [_norm_row(f"F{i:03d}", "#5") for i in range(250)]
        result, _, m_detect, m_cleanup, _ = self._run(
            _file_mock(), _pipeline_result(rows))

        assert set(result) >= {
            "errores", "total_errores", "tipos_procesados",
            "columnas", "export_id", "reglas_aplicadas",
        }
        assert result["total_errores"] == 250
        assert result["reglas_aplicadas"] == []
        assert result["export_id"] == "exp-1"
        # Area unificada + active sheet by default
        _, kwargs = m_detect.call_args
        assert kwargs["area"] == "unificada"
        assert kwargs["sheet_name"] is None
        m_cleanup.assert_called_once()

    def test_filters_by_selected_rule_ids_before_dedup(self):
        """Only rows whose regla matches the selection survive."""
        rows = [
            _norm_row("F001", "#5"),
            _norm_row("F002", "#7"),
            _norm_row("F003", "#5"),
        ]
        result, _, _, _, _ = self._run(
            _file_mock(), _pipeline_result(rows), rule_ids=[5])

        assert result["total_errores"] == 2
        assert result["reglas_aplicadas"] == [5]
        facturas = [
            f["factura"]
            for fg in result["errores"]
            for tg in fg["tipos"]
            for f in tg["facturas"]
        ]
        assert sorted(facturas) == ["F001", "F003"]

    def test_sheet_name_forwarded(self):
        """Optional sheet_name reaches detect_problems_only."""
        rows = [_norm_row("F001", "#5")]
        _, _, m_detect, _, _ = self._run(
            _file_mock(), _pipeline_result(rows), sheet_name="Hoja2")

        _, kwargs = m_detect.call_args
        assert kwargs["sheet_name"] == "Hoja2"

    def test_export_cache_failure_omits_export_id(self):
        """Disk cache failure never breaks the JSON flow."""
        from app.services.reglas import simulator_service as sim

        rows = [_norm_row("F001", "#5")]
        with patch.object(sim, "save_temp_excel",
                          return_value=(Path("/tmp/x.xlsx"), None)), \
             patch.object(sim, "detect_problems_only",
                          return_value=_pipeline_result(rows)), \
             patch.object(sim, "cleanup_temp_excel"), \
             patch.object(sim.export_store, "put", side_effect=OSError("disk")):
            result = sim.simulate(None, _file_mock())

        assert "export_id" not in result
        assert result["total_errores"] == 1


class TestSimulationScope:
    """simulation_scope: rule subset + forced no-persist in detect_domain_rules."""

    def test_scope_filters_rules_and_forces_no_persist(self):
        """Only selected rule ids evaluate; persist is forced False."""
        from app.services.engine import domain_detection as dd

        rule_a = MagicMock()
        rule_a.nombre = "regla_a"
        rule_a.id = 5
        rule_a.grupo_error = "G"
        rule_b = MagicMock()
        rule_b.nombre = "regla_b"
        rule_b.id = 7
        rule_b.grupo_error = "G"

        session = MagicMock()
        with patch.object(dd.RuleResolver, "resolve",
                          return_value=[rule_a, rule_b]), \
             patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_det:
            m_det.return_value.detect.return_value = []
            with dd.simulation_scope({5}):
                batches = dd.detect_domain_rules(
                    session, "urgencias", persist=True)

        # Only regla_a evaluated, persist forced off
        assert [b.nombre for b in batches] == ["regla_a"]
        _, kwargs = m_det.return_value.detect.call_args
        assert kwargs["persist"] is False

    def test_scope_resets_after_exit(self):
        """ContextVar overrides do not leak outside the scope."""
        from app.services.engine import domain_detection as dd

        assert dd._SIM_ONLY_RULE_IDS.get() is None
        assert dd._SIM_NO_PERSIST.get() is False
        with dd.simulation_scope({5}):
            assert dd._SIM_ONLY_RULE_IDS.get() == frozenset({5})
            assert dd._SIM_NO_PERSIST.get() is True
        assert dd._SIM_ONLY_RULE_IDS.get() is None
        assert dd._SIM_NO_PERSIST.get() is False
