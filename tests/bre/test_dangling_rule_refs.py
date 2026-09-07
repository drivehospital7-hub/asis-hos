"""Dangling rule-name references — reproduce + verify code-side alias mapping.

The 12 rule names below are referenced by detectors/engine but exist in NO
database (prod or dev), so the engine logs "Rule not found" and silently
returns []. This module:

- reproduces the bug per reference (dangling name on an empty session → []),
- verifies each MAPPED detector returns non-empty on its fixture against a
  mock session serving the target rule tree (verbatim from migrations/),
- verifies detect_all wiring requests the mapped names and NEVER the
  dangling ones (recording RuleBasedDetector fake, engine flag ON),
- verifies documented gaps explicitly skip engine evaluation ([] + no
  dangling-name lookup) instead of attempting a doomed rule load.

Hermetic: MagicMock sessions only — no DB writes, no servers (Ref #1).
"""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

from openpyxl import Workbook


# ── Mock-session helpers (same pattern as tests/engine/test_snapshot_*) ──

def _mock_session(
    rule_name: str | None,
    dominio: str,
    descripcion: str,
    condiciones: list[dict],
    parametros: Any = None,
):
    """Session serving one rule tree, or nothing when rule_name is None.

    None reproduces the production bug: RuleResolver/load returns no rule →
    engine logs "Rule not found" and RuleBasedDetector.detect returns [].
    """
    from app.models import Regla

    session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query

    if rule_name is None:
        mock_query.first.return_value = None
        mock_query.all.return_value = []
    else:
        regla = Regla(
            id=1, nombre=rule_name, dominio=dominio,
            estado="active", version=1, prioridad=10, severidad="warning",
            descripcion=descripcion,
        )
        regla.parametros = parametros
        mock_query.first.return_value = regla
        cond_mocks = []
        for cd in condiciones:
            m = MagicMock()
            m.id = cd["id"]
            m.regla_id = cd.get("regla_id", 1)
            m.padre_id = cd["padre_id"]
            m.tipo = cd["tipo"]
            m.operador = cd.get("operador")
            m.fuente_datos = cd.get("fuente_datos")
            m.valor_esperado = cd.get("valor_esperado")
            m.orden = cd.get("orden", 0)
            cond_mocks.append(m)
        mock_query.all.return_value = cond_mocks
    session.query.return_value = mock_query
    return session


def _run(rule_name: str | None, dominio: str, descripcion: str,
         condiciones: list[dict], ws, indices, parametros: Any = None):
    from app.services.engine.rule_based_detector import RuleBasedDetector

    session = _mock_session(rule_name, dominio, descripcion, condiciones, parametros)
    return RuleBasedDetector(rule_name or "dangling", session).detect(
        ws, indices, persist=False,
    )


def _wb(headers: list[str], rows: list[tuple]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    for col, name in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=name)
    for r, row in enumerate(rows, start=2):
        for c, val in enumerate(row, start=1):
            ws.cell(row=r, column=c, value=val)
    return wb


def _cid_seq():
    n = [0]

    def nxt() -> int:
        n[0] += 1
        return n[0]

    return nxt


# ── Rule-level: cantidades_anomalas → 3 transversal rules (012 verbatim) ──

CANTIDADES_HEADERS = ["numero_factura", "tipo_procedimiento", "cantidad", "convenio_facturado"]


