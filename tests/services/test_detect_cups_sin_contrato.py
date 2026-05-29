"""Tests para app/services/transversales/procedimiento_contratado.py.

STRICT TDD — Test escrito antes que la implementación.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openpyxl import Workbook

from app.services.transversales.normalize import normalize_invoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws(headers: list[str], data_rows: list[list]) -> Workbook.active:
    """Crea una Worksheet con headers en fila 1 y datos desde fila 2."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Datos"
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    for row_idx, row_data in enumerate(data_rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)
    return ws


def _build_indices(headers: list[str]) -> dict[str, int]:
    """Construye índices 0-based desde lista de headers."""
    return {h: i for i, h in enumerate(headers)}


REQUIRED = ["numero_factura", "codigo_entidad_cobrar", "codigo"]


def _mock_eps_instance(cod_contrato: str, eps: str) -> MagicMock:
    ec = MagicMock()
    ec.cod_contrato = cod_contrato
    ec.eps = eps
    return ec


def _mock_proc_instance(cups: str) -> MagicMock:
    p = MagicMock()
    p.cups = cups
    return p


def _make_mock_session(
    pairs: list[tuple[str, str]],
    eps_names: dict[str, str],
) -> MagicMock:
    """Crea un mock de sesión SQLAlchemy que retorna los datos dados.

    Args:
        pairs: Lista de (cod_contrato, cups) — resultados del primer query
        eps_names: Dict {cod_contrato: eps} — resultados del segundo query
    """
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.join.return_value = mock_query

    # First .all() → join results
    join_results = [
        (_mock_eps_instance(cod, eps_names.get(cod, cod)), _mock_proc_instance(cups))
        for cod, cups in pairs
    ]
    # Second .all() → EPS list
    eps_objects = [
        _mock_eps_instance(cod, name) for cod, name in eps_names.items()
    ]

    mock_query.all.side_effect = [join_results, eps_objects]
    mock_session.query.return_value = mock_query
    return mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDetectCupsSinContrato:
    """Tests para detect_cups_sin_contrato."""

    # ── 1. Columnas faltantes ──────────────────────────────────────────────

    def test_missing_numero_factura_returns_empty(self):
        """Cuando falta numero_factura, retorna []."""
        ws = _make_ws(
            headers=["codigo_entidad_cobrar", "codigo"],
            data_rows=[["ESS118", "CUPS001"]],
        )
        indices = _build_indices(["codigo_entidad_cobrar", "codigo"])

        from app.services.transversales.procedimiento_contratado import (
            detect_cups_sin_contrato,
        )
        result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    def test_missing_codigo_entidad_cobrar_returns_empty(self):
        """Cuando falta codigo_entidad_cobrar, retorna []."""
        ws = _make_ws(
            headers=["numero_factura", "codigo"],
            data_rows=[["FAC-001", "CUPS001"]],
        )
        indices = _build_indices(["numero_factura", "codigo"])

        from app.services.transversales.procedimiento_contratado import (
            detect_cups_sin_contrato,
        )
        result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    def test_missing_codigo_returns_empty(self):
        """Cuando falta codigo, retorna []."""
        ws = _make_ws(
            headers=["numero_factura", "codigo_entidad_cobrar"],
            data_rows=[["FAC-001", "ESS118"]],
        )
        indices = _build_indices(["numero_factura", "codigo_entidad_cobrar"])

        from app.services.transversales.procedimiento_contratado import (
            detect_cups_sin_contrato,
        )
        result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 2. DB no disponible ────────────────────────────────────────────────

    def test_db_not_available_returns_empty(self):
        """Cuando SessionLocal lanza excepción, retorna []."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[["FAC-001", "ESS118", "CUPS001"]],
        )
        indices = _build_indices(REQUIRED)

        with patch("app.database.SessionLocal", side_effect=RuntimeError("DB down")):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 3. Happy path: todos contratados ───────────────────────────────────

    def test_happy_path_all_contracted(self):
        """Todos los pares (entidad, CUPS) están contratados → []."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[["FAC-001", "ESS118", "CUPS001"]],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR ESS118"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 4. CUPS no contratado ──────────────────────────────────────────────

    def test_cups_not_contratado_detected(self):
        """CUPS no contratado → error con todos los campos."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[["FAC-001", "ESS118", "CUPS999"]],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR ESS118"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert len(result) == 1
        err = result[0]
        assert err["factura"] == "FAC-001"
        assert err["codigo"] == "CUPS999"
        assert err["codigo_entidad_cobrar"] == "ESS118"
        assert err["entidad"] == "EMSSANAR ESS118"
        assert "CUPS999" in err["problema"]
        assert "ESS118" in err["problema"]

    def test_multiple_rows_some_errors(self):
        """Cuando algunas filas tienen error y otras no, solo errores."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[
                ["FAC-001", "ESS118", "CUPS001"],   # OK
                ["FAC-002", "ESS118", "CUPS999"],   # ERROR
                ["FAC-003", "ESS119", "CUPS003"],   # OK
            ],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001"), ("ESS119", "CUPS003")],
            eps_names={"ESS118": "EMSSANAR", "ESS119": "OTRA EPS"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert len(result) == 1
        assert result[0]["factura"] == "FAC-002"

    # ── 5. Normalización ──────────────────────────────────────────────────

    def test_normalization_case_and_whitespace(self):
        """Normalización: .strip().upper() en ambos códigos."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[["FAC-001", "  ess118  ", "  cups001  "]],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 6. Columna procedimiento opcional ──────────────────────────────────

    def test_includes_procedimiento_when_available(self):
        """Cuando la columna procedimiento existe, se incluye en el error."""
        headers = REQUIRED + ["procedimiento"]
        ws = _make_ws(
            headers=headers,
            data_rows=[["FAC-001", "ESS118", "CUPS999", "PROC-X"]],
        )
        indices = _build_indices(headers)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert len(result) == 1
        assert result[0]["procedimiento"] == "PROC-X"

    # ── 7. Filas sin factura se ignoran ────────────────────────────────────

    def test_empty_invoice_skipped(self):
        """Filas sin número de factura se ignoran silenciosamente."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[
                [None, "ESS118", "CUPS999"],
                ["", "ESS118", "CUPS001"],
            ],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 9. Tarifario farmacia se ignora ─────────────────────────────────────

    def test_tarifario_farmacia_skipped(self):
        """Filas con tarifario=Suminstros, Medicamentos se ignoran."""
        headers = REQUIRED + ["tarifario"]
        ws = _make_ws(
            headers=headers,
            data_rows=[
                # FAC-001 tiene una fila de farmacia y otra normal
                ["FAC-001", "ESS118", "CUPS999", "Suminstros, Medicamentos"],
                ["FAC-001", "ESS118", "CUPS001", "Consultas"],
                # FAC-002 solo tiene farmacia
                ["FAC-002", "ESS118", "CUPS999", "Suminstros, Medicamentos"],
            ],
        )
        indices = _build_indices(headers)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        # Solo la fila normal no contratada debería aparecer
        # FAC-001 fila 1 (farmacia) → skip
        # FAC-001 fila 2 (CUPS001 contratado) → OK
        # FAC-002 (farmacia) → skip
        assert len(result) == 0

    def test_tarifario_farmacia_skip_still_detects_errors(self):
        """Otras filas de la misma factura se siguen procesando."""
        headers = REQUIRED + ["tarifario"]
        ws = _make_ws(
            headers=headers,
            data_rows=[
                ["FAC-001", "ESS118", "CUPS001", "Suminstros, Medicamentos"],
                ["FAC-001", "ESS118", "CUPS999", "Consultas"],
            ],
        )
        indices = _build_indices(headers)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert len(result) == 1
        assert result[0]["codigo"] == "CUPS999"

    def test_unknown_entity_without_data_skipped(self):
        """Entidad sin procedimientos en DB se salta (no se valida)."""
        ws = _make_ws(
            headers=REQUIRED,
            data_rows=[["FAC-001", "UNKNOWN_ENT", "CUPS999"]],
        )
        indices = _build_indices(REQUIRED)
        mock_session = _make_mock_session(
            pairs=[("ESS118", "CUPS001")],
            eps_names={"ESS118": "EMSSANAR"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        assert result == []

    # ── 11. Entidad sin procedimientos en DB se ignora ──────────────────────

    def test_entity_without_procedures_skipped(self):
        """Entidades que no tienen procedimientos cargados se ignoran."""
        headers = REQUIRED
        ws = _make_ws(
            headers=headers,
            data_rows=[
                # ASMET SALUD no tiene procedimientos en DB
                ["FAC-001", "ESS062", "CUPS001"],
                # MALLAMAS sí tiene
                ["FAC-002", "EPSI05", "CUPS999"],
            ],
        )
        indices = _build_indices(headers)
        # Solo MALLAMAS aparece en los resultados del JOIN
        mock_session = _make_mock_session(
            pairs=[("EPSI05", "CUPS001")],
            eps_names={"EPSI05": "MALLAMAS", "ESS062": "ASMET SALUD"},
        )

        with patch("app.database.SessionLocal", return_value=mock_session):
            from app.services.transversales.procedimiento_contratado import (
                detect_cups_sin_contrato,
            )
            result = detect_cups_sin_contrato(ws, indices)

        # FAC-001 (ASMET sin datos) → skip
        # FAC-002 (MALLAMAS, CUPS999 no contratado) → error
        assert len(result) == 1
        assert result[0]["factura"] == "FAC-002"
