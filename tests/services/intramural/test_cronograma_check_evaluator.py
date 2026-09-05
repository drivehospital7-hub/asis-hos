"""Strict TDD F5.1: Tests for CronogramaCheckEvaluator.

RED phase: tests written BEFORE implementation.
GREEN phase: implement minimum code to pass.
TRIANGULATE: add edge cases to force real logic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.engine.context import EvaluationContext


class TestCronogramaCheckEvaluator:
    """Unit tests for CronogramaCheckEvaluator (operator: cronograma_check).

    Each test creates an EvaluationContext with needed invoice_data fields
    and asserts the evaluator returns True (detection) or False (valid/bypass).
    """

    def _make_context(self, overrides: dict | None = None) -> EvaluationContext:
        """Build a default valid Intramural context for cronograma check.

        Defaults: tipo_factura=Intramural, codigo_tipo=02, lab=Si,
        codigo=901210, responsable_cierra='', fec_factura valid.
        """
        data = {
            "tipo_factura_descripcion": "Intramural",
            "codigo_tipo_procedimiento": "02",
            "laboratorio": "Si",
            "codigo": "901210",
            "responsable_cierra": "",
            "fec_factura": "2024-06-01",
        }
        if overrides:
            data.update(overrides)
        return EvaluationContext(invoice_data=data)

    # ── Scenario 5.5: Bacterióloga en cronograma → OK ──

    def test_profesional_en_turno_retorna_false(self):
        """Cronograma tiene a la bacterióloga → False (no detection)."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE/PYM"}],
        ) as mock_get:
            ctx = self._make_context()
            evaluator = CronogramaCheckEvaluator()
            # 03374 = MOLINA ALVAREZ KAROL DAYANNA
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False  # No detection
        mock_get.assert_called_once()

    # ── Scenario 5.6: Bacterióloga NO en cronograma → error ──

    def test_profesional_fuera_turno_retorna_true(self):
        """Cronograma vacío sin la bacterióloga → True (detection)."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "OTRA PERSONA", "codigo": "CE"}],
        ) as mock_get:
            ctx = self._make_context()
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is True  # Detection
        mock_get.assert_called_once()

    def test_cronograma_vacio_retorna_false(self):
        """No hay cronograma ese día → False (skip sin error)."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[],
        ) as mock_get:
            ctx = self._make_context()
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False  # No detection when no cronograma data
        mock_get.assert_called_once()

    # ── Scenario 5.7: PROFESIONALES_EXCEPTUADOS_CRONOGRAMA bypass ──

    def test_profesional_exceptuado_bypass_cronograma(self):
        """02217 (MADROÑERO) bypassa cronograma → False, no se llama get_turno."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
        ) as mock_get:
            ctx = self._make_context()
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "02217", None, context=ctx)

        assert result is False  # Bypass = no detection
        mock_get.assert_not_called()

    # ── Scenario 5.8: Chapuel → solo PYM ──

    def test_chapuel_envia_siglas_filter_pym(self):
        """Chapuel → siglas_filter={'PYM'} se pasa a get_turno_del_dia."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "PYM"}],
        ) as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "CHAPUEL CASANOVA ANGIE TATIANA",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False  # In PYM turno → OK
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("siglas_filter") == {"PYM"}, (
            f"Expected siglas_filter={{'PYM'}}, got {call_kwargs.get('siglas_filter')}"
        )

    def test_chapuel_sin_turno_pym_deteccion(self):
        """Chapuel filtra PYM y no hay profesional en turnos PYM → True."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "OTRA PERSONA", "codigo": "PYM"}],
        ) as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "CHAPUEL CASANOVA ANGIE TATIANA",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is True  # Professional not in PYM turnos
        mock_get.assert_called_once()

    def test_chapuel_solo_ce_no_turnos_skip(self):
        """Chapuel filtra PYM pero solo hay CE → get_turno_del_dia devuelve [] → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[],
        ) as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "CHAPUEL CASANOVA ANGIE TATIANA",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False  # Skip cuando no hay turnos (legacy behavior)
        mock_get.assert_called_once()

    # ── Scenario 5.9: Tapia → solo CE ──

    def test_tapia_envia_siglas_filter_ce(self):
        """Tapia → siglas_filter={'CE'} se pasa a get_turno_del_dia."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE"}],
        ) as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "TAPIA PERDOMO ANYI CATALEYA",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False  # In CE turno → OK
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("siglas_filter") == {"CE"}, (
            f"Expected siglas_filter={{'CE'}}, got {call_kwargs.get('siglas_filter')}"
        )

    def test_ordonez_envia_siglas_filter_ce(self):
        """Ordoñez también pasa siglas_filter={'CE'}."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE"}],
        ) as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "ORDOÑEZ MEZA SILVIA ELEY",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("siglas_filter") == {"CE"}

    # ── Scenario 5.10: Facturador Urgencias bypass ──

    def test_facturador_urgencias_bypass_total(self):
        """Responsable in FACTURADORES_URGENCIAS → False, no llama get_turno."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "responsable_cierra": "ARIAS CULCHA ANGIE CAROLINA",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    # ── Filters: tipo, lab, codigo ──

    def test_tipo_no_02_ni_05_retorna_false(self):
        """Tipo no 02/05 → skip (no detection)."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "codigo_tipo_procedimiento": "01",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_tipo_02_sin_lab_si_retorna_false(self):
        """Tipo 02 pero lab=No → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "laboratorio": "No",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_codigo_en_excepciones_bacteriologa_retorna_false(self):
        """Código in EXCEPCIONES_BACTERIOLOGA → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "codigo": "904903",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_no_intramural_retorna_false(self):
        """Tipo factura no Intramural → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "tipo_factura_descripcion": "Hospitalización",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_fecha_invalida_retorna_false(self):
        """fec_factura inválida → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context({
                "fec_factura": "INVALID_DATE",
            })
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "03374", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_codigo_profesional_vacio_retorna_false(self):
        """Sin codigo_profesional → skip."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch("app.services.cronograma_bacteriologas_service.get_turno_del_dia") as mock_get:
            ctx = self._make_context()
            evaluator = CronogramaCheckEvaluator()
            result = evaluator.evaluate({}, "", None, context=ctx)

        assert result is False
        mock_get.assert_not_called()

    def test_context_none_retorna_false(self):
        """Sin context → False."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        evaluator = CronogramaCheckEvaluator()
        result = evaluator.evaluate({}, "03374", None, context=None)
        assert result is False

    # ── Cache test: same day → one call only ──

    def test_cache_misma_fecha_una_sola_llamada(self):
        """Dos evaluaciones misma fecha → una sola llamada a get_turno_del_dia."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator

        with patch(
            "app.services.cronograma_bacteriologas_service.get_turno_del_dia",
            return_value=[{"nombre": "MOLINA ALVAREZ KAROL DAYANNA", "codigo": "CE/PYM"}],
        ) as mock_get:
            ctx1 = self._make_context({"fec_factura": "2024-06-01"})
            ctx2 = self._make_context({"fec_factura": "2024-06-01"})
            evaluator = CronogramaCheckEvaluator()
            evaluator.evaluate({}, "03374", None, context=ctx1)
            evaluator.evaluate({}, "03374", None, context=ctx2)

        assert mock_get.call_count == 1

    # ── Registry ──

    def test_registrado_en_evaluator_registry(self):
        """CronogramaCheckEvaluator debe estar en EVALUATOR_REGISTRY."""
        from app.services.engine.evaluators import EVALUATOR_REGISTRY
        assert "cronograma_check" in EVALUATOR_REGISTRY

    def test_operator_correcto(self):
        """Operator debe ser 'cronograma_check'."""
        from app.services.engine.evaluators import CronogramaCheckEvaluator
        assert CronogramaCheckEvaluator.operator == "cronograma_check"