class TestCantidadesAnomalasMapping:
    """Legacy detect_cantidades_anomalas = OR of 3 checks (consultas≥2,
    cantidad>10, PyP≥3); equipos constants are exactly 2/10/3, matching the
    three seeded transversal trees. All three must be evaluated."""

    def _consultas_tree(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "AND", "orden": 0}
        return [root,
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "eq",
                 "fuente_datos": "invoice.tipo_procedimiento", "valor_esperado": "Consultas", "orden": 0},
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "gte",
                 "fuente_datos": "invoice.cantidad", "valor_esperado": 2, "orden": 1}]

    def test_consultas_rule_matches_fixture(self):
        wb = _wb(CANTIDADES_HEADERS, [("E-001", "Consultas", 2, "Subsidiado")])
        indices = {h: i for i, h in enumerate(CANTIDADES_HEADERS)}
        res = _run("cantidad_consultas_anomalas", "transversal", "Consultas >= 2",
                   self._consultas_tree(), wb.active, indices)
        assert len(res) == 1 and res[0]["factura"] == "E-001"

    def test_general_rule_matches_fixture(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "AND", "orden": 0}
        tree = [root,
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "gt",
                 "fuente_datos": "invoice.cantidad", "valor_esperado": 10, "orden": 0}]
        wb = _wb(CANTIDADES_HEADERS, [("E-002", "Procedimientos", 11, "Subsidiado")])
        indices = {h: i for i, h in enumerate(CANTIDADES_HEADERS)}
        res = _run("cantidad_general_anomalas", "transversal", "cantidad > 10",
                   tree, wb.active, indices)
        assert len(res) == 1 and res[0]["factura"] == "E-002"

    def test_pyp_rule_matches_fixture(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "AND", "orden": 0}
        tree = [root,
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "eq",
                 "fuente_datos": "invoice.convenio_facturado",
                 "valor_esperado": "Promocion y Prevencion", "orden": 0},
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "gte",
                 "fuente_datos": "invoice.cantidad", "valor_esperado": 3, "orden": 1}]
        wb = _wb(CANTIDADES_HEADERS, [("E-003", "Procedimientos", 3, "Promocion y Prevencion")])
        indices = {h: i for i, h in enumerate(CANTIDADES_HEADERS)}
        res = _run("cantidad_pyp_anomalas", "transversal", "PyP >= 3",
                   tree, wb.active, indices)
        assert len(res) == 1 and res[0]["factura"] == "E-003"

    def test_dangling_name_reproduces_empty(self):
        """BUG repro: 'cantidades_anomalas' exists nowhere → Rule not found → []."""
        wb = _wb(CANTIDADES_HEADERS, [("E-001", "Consultas", 2, "Subsidiado")])
        indices = {h: i for i, h in enumerate(CANTIDADES_HEADERS)}
        assert _run(None, "transversal", "", [], wb.active, indices) == []


# ── Rule-level: ide_contrato_equipos_basicos_valido → ide_contrato_odontologia_valido ──

class TestIdeContratoEquiposMapping:
    """Equipos legacy falls back to detect_ide_contrato_odontologia
    (equipos detect_all else-branch); 014 seeds ide_contrato_odontologia_valido
    (111 conds). Representative branch mirrored verbatim (ESS118 even shape)."""

    def _branch_tree(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "OR", "orden": 0}
        branch = {"id": nid(), "padre_id": root["id"], "tipo": "composite", "operador": "AND", "orden": 0}
        notn = {"id": nid(), "padre_id": branch["id"], "tipo": "composite", "operador": "NOT", "orden": 2}
        codes = ["890203", "990203", "990212", "997002", "997106", "997107", "997301", "P0000011"]
        return [root, branch,
                {"id": nid(), "padre_id": branch["id"], "tipo": "atomic", "operador": "eq",
                 "fuente_datos": "invoice.codigo_entidad_cobrar", "valor_esperado": "ESS118", "orden": 0},
                {"id": nid(), "padre_id": branch["id"], "tipo": "atomic", "operador": "in",
                 "fuente_datos": "invoice.codigo", "valor_esperado": codes, "orden": 1},
                notn,
                {"id": nid(), "padre_id": notn["id"], "tipo": "atomic", "operador": "in",
                 "fuente_datos": "invoice.ide_contrato", "valor_esperado": ["970", "974"], "orden": 0}]

    def test_odonto_rule_matches_equipos_fixture(self):
        headers = ["numero_factura", "codigo", "codigo_entidad_cobrar", "ide_contrato"]
        wb = _wb(headers, [("E-010", "890203", "ESS118", "000")])
        indices = {h: i for i, h in enumerate(headers)}
        res = _run("ide_contrato_odontologia_valido", "odontologia", "IDE Contrato Odontologia",
                   self._branch_tree(), wb.active, indices)
        assert len(res) == 1 and res[0]["factura"] == "E-010"

    def test_dangling_name_reproduces_empty(self):
        headers = ["numero_factura", "codigo", "codigo_entidad_cobrar", "ide_contrato"]
        wb = _wb(headers, [("E-010", "890203", "ESS118", "000")])
        indices = {h: i for i, h in enumerate(headers)}
        assert _run(None, "odontologia", "", [], wb.active, indices) == []


