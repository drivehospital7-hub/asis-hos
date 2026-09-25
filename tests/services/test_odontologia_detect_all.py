"""Tests for engine path in odontologia/detect_all.py.

NOTE: the legacy/OFF path was removed by design (is_rule_engine_enabled()
returns True hard-coded — "Engine always on"). Tests mocking engine OFF
were deleted; only engine-ON tests remain.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from openpyxl import Workbook

from app.constants import CONVENIO_PYP
from app.services.odontologia.detect_all import detect_all_problems_odontologia


@pytest.fixture
def workbook_minimal() -> Workbook:
    """Crea un workbook con headers mínimos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws.cell(row=1, column=1, value="Número Factura")
    return wb


class TestDetectAllProblemsOdontologia:
    """Tests para detect_all_problems_odontologia."""

    # NOTE: legacy/OFF path removed — engine is always on, so tests mocking
    # is_rule_engine_enabled → False were deleted (no OFF branch exists).








    def test_ruta_duplicada_excluye_3_facturas_con_codigo_exento(
        self, workbook_minimal: Workbook
    ) -> None:
        """LEGACY OFF (2026-09-09, usuario eligió "Actualizar tests"): el
        post-filtro ruta-dup 3-facturas está ANULADO — el engine retorna los
        hallazgos sin filtrar (PAC-001 y PAC-002 reportados).

        TODO(engine): modelar esta excepción como rule/filtro engine y
        reactivar en app/services/odontologia/detect_all.py.
        Revertir con git revert. Ver comentario LEGACY OFF en detect_all.py.
        """
        ws = workbook_minimal.active
        ws.cell(row=1, column=1, value="Número Factura")
        ws.cell(row=1, column=2, value="Nº Identificación")
        ws.cell(row=1, column=3, value="Convenio Facturado")
        ws.cell(row=1, column=4, value="Código")

        ws.cell(row=2, column=1, value="FAC-001")
        ws.cell(row=2, column=2, value="PAC-001")
        ws.cell(row=2, column=3, value=CONVENIO_PYP)
        ws.cell(row=2, column=4, value="990203")
        ws.cell(row=3, column=1, value="FAC-002")
        ws.cell(row=3, column=2, value="PAC-001")
        ws.cell(row=3, column=3, value=CONVENIO_PYP)
        ws.cell(row=3, column=4, value="997002")
        ws.cell(row=4, column=1, value="FAC-003")
        ws.cell(row=4, column=2, value="PAC-001")
        ws.cell(row=4, column=3, value=CONVENIO_PYP)
        ws.cell(row=4, column=4, value="997106")
        ws.cell(row=5, column=1, value="FAC-004")
        ws.cell(row=5, column=2, value="PAC-002")
        ws.cell(row=5, column=3, value=CONVENIO_PYP)
        ws.cell(row=5, column=4, value="997002")
        ws.cell(row=6, column=1, value="FAC-005")
        ws.cell(row=6, column=2, value="PAC-002")
        ws.cell(row=6, column=3, value=CONVENIO_PYP)
        ws.cell(row=6, column=4, value="997106")
        ws.cell(row=7, column=1, value="FAC-006")
        ws.cell(row=7, column=2, value="PAC-002")
        ws.cell(row=7, column=3, value=CONVENIO_PYP)
        ws.cell(row=7, column=4, value="997301")

        indices = {
            "numero_factura": 0,
            "identificacion": 1,
            "convenio_facturado": 2,
            "codigo": 3,
            "codigo_equiv": None,
            "tipo_procedimiento": None,
            "codigo_tipo_procedimiento": None,
            "procedimiento": None,
            "centro_costo": None,
            "codigo_entidad_cobrar": None,
            "entidad_cobrar": None,
            "entidad_afiliacion": None,
            "fec_nacimiento": None,
            "fec_factura": None,
            "fecha_cierre": None,
            "profesional_identificacion": None,
            "profesional_atiende": None,
            "codigo_profesional": None,
            "responsable_cierra": None,
            "vlr_subsidiado": None,
            "vlr_procedimiento": None,
            "laboratorio": None,
            "tarifario": None,
            "tipo_factura_descripcion": None,
            "ide_contrato": None,
            "tipo_identificacion": None,
            "tipo_usuario": None,
            "vlr_copago": None,
            "numero_reingreso": None,
            "codigo_dx_principal": None,
            "cantidad": None,
        }
        # Mock RuleBasedDetector to let engine return ruta_dup data
        from unittest.mock import MagicMock

        from app.models import Regla

        fake_resolver = MagicMock()
        fake_resolver.resolve.return_value = [
            Regla(
                id=1, nombre="ruta_duplicada", dominio="odontologia",
                estado="active", version=1, prioridad=10, severidad="error",
                activo=True, grupo_error="Ruta Duplicada",
            )
        ]

        def _mock_detector(name, session, **kwargs):
            d = MagicMock()
            if name == "ruta_duplicada":
                # Return data matching the PAC-001/PAC-002 setup
                d.detect.return_value = [
                    {"identificacion": "PAC-001", "factura": "FAC-001",
                     "cantidad": 3, "codigo": "990203"},
                    {"identificacion": "PAC-001", "factura": "FAC-002",
                     "cantidad": 3, "codigo": "997002"},
                    {"identificacion": "PAC-001", "factura": "FAC-003",
                     "cantidad": 3, "codigo": "997106"},
                    {"identificacion": "PAC-002", "factura": "FAC-004",
                     "cantidad": 3, "codigo": "997002"},
                    {"identificacion": "PAC-002", "factura": "FAC-005",
                     "cantidad": 3, "codigo": "997106"},
                    {"identificacion": "PAC-002", "factura": "FAC-006",
                     "cantidad": 3, "codigo": "997301"},
                ]
            else:
                d.detect.return_value = []
            return d

        with patch("app.database.get_session") as m_gs:
            with patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_dc:
                m_gs.return_value = MagicMock()
                m_dc.side_effect = _mock_detector
                with patch(
                    "app.services.engine.domain_detection.RuleResolver",
                    return_value=fake_resolver,
                ):
                    result, _ = detect_all_problems_odontologia(ws, indices)

        ruta_dup = result["problemas"]["ruta_duplicada"]
        identificaciones = [r["identificacion"] for r in ruta_dup]

        # LEGACY OFF: /procesar usa solo engine, sin post-filtro PAC-001 se reporta.
        assert "PAC-001" in identificaciones, (
            "LEGACY OFF: sin post-filtro ruta-dup, PAC-001 debe reportarse"
        )
        assert "PAC-002" in identificaciones, (
            "PAC-002 tiene 3 facturas sin código exento => debe reportarse"
        )

    def test_ruta_duplicada_no_excluye_4_facturas_con_codigo_exento(
        self, workbook_minimal: Workbook
    ) -> None:
        """4+ facturas PyP se reportan aunque tengan códigos exentos."""
        ws = workbook_minimal.active
        ws.cell(row=1, column=1, value="Número Factura")
        ws.cell(row=1, column=2, value="Nº Identificación")
        ws.cell(row=1, column=3, value="Convenio Facturado")
        ws.cell(row=1, column=4, value="Código")

        ws.cell(row=2, column=1, value="FAC-001")
        ws.cell(row=2, column=2, value="PAC-001")
        ws.cell(row=2, column=3, value=CONVENIO_PYP)
        ws.cell(row=2, column=4, value="990203")
        ws.cell(row=3, column=1, value="FAC-002")
        ws.cell(row=3, column=2, value="PAC-001")
        ws.cell(row=3, column=3, value=CONVENIO_PYP)
        ws.cell(row=3, column=4, value="997002")
        ws.cell(row=4, column=1, value="FAC-003")
        ws.cell(row=4, column=2, value="PAC-001")
        ws.cell(row=4, column=3, value=CONVENIO_PYP)
        ws.cell(row=4, column=4, value="997106")
        ws.cell(row=5, column=1, value="FAC-004")
        ws.cell(row=5, column=2, value="PAC-001")
        ws.cell(row=5, column=3, value=CONVENIO_PYP)
        ws.cell(row=5, column=4, value="997301")

        indices = {
            "numero_factura": 0,
            "identificacion": 1,
            "convenio_facturado": 2,
            "codigo": 3,
            "codigo_equiv": None,
            "tipo_procedimiento": None,
            "codigo_tipo_procedimiento": None,
            "procedimiento": None,
            "centro_costo": None,
            "codigo_entidad_cobrar": None,
            "entidad_cobrar": None,
            "entidad_afiliacion": None,
            "fec_nacimiento": None,
            "fec_factura": None,
            "fecha_cierre": None,
            "profesional_identificacion": None,
            "profesional_atiende": None,
            "codigo_profesional": None,
            "responsable_cierra": None,
            "vlr_subsidiado": None,
            "vlr_procedimiento": None,
            "laboratorio": None,
            "tarifario": None,
            "tipo_factura_descripcion": None,
            "ide_contrato": None,
            "tipo_identificacion": None,
            "tipo_usuario": None,
            "vlr_copago": None,
            "numero_reingreso": None,
            "codigo_dx_principal": None,
            "cantidad": None,
        }
        from unittest.mock import MagicMock

        from app.models import Regla

        fake_resolver = MagicMock()
        fake_resolver.resolve.return_value = [
            Regla(
                id=1, nombre="ruta_duplicada", dominio="odontologia",
                estado="active", version=1, prioridad=10, severidad="error",
                activo=True, grupo_error="Ruta Duplicada",
            )
        ]

        def _mock_detector(name, session, **kwargs):
            d = MagicMock()
            if name == "ruta_duplicada":
                d.detect.return_value = [
                    {"identificacion": "PAC-001", "factura": "FAC-001",
                     "cantidad": 4, "codigo": "990203"},
                    {"identificacion": "PAC-001", "factura": "FAC-002",
                     "cantidad": 4, "codigo": "997002"},
                    {"identificacion": "PAC-001", "factura": "FAC-003",
                     "cantidad": 4, "codigo": "997106"},
                    {"identificacion": "PAC-001", "factura": "FAC-004",
                     "cantidad": 4, "codigo": "997301"},
                ]
            else:
                d.detect.return_value = []
            return d

        with patch("app.database.get_session") as m_gs:
            with patch("app.services.engine.rule_based_detector.RuleBasedDetector") as m_dc:
                m_gs.return_value = MagicMock()
                m_dc.side_effect = _mock_detector
                with patch(
                    "app.services.engine.domain_detection.RuleResolver",
                    return_value=fake_resolver,
                ):
                    result, _ = detect_all_problems_odontologia(ws, indices)

        ruta_dup = result["problemas"]["ruta_duplicada"]
        identificaciones = [r["identificacion"] for r in ruta_dup]

        assert "PAC-001" in identificaciones, (
            "PAC-001 tiene 4 facturas aunque con código exento => debe reportarse"
        )
