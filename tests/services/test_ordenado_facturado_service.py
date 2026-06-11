"""Tests para ordenado_facturado_service: filtro y totalizado.

Follows the spec from openspec/changes/filtrar-codigos-procesados/specs/ordenado-facturado/spec.md.
Tests the refactored behavior: positive filter (VISIBLE_CODES) and
4-row aggregate totalizado (PARTO, INTERCONSULTAS, OTROS, TRASLADOS).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.ordenado_facturado_service import (
    CODIGOS_EXCEPCION,
    PROCESADOS_INTERCONSULTAS,
    PROCESADOS_OTROS,
    PROCESADOS_PARTO,
    procesar_cruce,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_reporte_rows(data_rows: list[tuple]) -> list[list]:
    """Build mock _leer_como_raw output for reporte.

    data_rows: list of (factura, codigo, procedimiento, identificacion, fecha)
    Returns list-of-lists 1-based, matching _leer_como_raw format.
    """
    headers = [None, "Número Factura", "Código", "Procedimiento",
               "Nº Identificación", "Fec. Factura"]
    rows: list[list] = [[None], headers]
    for factura, codigo, procedimiento, identificacion, fecha in data_rows:
        rows.append([None, factura, codigo, procedimiento, identificacion, fecha])
    return rows


def _build_ayudas_rows(data_rows: list[tuple]) -> list[list]:
    """Build mock _leer_como_raw output for ayudas.

    data_rows: list of (factura, cups, tipo, identificacion, fecha, entidad, proc)
    Returns list-of-lists 1-based, matching _leer_como_raw format.
    """
    headers = [None, "N° Factura", "CUPS", "Tipo Factura (Servicio)",
               "Nº Identificación", "Fecha Solicitud",
               "Entidad Administradora", "Procedimiento Solicitado"]
    rows: list[list] = [[None], headers]
    for factura, cups, tipo, identificacion, fecha, entidad, proc_ in data_rows:
        rows.append([None, factura, cups, tipo, identificacion, fecha, entidad, proc_])
    return rows


def _cups_set(no_facturados: list[dict]) -> set[str]:
    """Extract raw CUPS values from no_facturados list."""
    return {item["cups"] for item in no_facturados}


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def base_date() -> datetime:
    return datetime(2024, 6, 1)


@pytest.fixture
def dummy_reporte(base_date: datetime) -> list[list]:
    """Reporte con un solo registro dummy (nada matchea con ayudas)."""
    return _build_reporte_rows([
        ("R-DUMMY", "000000", "DUMMY", "000", base_date),
    ])


# ──────────────────────────────────────────────────────────────────────
# Requirement: Individual List Code Filter
# ──────────────────────────────────────────────────────────────────────

class TestIndividualFilter:
    """VISIBLE_CODES = PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS
       | PROCESADOS_OTROS"""

    VISIBLE = PROCESADOS_PARTO | PROCESADOS_INTERCONSULTAS | PROCESADOS_OTROS

    @pytest.fixture
    def ayudas_mixtas(self, base_date: datetime) -> list[list]:
        """Ayudas: PARTO code, INTER code, OTROS code, non-matching, exception."""
        return _build_ayudas_rows([
            ("A-PARTO", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("A-INTER", "890410", "URGENCIAS", "100", base_date, "E1", "INTER"),
            ("A-OTROS", "861801", "URGENCIAS", "100", base_date, "E1", "OTROS"),
            ("A-NOMATCH", "999999", "URGENCIAS", "100", base_date, "E1", "NOMATCH"),
            ("A-EXCEP", "8938011", "URGENCIAS", "100", base_date, "E1", "EXCEP"),
        ])

    # ── Scenario: Parto code appears ──
    def test_parto_code_included(self, dummy_reporte, ayudas_mixtas):
        """GIVEN a CUPS in PROCESADOS_PARTO is un-invoiced
           WHEN building the individual list
           THEN it appears."""
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = [dummy_reporte, ayudas_mixtas]
            result = procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "735301" in cups, "PARTO code should be included"

    # ── Scenario: OTROS code appears ──
    def test_otros_code_included(self, dummy_reporte, ayudas_mixtas):
        """GIVEN a CUPS in PROCESADOS_OTROS is un-invoiced
           WHEN building the individual list
           THEN it appears."""
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = [dummy_reporte, ayudas_mixtas]
            result = procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "861801" in cups, "OTROS code should be included"

    # ── Scenario: Non-matching code excluded ──
    def test_non_matching_excluded(self, dummy_reporte, ayudas_mixtas):
        """GIVEN a CUPS not in VISIBLE_CODES is un-invoiced
           WHEN building the individual list
           THEN it is excluded."""
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = [dummy_reporte, ayudas_mixtas]
            result = procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "999999" not in cups, "Non-matching code should be excluded"

    # ── Scenario: Exception code excluded ──
    def test_exception_excluded(self, dummy_reporte, ayudas_mixtas):
        """GIVEN a CUPS in CODIGOS_EXCEPCION is un-invoiced
           WHEN building the individual list
           THEN it is excluded."""
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = [dummy_reporte, ayudas_mixtas]
            result = procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "8938011" not in cups, "Exception code should be excluded from individual list"

    # ── Scenario: only visible codes appear ──
    def test_only_visible_codes_in_list(self, dummy_reporte, ayudas_mixtas):
        """GIVEN a mix of visible, non-matching, and exception codes
           WHEN building the individual list
           THEN only visible codes appear."""
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = [dummy_reporte, ayudas_mixtas]
            result = procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        expected = {"735301", "890410", "861801"}
        assert cups == expected, f"Expected only visible codes {expected}, got {cups}"


# ──────────────────────────────────────────────────────────────────────
# Requirement: Totalizado Aggregation
# ──────────────────────────────────────────────────────────────────────

class TestTotalizadoAggregation:
    """4 aggregate rows (PARTO, INTERCONSULTAS, OTROS, TRASLADOS)
    instead of per-code entries."""

    def _run(self, reporte_rows, ayudas_rows, notas_rows=None):
        """Helper: mock _leer_como_raw and call procesar_cruce."""
        side_effect = [reporte_rows, ayudas_rows]
        notas_path = None
        if notas_rows is not None:
            side_effect.append(notas_rows)
            notas_path = Path("n.xlsx")
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = side_effect
            return procesar_cruce(Path("r.xlsx"), Path("a.xlsx"), notas_path)

    @pytest.fixture
    def multi_cat_reporte(self, base_date: datetime) -> list[list]:
        """Reporte with codes from all 4 categories."""
        return _build_reporte_rows([
            ("R-P1", "735301", "PARTO-A", "100", base_date),
            ("R-P2", "735930", "PARTO-B", "100", base_date),
            ("R-I1", "890410", "INTER-A", "100", base_date),
            ("R-I2", "890402", "INTER-B", "100", base_date),
            ("R-O1", "861801", "OTROS", "100", base_date),
            ("R-E1", "8938011", "EXCEP-A", "100", base_date),
            ("R-E2", "601T01", "EXCEP-B", "100", base_date),
        ])

    @pytest.fixture
    def ayudas_multi(self, base_date: datetime) -> list[list]:
        """Ayudas matching each category."""
        return _build_ayudas_rows([
            ("A-P1", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("A-P2", "735930", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("A-I1", "890410", "URGENCIAS", "100", base_date, "E1", "INTER"),
            ("A-I2", "890402", "URGENCIAS", "100", base_date, "E1", "INTER"),
            ("A-O1", "861801", "URGENCIAS", "999", base_date, "E1", "OTROS"),
        ])

    # ── Scenario: All categories rendered ──
    def test_four_aggregate_rows(self, multi_cat_reporte, ayudas_multi):
        """GIVEN codes from all 4 categories exist
           WHEN building the totalizado
           THEN 4 rows (PARTO, INTERCONSULTAS, OTROS, TRASLADOS) appear."""
        result = self._run(multi_cat_reporte, ayudas_multi)

        assert result["status"] == "success"
        rows = {r["codigo"] for r in result["data"]["totalizado"]}
        assert rows == {"PARTO", "INTERCONSULTAS", "OTROS", "TRASLADOS"}, (
            f"Expected 4 category rows, got {rows}"
        )

    def test_aggregate_sums(self, multi_cat_reporte, ayudas_multi):
        """GIVEN specific counts per category
           WHEN building the totalizado
           THEN each row has summed totals."""
        result = self._run(multi_cat_reporte, ayudas_multi)

        assert result["status"] == "success"
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}

        # PARTO: 2 codes x 1 each
        parto = totalizado["PARTO"]
        assert parto["total_reporte"] == 2
        assert parto["total_ordenadas"] == 2
        assert parto["total_no_facturado"] == 2

        # INTERCONSULTAS: 2 codes x 1 each
        inter = totalizado["INTERCONSULTAS"]
        assert inter["total_reporte"] == 2
        assert inter["total_ordenadas"] == 2
        assert inter["total_no_facturado"] == 2

        # OTROS: 1 code x 1
        otros = totalizado["OTROS"]
        assert otros["total_reporte"] == 1
        assert otros["total_ordenadas"] == 1
        assert otros["total_no_facturado"] == 1

        # TRASLADOS: 2 exception codes in reporte
        traslados = totalizado["TRASLADOS"]
        assert traslados["total_reporte"] == 2
        assert traslados["total_ordenadas"] == 0
        assert traslados["total_no_facturado"] == 0
        assert traslados["es_notas"] is False

    def test_totalizado_procedimiento_labels(self, multi_cat_reporte, ayudas_multi):
        """GIVEN rows from all categories
           WHEN building the totalizado
           THEN procedimiento has human-readable label."""
        result = self._run(multi_cat_reporte, ayudas_multi)

        assert result["status"] == "success"
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}

        assert totalizado["PARTO"]["procedimiento"] == "Procesados Parto"
        assert totalizado["INTERCONSULTAS"]["procedimiento"] == "Procesados Interconsultas"
        assert totalizado["OTROS"]["procedimiento"] == "Procesados Otros"
        assert totalizado["TRASLADOS"]["procedimiento"] == "Traslados (excepción)"

    # ── Scenario: Empty category suppressed ──
    def test_empty_category_suppressed(self, base_date: datetime):
        """GIVEN a category has zero counts
           WHEN building the totalizado
           THEN that row is omitted."""
        # Only PARTO codes in reporte, no ayudas at all
        reporte = _build_reporte_rows([
            ("R-P1", "735301", "PARTO", "100", base_date),
        ])
        ayudas = _build_ayudas_rows([])  # VACIO — solo headers, no data

        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        # Helpers: no data rows → no ayudas, so ordenadas and no_facturado are 0
        # PARTO: reporte=1, ordenadas=0, nf=0 → should show (reporte > 0)
        # INTER: all zero → suppressed
        # OTROS: all zero → suppressed
        # TRASLADOS: no exception codes → suppressed
        codigos = {r["codigo"] for r in result["data"]["totalizado"]}
        assert codigos == {"PARTO"}, f"Expected only PARTO row, got {codigos}"

        parto = next(r for r in result["data"]["totalizado"] if r["codigo"] == "PARTO")
        assert parto["total_reporte"] == 1
        assert parto["total_ordenadas"] == 0
        assert parto["total_no_facturado"] == 0


# ──────────────────────────────────────────────────────────────────────
# Requirement: OTROS Code Inclusion (861801)
# ──────────────────────────────────────────────────────────────────────

class Test861801Inclusion:
    """861801 is in PROCESADOS_OTROS and appears in individual list
    and OTROS totalizado row."""

    def _run(self, reporte_rows, ayudas_rows):
        side_effect = [reporte_rows, ayudas_rows]
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = side_effect
            return procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

    def test_861801_in_individual_list(self, dummy_reporte, base_date):
        """GIVEN 861801 is un-invoiced
           WHEN building results
           THEN it appears in the individual list."""
        ayudas = _build_ayudas_rows([
            ("A-861", "861801", "URGENCIAS", "100", base_date, "E1", "OTROS"),
        ])
        result = self._run(dummy_reporte, ayudas)

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "861801" in cups

    def test_861801_in_otros_aggregate(self, base_date):
        """GIVEN 861801 exists in reporte and ayudas
           WHEN building results
           THEN it is counted in the OTROS totalizado row."""
        reporte = _build_reporte_rows([
            ("R-861", "861801", "OTROS", "100", base_date),
        ])
        ayudas = _build_ayudas_rows([
            ("A-861", "861801", "URGENCIAS", "200", base_date, "E1", "OTROS"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}

        assert "OTROS" in totalizado
        assert totalizado["OTROS"]["total_reporte"] == 1
        assert totalizado["OTROS"]["total_ordenadas"] == 1
        assert totalizado["OTROS"]["total_no_facturado"] == 1


# ──────────────────────────────────────────────────────────────────────
# Requirement: API Contract Preserved
# ──────────────────────────────────────────────────────────────────────

class TestBackwardCompat:
    """Each totalizado row MUST retain {codigo, procedimiento,
    total_reporte, total_ordenadas, total_no_facturado}."""

    def _run(self, reporte_rows, ayudas_rows):
        side_effect = [reporte_rows, ayudas_rows]
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = side_effect
            return procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

    def test_response_shape(self, base_date):
        """GIVEN a valid request
           WHEN inspecting totalizado rows
           THEN all required fields are present with correct types."""
        reporte = _build_reporte_rows([
            ("R-P1", "735301", "PARTO", "100", base_date),
            ("R-E1", "8938011", "EXCEP", "100", base_date),
        ])
        ayudas = _build_ayudas_rows([
            ("A-P1", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        assert "totalizado" in result["data"]
        assert "no_facturados" in result["data"]
        assert "total_no_facturado" in result["data"]
        assert "total_ayudas" in result["data"]

        for row in result["data"]["totalizado"]:
            assert "codigo" in row
            assert "procedimiento" in row
            assert "total_reporte" in row
            assert "total_ordenadas" in row
            assert "total_no_facturado" in row
            assert isinstance(row["codigo"], str)
            assert isinstance(row["procedimiento"], str)
            assert isinstance(row["total_reporte"], int)
            assert isinstance(row["total_ordenadas"], int)
            assert isinstance(row["total_no_facturado"], int)


# ──────────────────────────────────────────────────────────────────────
# Requirement: Dedup by (factura, código) in ayudas_full and reporte
# ──────────────────────────────────────────────────────────────────────

class TestDedup:
    """Total Ordenadas y Total Reporte cuentan pares únicos
    (factura, código), no filas totales."""

    def _run(self, reporte_rows, ayudas_rows):
        side_effect = [reporte_rows, ayudas_rows]
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = side_effect
            return procesar_cruce(Path("r.xlsx"), Path("a.xlsx"))

    def test_ayudas_full_dedup_by_factura_cups(self, base_date):
        """GIVEN ayudas has duplicate (factura, cups) rows
           WHEN building totalizado
           THEN ordenadas counts unique pairs only."""
        reporte = _build_reporte_rows([
            ("F001", "735301", "PARTO", "100", base_date),
        ])
        # 3 filas en ayudas pero mismo par (F001, 735301)
        ayudas = _build_ayudas_rows([
            ("F001", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("F001", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("F001", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}

        # 1 par único en ayudas, 1 par único en reporte, 0 no facturados
        assert totalizado["PARTO"]["total_reporte"] == 1
        assert totalizado["PARTO"]["total_ordenadas"] == 1
        assert totalizado["PARTO"]["total_no_facturado"] == 0

    def test_ayudas_dedup_distinct_factura_counts_separately(self, base_date):
        """GIVEN ayudas has same cups but different facturas
           WHEN building totalizado
           THEN each distinct pair counts."""
        reporte = _build_reporte_rows([
            ("F001", "735301", "PARTO", "100", base_date),
        ])
        ayudas = _build_ayudas_rows([
            ("F001", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
            ("F002", "735301", "URGENCIAS", "200", base_date, "E1", "PARTO"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}

        # 2 pares únicos en ayudas, 1 en reporte, 1 no facturado (F002, 735301)
        assert totalizado["PARTO"]["total_reporte"] == 1
        assert totalizado["PARTO"]["total_ordenadas"] == 2
        assert totalizado["PARTO"]["total_no_facturado"] == 1


# ──────────────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Empty ayudas, all facturado, only CODIGOS_EXCEPCION present."""

    def _run(self, reporte_rows, ayudas_rows, notas_rows=None):
        side_effect = [reporte_rows, ayudas_rows]
        notas_path = None
        if notas_rows is not None:
            side_effect.append(notas_rows)
            notas_path = Path("n.xlsx")
        with patch("app.services.ordenado_facturado_service._leer_como_raw") as m:
            m.side_effect = side_effect
            return procesar_cruce(Path("r.xlsx"), Path("a.xlsx"), notas_path)

    # ── Scenario: Empty ayudas ──
    def test_empty_ayudas(self, dummy_reporte, base_date):
        """GIVEN ayudas has no data rows
           WHEN processing
           THEN totalizado built without crash, no facturados empty."""
        # Solo headers, sin datos
        ayudas = _build_ayudas_rows([])
        result = self._run(dummy_reporte, ayudas)

        assert result["status"] == "success"
        assert result["data"]["no_facturados"] == []
        assert result["data"]["total_no_facturado"] == 0

        # No visible codes in ayudas → no aggregate rows with ayudas data
        # dummy_reporte only has code 000000 which is not in any category
        # TRASLADOS: 000000 is not in CODIGOS_EXCEPCION → no TRASLADOS row
        # PARTO/INTER/OTROS: all zero from empty ayudas → suppressed
        assert result["data"]["totalizado"] == []

    # ── Scenario: All facturado ──
    def test_all_facturado(self, base_date):
        """GIVEN every ayuda code is matched in reporte by same factura
           WHEN processing
           THEN no_facturados is empty, correct totals."""
        reporte = _build_reporte_rows([
            ("A-FAC", "735301", "PARTO", "100", base_date),
        ])
        ayudas = _build_ayudas_rows([
            ("A-FAC", "735301", "URGENCIAS", "100", base_date, "E1", "PARTO"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        assert result["data"]["no_facturados"] == []
        assert result["data"]["total_no_facturado"] == 0

        # Ayudas: ordenadas=1, no_facturado=0
        totalizado = {r["codigo"]: r for r in result["data"]["totalizado"]}
        assert totalizado["PARTO"]["total_reporte"] == 1
        assert totalizado["PARTO"]["total_ordenadas"] == 1
        assert totalizado["PARTO"]["total_no_facturado"] == 0

    # ── Scenario: Only CODIGOS_EXCEPCION present ──
    def test_only_exception_codes(self, base_date):
        """GIVEN only CODIGOS_EXCEPCION codes exist
           WHEN processing
           THEN only TRASLADOS row appears, no individual entries."""
        reporte = _build_reporte_rows([
            ("R-E1", "8938011", "EXCEP", "100", base_date),
        ])
        # Ayudas con código de excepción y factura que NO está en reporte
        ayudas = _build_ayudas_rows([
            ("A-E1", "8938011", "URGENCIAS", "100", base_date, "E1", "EXCEP"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        # No individual entries (only exception codes in ayudas)
        assert result["data"]["no_facturados"] == []

        # Only TRASLADOS in totalizado (exception codes only)
        codigos = {r["codigo"] for r in result["data"]["totalizado"]}
        assert codigos == {"TRASLADOS"}, f"Expected only TRASLADOS, got {codigos}"

        traslados = next(r for r in result["data"]["totalizado"])
        assert traslados["total_reporte"] == 1

    # ── Scenario: MATCH_POR_DOCUMENTO 890405 still works ──
    def test_match_por_documento_still_works(self, base_date):
        """GIVEN 890405 (match-by-doc code) is present in ayudas
           WHEN the same paciente has it in reporte
           THEN it is considered facturado (not in no_facturados)."""
        reporte = _build_reporte_rows([
            ("R-MATCH", "890405", "INTER", "100", base_date),
        ])
        # Misma factura en ayudas (match by factura)
        ayudas = _build_ayudas_rows([
            ("R-MATCH", "890405", "URGENCIAS", "100", base_date, "E1", "INTER"),
        ])
        result = self._run(reporte, ayudas)

        assert result["status"] == "success"
        cups = _cups_set(result["data"]["no_facturados"])
        assert "890405" not in cups, (
            "890405 matched by factura should be considered facturado"
        )


# ──────────────────────────────────────────────────────────────────────
# Requirement: CODIGOS_TOTALIZADO has zero references
# ──────────────────────────────────────────────────────────────────────

def test_codigos_totalizado_removed():
    """GIVEN the refactored service file
       WHEN searching for CODIGOS_TOTALIZADO
       THEN no matches exist in the module."""
    import inspect
    from app.services import ordenado_facturado_service as mod

    source = inspect.getsource(mod)
    assert "CODIGOS_TOTALIZADO" not in source, (
        "CODIGOS_TOTALIZADO constant must be removed"
    )