# ── Rule-level: revision_cantidad_urgencias_valido → revision_cantidad_urgencias ──

class TestRevisionCantidadUrgenciasMapping:
    """013 seeds revision_cantidad_urgencias (group_by numero_factura SUM >
    1). Semantic delta vs the row-level cascade is documented in the PR body;
    it is the only existing rule covering the revisión-cantidad intent."""

    PARAMS = [{"group_by": "numero_factura",
               "aggregations": [{"field": "cantidad", "target": "sum_cantidad", "function": "sum"}]}]

    def _tree(self):
        return [{"id": 1, "padre_id": None, "tipo": "atomic", "operador": "gt",
                 "fuente_datos": "invoice.sum_cantidad", "valor_esperado": "1", "orden": 0}]

    def test_group_rule_matches_fixture(self):
        headers = ["numero_factura", "cantidad"]
        wb = _wb(headers, [("U-001", 1), ("U-001", 1)])
        indices = {h: i for i, h in enumerate(headers)}
        res = _run("revision_cantidad_urgencias", "urgencias", "suma > 1",
                   self._tree(), wb.active, indices, parametros=self.PARAMS)
        assert len(res) == 1 and res[0]["factura"] == "U-001"

    def test_dangling_name_reproduces_empty(self):
        headers = ["numero_factura", "cantidad"]
        wb = _wb(headers, [("U-001", 1), ("U-001", 1)])
        indices = {h: i for i, h in enumerate(headers)}
        assert _run(None, "urgencias", "", [], wb.active, indices) == []


# ── Rule-level: sala_observacion_valido → sala_obs_check_set ──

class TestSalaObservacionMapping:
    """sala_observacion_valido has no covering rule that can fire:
    sala_observacion_entidad/_estancia_prolongada run the deregistered
    sala_obs_check operator (condition_evaluator returns outcome False +
    'Unknown evaluator operator' — seeded but dead). The executable,
    dev-live rule for the slot is sala_obs_check_set (014 verbatim:
    obligatorios 890701+890601 presence when sala codes present)."""

    SALA_CODES = ["5DSB01", "05DSB01", "129B02", "38114", "38915"]

    def _tree(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "AND", "orden": 0}
        notn = {"id": nid(), "padre_id": root["id"], "tipo": "composite", "operador": "NOT", "orden": 1}
        return [root,
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic",
                 "operador": "set_intersects", "fuente_datos": "group.collect_set_codigo",
                 "valor_esperado": list(self.SALA_CODES), "orden": 0},
                notn,
                {"id": nid(), "padre_id": notn["id"], "tipo": "atomic",
                 "operador": "set_contains_all", "fuente_datos": "group.collect_set_codigo",
                 "valor_esperado": ["890701", "890601"], "orden": 0}]

    PARAMS = [{"group_by": "factura",
               "aggregations": [{"field": "codigo", "function": "collect_set"}]}]

    def _fixture(self):
        headers = ["factura", "codigo"]
        rows = [("U-SAL-001", "129B02"), ("U-SAL-001", "890701")]
        return _wb(headers, rows), {h: i for i, h in enumerate(headers)}

    def test_check_set_rule_matches_fixture(self):
        """Sala code present but 890601 missing → NOT contains-all → MATCH."""
        wb, indices = self._fixture()
        res = _run("sala_obs_check_set", "urgencias", "obligatorios 890701+890601",
                   self._tree(), wb.active, indices, parametros=self.PARAMS)
        assert len(res) == 1 and res[0]["factura"] == "U-SAL-001"

    def test_dangling_name_reproduces_empty(self):
        wb, indices = self._fixture()
        assert _run(None, "urgencias", "", [], wb.active, indices) == []


# ── Rule-level: duplicados_farmacia_farmacia → duplicados_farmacia ──

