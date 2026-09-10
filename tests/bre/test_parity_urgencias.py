"""URG parity harness (Slice 2, strict TDD).

Unified /procesar (process_unified) must match the legacy urgencias
orchestrator on the same fixture: order-insensitive problem-set compare,
IDE/centro-costo paths, missing-column tolerance, exact header matching.
No engine refactor. No prod connection (engine flag OFF / mocked session).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from openpyxl import Workbook

from app.services.transversales.column_indices import get_column_indices

RESP = "Perez Gomez Ana Maria"
CENTRO_URG = "URGENCIAS"
CENTRO_HOSP = "HOSPITALIZACIÓN - ESTANCIA GENERAL"

# Unified enriches each normalized row with tipo_factura; legacy does not.
UNIFIED_ONLY_KEYS = frozenset({"tipo_factura"})

URG_REQUIRED_HEADERS: dict[str, str] = {
    "numero_factura": "Número Factura",
    "identificacion": "Nº Identificación",
    "codigo": "Código",
    "procedimiento": "Procedimiento",
    "cantidad": "Cantidad",
    "vlr_subsidiado": "Vlr. Subsidiado",
    "vlr_procedimiento": "Vlr. Procedimiento",
    "tipo_factura_descripcion": "Tipo Factura Descripción",
    "responsable_cierra": "Responsable Cierra Facturar",
    "centro_costo": "Centro Costo",
    "codigo_tipo_procedimiento": "Código Tipo Procedimiento",
    "codigo_entidad_cobrar": "Cód Entidad Cobrar",
    "ide_contrato": "IDE Contrato",
    "fec_factura": "Fec. Factura",
    "tarifario": "Tarifario",
    "laboratorio": "Laboratorio",
    "tipo_identificacion": "Tipo Identificación",
}


def _build_urg_workbook() -> Workbook:
    """Minimal URG fixture with exact headers (shared style with ODO slice)."""
    wb = Workbook()
    ws = wb.active
    headers = list(URG_REQUIRED_HEADERS.values())
    for col, name in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=name)
    rows = [
        # cantidad violation (890701 qty 2 > 1)
        ("FAC-URG-001", "PAC-101", "890701", "Procedimiento A", 2, 1000, 2000, CENTRO_URG, "986"),
        # centro-costo violation (Urgencias + HOSPITALIZACIÓN)
        ("FAC-URG-002", "PAC-102", "861101", "Procedimiento B", 1, 1000, 2000, CENTRO_HOSP, "986"),
        # IDE violation (906340 + EPSI05 expects 986)
        ("FAC-URG-003", "PAC-103", "906340", "Procedimiento C", 1, 1000, 2000, CENTRO_URG, "000"),
        # clean IDE row (906340 + EPSI05 -> 986)
        ("FAC-URG-004", "PAC-104", "906340", "Procedimiento D", 1, 1000, 2000, CENTRO_URG, "986"),
        # decimales violation (Vlr. Subsidiado 1500.75)
        ("FAC-URG-005", "PAC-105", "890701", "Procedimiento E", 1, 1500.75, 2000, CENTRO_URG, "986"),
    ]
    for r, (fact, pac, cod, proc, cant, vs, vp, centro, ide) in enumerate(rows, start=2):
        ws.cell(row=r, column=1, value=fact)
        ws.cell(row=r, column=2, value=pac)
        ws.cell(row=r, column=3, value=cod)
        ws.cell(row=r, column=4, value=proc)
        ws.cell(row=r, column=5, value=cant)
        ws.cell(row=r, column=6, value=vs)
        ws.cell(row=r, column=7, value=vp)
        ws.cell(row=r, column=8, value="Urgencias")
        ws.cell(row=r, column=9, value=RESP)
        ws.cell(row=r, column=10, value=centro)
        ws.cell(row=r, column=11, value="09")
        ws.cell(row=r, column=12, value="EPSI05")
        ws.cell(row=r, column=13, value=ide)
        ws.cell(row=r, column=14, value="2024-01-15")
        ws.cell(row=r, column=15, value="Subsidiado")
        ws.cell(row=r, column=16, value="No")
        ws.cell(row=r, column=17, value="CC")
    return wb


def _indices(wb: Workbook) -> dict[str, int | None]:
    headers = [wb.active.cell(row=1, column=c).value for c in range(1, wb.active.max_column + 1)]
    indices, _ = get_column_indices(headers, URG_REQUIRED_HEADERS)
    return indices


def _norm_key(row: dict) -> tuple[str, str, str, str]:
    """Order-insensitive problem identity (ignores unified-only enrichment)."""
    return (
        str(row.get("tipo_error", "")),
        str(row.get("factura", "")),
        str(row.get("descripcion", "")),
        str(row.get("procedimiento", "")),
    )


def _forbidden_session(*args, **kwargs):  # pragma: no cover
    raise AssertionError("parity harness must not open a DB connection")


class TestUrgParity:
    def test_unified_matches_legacy_order_insensitive(self) -> None:
        """Engine (flag OFF, no DB) unified output == legacy detect_all."""
        from app.services.unified_processor import process_unified
        from app.services.urgencias.detect_all import detect_all_problems_urgencias

        wb = _build_urg_workbook()
        indices = _indices(wb)
        with (
            patch("app.services.urgencias.detect_all.is_rule_engine_enabled", return_value=False),
            patch("app.services.unified_processor.is_rule_engine_enabled", return_value=False),
            patch("app.database.get_session", _forbidden_session),
        ):
            legacy, _ = detect_all_problems_urgencias(wb.active, indices)
            unified, _ = process_unified(wb.active, indices)
        assert unified["area"] == "unificada"
        assert legacy["area"] == "urgencias"
        assert unified["tipos_procesados"] == ["Urgencias"]
        assert sorted(map(_norm_key, unified["problemas"]["normalizados"])) == sorted(
            map(_norm_key, legacy["problemas"]["normalizados"])
        )

    def test_ide_centro_costo_detector_paths(self) -> None:
        """Legacy IDE/centro-costo detectors flag wrong rows, spare clean row."""
        from app.services.urgencias.centro_costo_urgencias import detect_centro_costo_urgencias
        from app.services.urgencias.ide_contrato_urgencias import detect_ide_contrato_urgencias

        wb = _build_urg_workbook()
        indices = _indices(wb)
        ide = detect_ide_contrato_urgencias(wb.active, indices)
        centros = detect_centro_costo_urgencias(wb.active, indices)
        ide_facturas = {item["factura"] for item in ide}
        centros_facturas = {item["factura"] for item in centros}
        assert "FAC-URG-003" in ide_facturas
        assert "FAC-URG-004" not in ide_facturas
        assert "FAC-URG-002" in centros_facturas

    def test_engine_mocked_ide_centro_parity(self) -> None:
        """Engine ON (mocked RuleBasedDetector): IDE/centro sets match legacy."""
        from app.services.unified_processor import process_unified
        from app.services.urgencias.detect_all import detect_all_problems_urgencias

        wb = _build_urg_workbook()
        indices = _indices(wb)
        centros_payload = [
            {"factura": "FAC-URG-002", "codigo": "861101", "procedimiento": "Procedimiento B",
             "centro_actual": CENTRO_HOSP, "centro_deberia": CENTRO_URG, "prioridad": 2},
        ]
        ide_payload = [
            {"factura": "FAC-URG-003", "codigo": "906340", "entidad": "EPSI05",
             "ide_contrato_actual": "000", "ide_contrato_deberia": "986"},
        ]

        def _mock_detector(name, session, **kwargs):
            detector = MagicMock()
            if name == "centro_costo_urgencias_valido":
                detector.detect.return_value = list(centros_payload)
            elif name == "ide_contrato_urgencias_valido":
                # NOTE: legacy extends ide_contrato_simple_urgencias on top;
                # payload on exactly one rule name keeps normalized sets 1:1.
                detector.detect.return_value = list(ide_payload)
            else:
                detector.detect.return_value = []
            return detector

        with (
            patch("app.services.urgencias.detect_all.is_rule_engine_enabled", return_value=True),
            patch("app.services.unified_processor.is_rule_engine_enabled", return_value=True),
            patch("app.services.engine.session_manager.SessionManager") as mock_session_mgr,
            patch("app.services.engine.rule_based_detector.RuleBasedDetector") as mock_detector_cls,
            patch("app.database.get_session", return_value=MagicMock()),
        ):
            mock_session_mgr.return_value.__enter__.return_value = MagicMock()
            mock_detector_cls.side_effect = _mock_detector
            legacy, _ = detect_all_problems_urgencias(wb.active, indices)
            unified, _ = process_unified(wb.active, indices)
        assert {i["factura"] for i in legacy["problemas"]["ide_contrato"]} == {"FAC-URG-003"}
        assert {i["factura"] for i in unified["problemas"]["ide_contrato"]} == {"FAC-URG-003"}
        assert sorted(map(_norm_key, unified["problemas"]["normalizados"])) == sorted(
            map(_norm_key, legacy["problemas"]["normalizados"])
        )

    def test_missing_column_tolerance(self) -> None:
        """Fixture without Cantidad/IDE: affected detectors return [], never raise."""
        from app.services.unified_processor import process_unified
        from app.services.urgencias.cantidades_urgencias import detect_cantidades_urgencias
        from app.services.urgencias.detect_all import detect_all_problems_urgencias
        from app.services.urgencias.ide_contrato_urgencias import detect_ide_contrato_urgencias

        wb = _build_urg_workbook()
        indices = _indices(wb)
        indices["cantidad"] = None
        indices["ide_contrato"] = None
        with (
            patch("app.services.urgencias.detect_all.is_rule_engine_enabled", return_value=False),
            patch("app.services.unified_processor.is_rule_engine_enabled", return_value=False),
            patch("app.database.get_session", _forbidden_session),
        ):
            assert detect_cantidades_urgencias(wb.active, indices) == []
            assert detect_ide_contrato_urgencias(wb.active, indices) == []
            legacy, _ = detect_all_problems_urgencias(wb.active, indices)
            unified, _ = process_unified(wb.active, indices)
        assert legacy["problemas"]["cantidades_urgencias"] == []
        assert sorted(map(_norm_key, unified["problemas"]["normalizados"])) == sorted(
            map(_norm_key, legacy["problemas"]["normalizados"])
        )

    def test_exact_header_matching(self) -> None:
        """Near-miss 'Codigo' must NOT map; exact 'Código' must map."""
        required = {"codigo": "Código"}
        indices, missing = get_column_indices(["Codigo", "Número Factura"], required)
        assert indices["codigo"] is None
        assert "Código" in missing
        indices, missing = get_column_indices(["Código", "Número Factura"], required)
        assert indices["codigo"] == 0
        assert missing == []


# ── Detallado parity (Strict TDD RED — oracle builders land in GREEN) ──

DETALLADO_HEADERS: dict[str, str] = {
    "numero_factura": "Número Factura",
    "codigo_tipo_procedimiento": "Código Tipo Procedimiento",
    "codigo": "Código",
    "laboratorio": "Laboratorio",
    "centro_costo": "Centro Costo",
    "codigo_entidad_cobrar": "Cód Entidad Cobrar",
    "tipo_factura_descripcion": "Tipo Factura Descripción",
    "procedimiento": "Procedimiento",
    "tarifario": "Tarifario",
    "tipo_identificacion": "Tipo Identificación",
}

LAB = "APOYO DIAGNOSTICO-LABORATOR CLINICO"
DIAG = "APOYO DIAGNOSTICO-IMAGENOLOGIA"
FARM = "APOYO TERAPEUTICO-FARMACIA E INSUMOS."
PYP = "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"
QUIR = "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"
HOSP = "HOSPITALIZACIÓN - ESTANCIA GENERAL"
FARM_TAR = "Suminstros, Medicamentos"

# 17 branches + 2 negatives. Each row: (factura, cod_tipo, codigo, lab, centro,
# entidad, tipo_factura, tarifario, tipo_id). All centros valid (valido-rule
# scope excluded); exact spellings (eq has no strip fallback).
DETALLADO_FIXTURES: list[tuple] = [
    ("FAC-D-01", "01", "890601", "No", "URGENCIAS", "EPSI05", "Urgencias", FARM_TAR, "CC"),  # R9
    ("FAC-D-02", "02", "890601", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # R1
    ("FAC-D-03", "01", "890601", "No", DIAG, "EPSI05", "Urgencias", "Subsidiado", "CC"),  # REV1
    ("FAC-D-04", "14", "890601", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # R2
    ("FAC-D-05", "02", "903883", "No", "TRASLADOS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # REV2
    ("FAC-D-06", "01", "990211", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # R3
    ("FAC-D-07", "01", "735301", "No", PYP, "EPSI05", "Urgencias", "Subsidiado", "CC"),  # REV3
    ("FAC-D-08", "01", "735301", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # R4
    ("FAC-D-09", "01", "990211", "No", QUIR, "EPSI05", "Urgencias", "Subsidiado", "CC"),  # REV4
    ("FAC-D-10", "09", "906340", "No", "URGENCIAS", "ESS118", "Intramural", "Subsidiado", "CC"),  # R5
    ("FAC-D-11", "09", "906340", "No", LAB, "EPSI05", "Urgencias", "Subsidiado", "CC"),  # REV5
    ("FAC-D-12", "01", "890601", "No", FARM, "EPSI05", "Urgencias", "SOAT", "CC"),  # REV9
    ("FAC-D-13", "01", "890601H", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # R8
    ("FAC-D-14", "09", "890601", "No", "URGENCIAS", "EPSI05", "Intramural", "Subsidiado", "CC"),  # INTRA
    ("FAC-D-15", "01", "890601", "No", "URGENCIAS", "EPSI05", "Ambulatoria", "Subsidiado", "CC"),  # AMB
    ("FAC-D-16", "01", "890601", "No", "URGENCIAS", "EPSI05", "Hospitalización", "Subsidiado", "CC"),  # X1
    ("FAC-D-17", "01", "890601", "No", HOSP, "EPSI05", "Urgencias", "Subsidiado", "CC"),  # X2
    ("FAC-D-18", "01", "890601", "No", "URGENCIAS", "EPSI05", "Urgencias", "Subsidiado", "CC"),  # NEG
    ("FAC-D-19", "09", "904902", "No", LAB, "EPSI05", "Intramural", "Subsidiado", "CN"),  # NEG CN
]

BRANCH_FACTURAS = frozenset(f"FAC-D-{i:02d}" for i in range(1, 18))


def _load_tree_oracle():
    """Load test_centro_costo_tree.py by path (RED: builders missing → fail)."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "engine" / "test_centro_costo_tree.py"
    spec = importlib.util.spec_from_file_location("tct_oracle", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_detallado_workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    for col, name in enumerate(DETALLADO_HEADERS.values(), start=1):
        ws.cell(row=1, column=col, value=name)
    for r, (fact, ct, cod, lab, centro, ent, tipo, tar, tid) in enumerate(DETALLADO_FIXTURES, start=2):
        ws.cell(row=r, column=1, value=fact)
        ws.cell(row=r, column=2, value=ct)
        ws.cell(row=r, column=3, value=cod)
        ws.cell(row=r, column=4, value=lab)
        ws.cell(row=r, column=5, value=centro)
        ws.cell(row=r, column=6, value=ent)
        ws.cell(row=r, column=7, value=tipo)
        ws.cell(row=r, column=8, value=f"Proc {fact}")
        ws.cell(row=r, column=9, value=tar)
        ws.cell(row=r, column=10, value=tid)
    return wb


class TestUrgenciasDetalladoParity:
    def test_legacy_vs_engine_snapshot_diff_empty(self) -> None:
        """Legacy detector fire-set == (p1 or p2) tree fire-set over 17 branches."""
        from app.services.urgencias.centro_costo_urgencias import detect_centro_costo_urgencias

        oracle = _load_tree_oracle()
        wb = _build_detallado_workbook()
        headers = [wb.active.cell(row=1, column=c).value for c in range(1, wb.active.max_column + 1)]
        indices, _ = get_column_indices(headers, DETALLADO_HEADERS)

        legacy = detect_centro_costo_urgencias(wb.active, indices)
        legacy_fired = {item["factura"] for item in legacy}

        tree_fired: set[str] = set()
        for (fact, ct, cod, lab, centro, ent, tipo, tar, tid) in DETALLADO_FIXTURES:
            row = {
                "codigo_tipo_procedimiento": ct, "codigo": cod, "laboratorio": lab,
                "centro_costo": centro, "codigo_entidad_cobrar": ent,
                "tipo_factura_descripcion": tipo, "tarifario": tar,
                "tipo_identificacion": tid,
            }
            p1 = oracle._run_tree(oracle._build_urgencias_detallado_tree(), row)
            p2 = oracle._run_tree(oracle._build_urgencias_cross_tree(), row)
            if p1 or p2:
                tree_fired.add(fact)

        assert BRANCH_FACTURAS <= legacy_fired, f"fixtures must fire legacy: {BRANCH_FACTURAS - legacy_fired}"
        assert tree_fired == legacy_fired, f"parity diff: legacy-only={legacy_fired - tree_fired} tree-only={tree_fired - legacy_fired}"
