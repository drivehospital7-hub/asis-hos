"""Tests para app/services/odontologia/normalized_rows.py — fec_factura.

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.odontologia.normalized_rows import build_odontologia_normalized_rows


class TestFecFacturaInNormalizedRows:
    """Spec R1 + R3: normalized rows MUST include fec_factura from mapping."""

    def test_fec_factura_present_in_decimales_row(self):
        """Given a fec_factura_map with a known factura,
        when build_odontologia_normalized_rows is called,
        then the row with that factura MUST have fec_factura set."""
        fec_factura_map = {"FAC-001": "2024-01-15"}
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 1
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_empty_when_factura_not_in_map(self):
        """Given a fec_factura_map that does NOT contain the row's factura,
        when the row is built,
        then fec_factura MUST be an empty string."""
        fec_factura_map = {"FAC-999": "2024-01-15"}
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_empty_with_empty_map(self):
        """Given an empty fec_factura_map,
        when any row is built,
        then fec_factura MUST be an empty string."""
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map={},
        )
        assert rows[0]["fec_factura"] == ""

    def test_fec_factura_in_all_row_types(self):
        """Given fec_factura_map with multiple facturas,
        when multiple error types are built,
        then ALL rows MUST have fec_factura populated correctly."""
        fec_factura_map = {
            "FAC-001": "2024-01-15",
            "FAC-002": "2024-01-16",
        }
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[{"factura": "FAC-002", "tipos": "ODT, CON"}],
            ruta_dup=[],
            profesionales=[],
            cantidades=[],
            tipo_id_edad=[],
            centro_costo=[],
            ide_contrato=[],
            responsable_cierra={},
            fec_factura_map=fec_factura_map,
        )
        assert len(rows) == 2
        assert rows[0]["fec_factura"] == "2024-01-15"
        assert rows[1]["fec_factura"] == "2024-01-16"

    def test_fec_factura_key_exists_on_all_items(self):
        """Given any data,
        when rows are built,
        then EVERY row dict MUST have the 'fec_factura' key."""
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "100"}],
            doble_tipo=[{"factura": "FAC-002", "tipos": "ODT"}],
            ruta_dup=[{"identificacion": "ID-1", "facturas": "FAC-003", "cantidad": 2}],
            profesionales=[{"factura": "FAC-004", "codigo_profesional": "123", "procedimiento": "Test"}],
            cantidades=[{"factura": "FAC-005", "tipo_procedimiento": "ODT", "cantidad": "3"}],
            tipo_id_edad=[{"factura": "FAC-006", "tipo_actual": "CC", "tipo_deberia": "TI"}],
            centro_costo=[{"factura": "FAC-007", "centro_actual": "A", "centro_deberia": "B"}],
            ide_contrato=[{"factura": "FAC-008", "codigo": "C001"}],
            responsable_cierra={},
            fec_factura_map={},
        )
        assert len(rows) == 8
        for row in rows:
            assert "fec_factura" in row, f"Row missing fec_factura: {row}"


class TestOdontologiaHandlerConsistency:
    """Tests for standardized handler pattern (desc=problema, proc=_build_procedimiento, det=key)."""

    # --- 1.1 Decimales ---

    def test_decimales_engine_enriched(self):
        """Engine-enriched: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "CONSULTA",
                "vlr_subsidiado": "15000.50", "vlr_procedimiento": "15000",
                "problema": "Valores con decimales detectados",
            }],
            doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        assert rows[0]["descripcion"] == "Valores con decimales detectados"
        assert rows[0]["procedimiento"] == "C001 - CONSULTA"

    def test_decimales_legacy_format(self):
        """Legacy: no problema, fallback to values template."""
        rows = build_odontologia_normalized_rows(
            decimales=[{"factura": "FAC-001", "valores": "15000.50"}],
            doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        assert "Valores con decimales" in rows[0]["descripcion"]

    # --- 1.2 Doble Tipo ---

    def test_doble_tipo_engine_enriched(self):
        """Engine-enriched: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[{
                "factura": "FAC-001", "codigo": "C002", "procedimiento": "ODONTOLOGIA",
                "tipo_procedimiento": "ODT",
                "problema": "Multiples tipos en misma factura",
            }],
            ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Multiples tipos en misma factura"
        assert r["procedimiento"] == "C002 - ODONTOLOGIA"
        assert r["detalle"] == "ODT"

    def test_doble_tipo_legacy_format(self):
        """Legacy: no problema, hardcoded desc, empty procedimiento, tipos as detalle."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[{
                "factura": "FAC-001", "tipos": "ODT, CON",
            }],
            ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Múltiples tipos de procedimiento"
        assert r["detalle"] == "ODT, CON"

    # --- 1.3 Ruta Duplicada (P0) ---

    def test_ruta_duplicada_engine_enriched(self):
        """Engine-enriched: provides identificacion, cantidad_repeticiones, no facturas string."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[{
                "identificacion": "ID-123",
                "cantidad_repeticiones": 3,
                "problema": "Paciente con facturas duplicadas en PyP",
            }],
            profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Paciente con facturas duplicadas en PyP"
        assert r["detalle"] == "ID-123"

    def test_ruta_duplicada_legacy_format(self):
        """Legacy: provides facturas string and cantidad int."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[{
                "identificacion": "ID-123",
                "facturas": "FAC-001,FAC-002",
                "cantidad": 2,
            }],
            profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["factura"] == "FAC-001"
        assert r["detalle"] == "ID-123"

    # --- 1.4 Profesionales ---

    def test_profesionales_engine_enriched(self):
        """Profesionales: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[{
                "factura": "FAC-001",
                "codigo_profesional": "DOC123",
                "procedimiento": "CONSULTA",
                "problema": "Profesional no coincide con convenio",
            }],
            cantidades=[], tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Profesional no coincide con convenio"
        assert r["procedimiento"] == "DOC123 - CONSULTA"

    def test_profesionales_legacy_format(self):
        """Profesionales: no problema, fallback to regla."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[{
                "factura": "FAC-001",
                "codigo_profesional": "DOC123",
                "procedimiento": "CONSULTA",
                "regla": "Convenio invalido",
            }],
            cantidades=[], tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        assert rows[0]["descripcion"] == "Convenio invalido"

    # --- 1.5 Cantidades ---

    def test_cantidades_engine_enriched(self):
        """Cantidades: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "RAYOS-X",
                "cantidad": "5",
                "problema": "Cantidad anomala: 5",
            }],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Cantidad anomala: 5"
        assert r["procedimiento"] == "C001 - RAYOS-X"
        assert r["detalle"] == "5"

    def test_cantidades_legacy_format(self):
        """Cantidades: no problema, no codigo/procedimiento, uses tipo_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[{
                "factura": "FAC-001",
                "tipo_procedimiento": "ODT",
                "cantidad": "3",
            }],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert "Cantidad anómala" in r["descripcion"]
        assert r["procedimiento"] == "ODT"
        assert r["detalle"] == "3"

    # --- 1.6 Tipo ID / Edad ---

    def test_tipo_id_edad_engine_enriched(self):
        """Tipo ID / Edad: desc from problema, proc from num_id."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[{
                "factura": "FAC-001",
                "numero_identificacion": "12345",
                "edad_anios": "25",
                "tipo_actual": "CC",
                "tipo_deberia": "TI",
                "problema": "Tipo ID CC deberia ser TI para edad 25",
            }],
            centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Tipo ID CC deberia ser TI para edad 25"
        assert r["procedimiento"] == "12345"
        assert "25" in r["detalle"]

    def test_tipo_id_edad_legacy_format(self):
        """Tipo ID / Edad: no problema, fallback to inference."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[{
                "factura": "FAC-001",
                "tipo_actual": "CC",
                "regla": "menor_7_anios",
            }],
            centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert "debería" in r["descripcion"]
        assert r["procedimiento"] == ""

    # --- 1.7 Tipo ID / Entidad ---

    def test_tipo_id_entidad_engine_enriched(self):
        """Tipo ID / Entidad: desc from problema."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
            tipo_id_entidad=[{
                "factura": "FAC-001",
                "tipo_identificacion": "CC",
                "cod_entidad_actual": "85700",
                "cod_entidad_esperado": "86000",
                "problema": "86000_solo_para_as_ms",
            }],
        )
        r = rows[0]
        assert "86000" in r["descripcion"]
        assert "CC" in r["descripcion"]

    # --- 1.8 Centro Costo ---

    def test_centro_costo_engine_enriched(self):
        """Centro Costo: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[{
                "factura": "FAC-001",
                "codigo": "C001",
                "procedimiento": "CONSULTA",
                "centro_actual": "CC-A",
                "centro_deberia": "CC-B",
                "problema": "Centro de costo no coincide",
            }],
            ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Centro de costo no coincide"
        assert r["procedimiento"] == "C001 - CONSULTA"
        assert r["detalle"] == "CC-A"

    def test_centro_costo_legacy_format(self):
        """Centro Costo: no problema, fallback to centro_deberia template."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[{
                "factura": "FAC-001",
                "centro_actual": "CC-A",
                "centro_deberia": "CC-B",
            }],
            ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert "Centro de costo debería ser" in r["descripcion"]
        assert r["detalle"] == "CC-A"

    # --- 1.9 IDE Contrato ---

    def test_ide_contrato_engine_enriched(self):
        """IDE Contrato: desc from problema, proc from _build_procedimiento(codigo, '')."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[{
                "factura": "FAC-001",
                "codigo": "C001",
                "ide_actual": "ID-OLD",
                "ide_deberia": "ID-NEW",
                "problema": "IDE Contrato no coincide",
            }],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "IDE Contrato no coincide"
        assert r["procedimiento"] == "C001"
        assert r["detalle"] == "ID-OLD"

    # --- 1.10 Código Entidad vs Af. ---

    def test_entidad_afiliacion_engine_enriched(self):
        """Código Entidad vs Af.: desc from problema, legacy keys."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
            entidad_afiliacion_comparison=[{
                "factura": "FAC-001",
                "codigo_entidad_cobrar": "85700",
                "entidad_cobrar_nombre": "SALUD TOTAL",
                "entidad_afiliacion": "EPS Otra",
                "problema": "Entidad no coincide",
            }],
        )
        r = rows[0]
        assert r["descripcion"] == "Entidad no coincide"

    # --- 1.11 Tipo Usuario ---

    def test_tipo_usuario_engine_enriched(self):
        """Tipo Usuario: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
            tipo_usuario=[{
                "factura": "FAC-001",
                "codigo": "C001",
                "procedimiento": "CONSULTA",
                "tipo_actual": "BENEFICIARIO",
                "tipo_usuario": "COTIZANTE",
                "problema": "Tipo usuario debe ser Cotizante",
            }],
        )
        r = rows[0]
        assert r["descripcion"] == "Tipo usuario debe ser Cotizante"
        assert r["procedimiento"] == "C001 - CONSULTA"
        assert r["detalle"] == "BENEFICIARIO"

    def test_tipo_usuario_legacy_format(self):
        """Tipo Usuario: no problema, hardcoded desc."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
            tipo_usuario=[{
                "factura": "FAC-001",
                "tipo_actual": "BENEFICIARIO",
            }],
        )
        assert rows[0]["descripcion"] == "Revisar tipo usuario en Targetero"

    # --- 1.12 Cups Sin Contrato ---

    def test_cups_sin_contrato_engine_enriched(self):
        """Cups Sin Contrato: desc from problema, proc from _build_procedimiento."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[], profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
            cups_sin_contrato=[{
                "factura": "FAC-001",
                "codigo": "C001",
                "procedimiento": "CONSULTA",
                "codigo_entidad_cobrar": "85700",
                "entidad": "SALUD TOTAL",
                "problema": "CUPS sin contrato",
            }],
        )
        r = rows[0]
        assert r["descripcion"] == "CUPS sin contrato"
        assert r["procedimiento"] == "C001 - CONSULTA"

    # --- 1.13 Generic Fallback ---

    def test_generic_fallback_empty_proc_and_det(self):
        """Generic fallback: if proc AND det empty, first non-factura key used."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[{
                "factura": "FAC-001",
                "problema": "Paciente duplicado",
                "identificacion": "ID-123",
            }],
            profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["descripcion"] == "Paciente duplicado"
        # Fallback should fill procedimiento or detalle from identificacion
        assert r["procedimiento"] or r["detalle"]


class TestOdontologiaP0Fixes:
    """P0 fix tests for ruta_duplicada edge cases."""

    def test_ruta_duplicada_sin_facturas_string(self):
        """Engine output: no facturas string, only identificacion + cantidad_repeticiones."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[{
                "identificacion": "ID-456",
                "cantidad_repeticiones": 5,
                "problema": "Paciente con facturas repetidas",
            }],
            profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["factura"] == "ID-456"  # fallback from identificacion
        assert r["detalle"] == "ID-456"
        assert r["descripcion"] == "Paciente con facturas repetidas"

    def test_ruta_duplicada_con_engine_legacy(self):
        """Engine output with legacy keys: facturas + cantidad."""
        rows = build_odontologia_normalized_rows(
            decimales=[], doble_tipo=[], ruta_dup=[{
                "identificacion": "ID-789",
                "facturas": "FAC-100,FAC-200",
                "cantidad": 2,
                "problema": "Paciente con facturas en PyP",
            }],
            profesionales=[], cantidades=[],
            tipo_id_edad=[], centro_costo=[], ide_contrato=[],
            responsable_cierra={},
        )
        r = rows[0]
        assert r["factura"] == "FAC-100"  # first from split
        assert r["detalle"] == "ID-789"