class TestDuplicadosFarmaciaMapping:
    """013 seeds duplicados_farmacia (tipo==FARMACIA AND cantidad>1). The
    dangling farmacia-suffixed name exists only in the test DB."""

    def _tree(self):
        nid = _cid_seq()
        root = {"id": nid(), "padre_id": None, "tipo": "composite", "operador": "AND", "orden": 0}
        return [root,
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "eq",
                 "fuente_datos": "invoice.tipo_factura_descripcion", "valor_esperado": "FARMACIA", "orden": 0},
                {"id": nid(), "padre_id": root["id"], "tipo": "atomic", "operador": "gt",
                 "fuente_datos": "invoice.cantidad", "valor_esperado": "1", "orden": 1}]

    def test_duplicados_farmacia_matches_fixture(self):
        headers = ["numero_factura", "tipo_factura_descripcion", "cantidad"]
        wb = _wb(headers, [("F-001", "FARMACIA", 2)])
        indices = {h: i for i, h in enumerate(headers)}
        res = _run("duplicados_farmacia", "urgencias", "farmacia cantidad > 1",
                   self._tree(), wb.active, indices)
        assert len(res) == 1 and res[0]["factura"] == "F-001"

    def test_dangling_name_reproduces_empty(self):
        headers = ["numero_factura", "tipo_factura_descripcion", "cantidad"]
        wb = _wb(headers, [("F-001", "FARMACIA", 2)])
        indices = {h: i for i, h in enumerate(headers)}
        assert _run(None, "urgencias", "", [], wb.active, indices) == []


# ── Wiring: recording RuleBasedDetector fake ──

DANGLING = frozenset({
    "cantidades_anomalas",
    "ide_contrato_equipos_basicos_valido",
    "ide_contrato_simple",
    "ide_contrato_simple_urgencias",
    "pym_rutas_dx",
    "cups_equivalentes_transversal",
    "centro_costo_intramural_valido",
    "bacteriologas_cronograma",
    "duplicado_id_codigo_05",
    "duplicado_id_codigo_02_lab",
    "revision_cantidad_intramural",
    "revision_cantidad_urgencias_valido",
    "sala_observacion_valido",
    "duplicados_farmacia_farmacia",
})


class _RecordingDetector:
    """Fake RuleBasedDetector: records requested names, serves payloads."""

    instances: list[str] = []

    def __init__(self, payloads: dict[str, list[dict]]) -> None:
        self._payloads = payloads

    def __call__(self, name: str, session, **kwargs):
        type(self).instances.append(name)
        m = MagicMock()
        m.detect.return_value = [dict(p) for p in self._payloads.get(name, [])]
        return m

    @classmethod
    def reset(cls) -> None:
        cls.instances = []


def _engine_on():
    old = os.environ.get("USE_RULE_ENGINE")
    os.environ["USE_RULE_ENGINE"] = "true"
    return old


def _engine_restore(old) -> None:
    if old is None:
        os.environ.pop("USE_RULE_ENGINE", None)
    else:
        os.environ["USE_RULE_ENGINE"] = old


class TestEquiposWiring:
    """Equipos detect_all must request the 3 cantidad_* rules + the odonto
    IDE rule, never the dangling names."""

    def test_mapped_names_requested_dangling_never(self):
        from app.services.equipos_basicos.detect_all import detect_all_problems_equipos_basicos

        headers = ["numero_factura", "tipo_procedimiento", "cantidad", "convenio_facturado",
                   "codigo", "codigo_entidad_cobrar", "ide_contrato",
                   "responsable_cierra", "fec_factura"]
        wb = _wb(headers, [("E-001", "Consultas", 2, "Subsidiado",
                             "890203", "ESS118", "000", "Resp", "2024-01-15")])
        indices = {h: i for i, h in enumerate(headers)}
        fake = _RecordingDetector({
            "cantidad_consultas_anomalas": [{"factura": "E-001", "problema": "x"}],
            "ide_contrato_odontologia_valido": [{"factura": "E-001", "problema": "y"}],
        })
        fake.reset()
        old = _engine_on()
        try:
            with (
                patch("app.services.equipos_basicos.detect_all.is_rule_engine_enabled",
                      return_value=True),
                patch("app.services.engine.session_manager.SessionManager") as m_sm,
                patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_rbd,
            ):
                m_sm.return_value.__enter__.return_value = MagicMock()
                m_rbd.side_effect = fake
                resultado, _ = detect_all_problems_equipos_basicos(wb.active, indices)
        finally:
            _engine_restore(old)
        for name in ("cantidad_consultas_anomalas", "cantidad_general_anomalas",
                     "cantidad_pyp_anomalas", "ide_contrato_odontologia_valido"):
            assert name in fake.instances, f"mapped rule {name} not requested: {fake.instances}"
        assert not (set(fake.instances) & DANGLING), (
            f"dangling names still requested: {set(fake.instances) & DANGLING}"
        )
        assert len(resultado["problemas"]["cantidades_anomalas"]) == 1
        assert len(resultado["problemas"]["ide_contrato"]) == 1


class TestUrgenciasWiring:
    """Urgencias detect_all: simple_urgencias removed (covered by the base
    IDE rule — evaluated exactly once), sala + revision renamed."""

    def test_mapped_names_requested_dangling_never(self):
        from app.services.urgencias.detect_all import detect_all_problems_urgencias

        headers = ["numero_factura", "codigo", "procedimiento", "cantidad",
                   "tipo_factura_descripcion", "centro_costo", "codigo_entidad_cobrar",
                   "ide_contrato", "responsable_cierra", "fec_factura",
                   "tarifario", "laboratorio", "tipo_identificacion",
                   "fecha_cierre", "codigo_tipo_procedimiento"]
        wb = _wb(headers, [("U-001", "129B02", "Proc", 2, "Urgencias", "URGENCIAS",
                             "ESS118", "986", "Resp", "2024-01-15",
                             "Subsidiado", "No", "CC",
                             "2024-01-15 16:30:00", "09")])
        indices = {h: i for i, h in enumerate(headers)}
        fake = _RecordingDetector({
            "ide_contrato_urgencias_valido": [{"factura": "U-001", "codigo": "129B02",
                                               "procedimiento": "Proc", "entidad": "ESS118",
                                               "ide_contrato_actual": "986",
                                               "ide_contrato_deberia": "986"}],
            # group-shape item on purpose (no codigo/codigo_equiv keys):
            # the formatter must not crash on engine items.
            "sala_obs_check_set": [{"factura": "U-001", "problema": "sala",
                                    "regla": "#1", "severidad": "error",
                                    "collect_set_codigo": ["129B02", "890701"]}],
            "revision_cantidad_urgencias": [{"factura": "U-001", "problema": "rev"}],
        })
        fake.reset()
        old = _engine_on()
        try:
            with (
                patch("app.services.urgencias.detect_all.is_rule_engine_enabled",
                      return_value=True),
                patch("app.services.engine.session_manager.SessionManager") as m_sm,
                patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_rbd,
            ):
                m_sm.return_value.__enter__.return_value = MagicMock()
                m_rbd.side_effect = fake
                resultado, _ = detect_all_problems_urgencias(wb.active, indices)
        finally:
            _engine_restore(old)
        assert fake.instances.count("ide_contrato_urgencias_valido") == 1, (
            f"base IDE rule must be evaluated exactly once: {fake.instances}"
        )
        for name in ("sala_obs_check_set", "revision_cantidad_urgencias"):
            assert name in fake.instances, f"mapped rule {name} not requested"
        assert not (set(fake.instances) & DANGLING), (
            f"dangling names still requested: {set(fake.instances) & DANGLING}"
        )
        assert len(resultado["problemas"]["ide_contrato"]) == 1
        assert len(resultado["problemas"]["revision_cantidad"]) == 1
        cups = resultado["problemas"]["cups_equivalentes"]
        assert any(i["factura"] == "U-001" for i in cups)


class TestFarmaciaWiring:
    def test_mapped_name_requested_dangling_never(self):
        from app.services.farmacia.detect_all import detect_all_problems_farmacia

        headers = ["numero_factura", "tipo_factura_descripcion", "cantidad",
                   "responsable_cierra", "fec_factura", "fecha_cierre"]
        wb = _wb(headers, [("F-001", "FARMACIA", 2, "Resp", "2024-01-15", "")])
        indices = {h: i for i, h in enumerate(headers)}
        fake = _RecordingDetector({
            "duplicados_farmacia": [{"factura": "F-001", "problema": "dup"}],
        })
        fake.reset()
        old = _engine_on()
        try:
            with (
                patch("app.database.get_session", return_value=MagicMock()),
                patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_rbd,
            ):
                m_rbd.side_effect = fake
                resultado, _ = detect_all_problems_farmacia(wb.active, indices)
        finally:
            _engine_restore(old)
        assert "duplicados_farmacia" in fake.instances
        assert not (set(fake.instances) & DANGLING), (
            f"dangling names still requested: {set(fake.instances) & DANGLING}"
        )
        assert len(resultado["problemas"]["duplicados_farmacia"]) == 1


class TestUnifiedProcessorCupsGap:
    """GAP: no existing rule covers the transversal 906317/906249 mapping
    (seeded cups_equivalentes is the urgencias code set). The engine override
    is explicitly skipped; the legacy result stands (no silent [])."""

    def test_engine_path_keeps_legacy_transversal_result(self):
        from app.services.unified_processor import process_unified

        headers = ["numero_factura", "codigo", "procedimiento", "tipo_factura_descripcion",
                   "responsable_cierra", "fec_factura"]
        wb = _wb(headers, [("T-001", "906317", "Hep B", "Hospitalización", "Resp", "2024-01-15")])
        indices = {h: i for i, h in enumerate(headers)}
        fake = _RecordingDetector({})
        fake.reset()
        old = _engine_on()
        try:
            with (
                patch("app.services.unified_processor.is_rule_engine_enabled",
                      return_value=True),
                patch("app.database.get_session", return_value=MagicMock()),
                patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_rbd,
            ):
                m_rbd.side_effect = fake
                resultado, _ = process_unified(wb.active, indices)
        finally:
            _engine_restore(old)
        assert "cups_equivalentes_transversal" not in fake.instances
        items = resultado["problemas"].get("cups_equivalentes", [])
        assert any(i.get("codigo") == "906317" and i.get("codigo_equiv") == "1906317"
                   for i in items), f"legacy transversal result lost: {items}"


class TestIntramuralGaps:
    """GAPs: bacteriologas / centro_costo / ide_simple / pym_rutas_dx /
    duplicado_05+02_lab / revision_cantidad intramural have no covering rule
    in any DB. Engine evaluation is explicitly skipped ([] + no lookup)."""

    GAP_NAMES = (
        "bacteriologas_cronograma",
        "centro_costo_intramural_valido",
        "ide_contrato_simple",
        "pym_rutas_dx",
        "duplicado_id_codigo_05",
        "duplicado_id_codigo_02_lab",
        "revision_cantidad_intramural",
    )

    def test_gaps_skipped_no_dangling_lookup(self):
        from app.services.intramural.detect_all import detect_all_problems_intramural

        headers = ["numero_factura", "codigo", "cantidad", "tipo_factura_descripcion",
                   "responsable_cierra", "fec_factura", "fecha_cierre"]
        wb = _wb(headers, [("I-001", "890201", 5, "Intramural", "Resp",
                             "2024-01-15", "2024-01-15")])
        indices = {h: i for i, h in enumerate(headers)}
        fake = _RecordingDetector({})
        fake.reset()
        old = _engine_on()
        try:
            with (
                patch("app.database.get_session", return_value=MagicMock()),
                patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_rbd,
            ):
                m_rbd.side_effect = fake
                resultado, _ = detect_all_problems_intramural(wb.active, indices)
        finally:
            _engine_restore(old)
        for name in self.GAP_NAMES:
            assert name not in fake.instances, f"gap rule {name} still evaluated"
        assert resultado["problemas"]["profesionales"] == []
        assert resultado["problemas"]["centros_de_costos"] == []
        assert resultado["problemas"]["duplicado_id_codigo"] == []
        assert resultado["problemas"]["revision_cantidad"] == []
