"""Tests for app/services/normalized_rows.py (shared, parametrized builder).

Strict TDD: tests written BEFORE implementation.
"""

from __future__ import annotations

from app.services.normalized_rows import build_normalized_rows


class TestBuildNormalizedRows:
    """Spec: parametrized build_normalized_rows(error_groups, ...) -> list[dict]."""

    def test_empty_error_groups_returns_empty_list(self):
        """Given empty error_groups, returns []."""
        rows = build_normalized_rows(
            error_groups={},
            responsables_map={},
        )
        assert rows == []

    def test_centros_de_costo_row_format(self):
        """Centros de Costo rows have correct tipo_error, descripcion, detalle."""
        error_groups = {
            "Centros de Costo": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "procedimiento": "Test Proc",
                    "centro_actual": "CENTRO_A",
                    "centro_deberia": "CENTRO_B",
                }
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
        )
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "Centros de Costo"
        assert r["factura"] == "FAC-001"
        assert r["descripcion"] == "Centro de costo debería ser CENTRO_B"
        assert r["detalle"] == "CENTRO_A"
        assert r["procedimiento"] == "C001 - Test Proc"

    def test_fec_factura_populated(self):
        """fec_factura_map populates fec_factura field in rows."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fec_factura_map={"FAC-001": "2024-01-15"},
        )
        assert rows[0]["fec_factura"] == "2024-01-15"

    def test_fec_factura_empty_when_not_in_map(self):
        """fec_factura is '' when factura not in map."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
        )
        assert rows[0]["fec_factura"] == ""

    def test_responsable_cierra_populated(self):
        """responsables_map populates responsable_cierra field."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={"FAC-001": "John Doe"},
        )
        assert rows[0]["responsable_cierra"] == "John Doe"

    def test_fecha_cierre_vacia_true(self):
        """fecha_cierre_vacia_map sets the boolean field."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fecha_cierre_vacia_map={"FAC-001": True},
        )
        assert rows[0]["fecha_cierre_vacia"] is True

    def test_ide_contrato_row_format(self):
        """IDE Contrato rows: correct tipo_error with ide_contrato description."""
        error_groups = {
            "IDE Contrato": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "procedimiento": "Test Proc",
                    "ide_contrato_actual": "IDE_OLD",
                    "ide_contrato_deberia": "IDE_NEW",
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "IDE Contrato"
        assert r["descripcion"] == "IDE Contrato debería ser IDE_NEW"
        assert r["detalle"] == "IDE_OLD"

    def test_ide_contrato_codigo_no_en_db(self):
        """IDE Contrato with 'Código no en DB' uses short description."""
        error_groups = {
            "IDE Contrato": [
                {
                    "factura": "FAC-001",
                    "codigo": "C001",
                    "ide_contrato_actual": "N/A",
                    "ide_contrato_deberia": "Código no en DB",
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert rows[0]["descripcion"] == "Código no en DB"

    def test_decimales_row_format(self):
        """Decimales: each factura string becomes a row."""
        error_groups = {
            "Decimales": ["FAC-001", "FAC-002"]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 2
        assert rows[0]["tipo_error"] == "Decimales"
        assert rows[0]["factura"] == "FAC-001"
        assert rows[0]["descripcion"] == "Valores con decimales"

    def test_multiple_error_groups_combined(self):
        """Multiple error groups produce combined rows."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P1", "centro_actual": "A", "centro_deberia": "B"}
            ],
            "IDE Contrato": [
                {"factura": "FAC-002", "codigo": "C002", "ide_contrato_actual": "X", "ide_contrato_deberia": "Y"}
            ],
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 2
        tipos = {r["tipo_error"] for r in rows}
        assert tipos == {"Centros de Costo", "IDE Contrato"}

    def test_unknown_error_type_skipped(self):
        """Unknown tipo_error key is gracefully skipped (design: known types only)."""
        error_groups = {
            "Custom Check": [
                {"factura": "FAC-001", "field_a": "val_a", "field_b": "val_b"}
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        # Unknown keys produce no rows — only known tipo_error labels are processed
        assert rows == []

    def test_none_fec_factura_map_handled(self):
        """None fec_factura_map defaults to empty dict."""
        error_groups = {
            "Centros de Costo": [
                {"factura": "FAC-001", "codigo": "C001", "procedimiento": "P", "centro_actual": "A", "centro_deberia": "B"}
            ]
        }
        rows = build_normalized_rows(
            error_groups=error_groups,
            responsables_map={},
            fec_factura_map=None,
        )
        assert rows[0]["fec_factura"] == ""

    # --- Duplicados Farmacia ---

    def test_duplicados_farmacia_con_tipo_proc(self):
        """Duplicados Farmacia con codigo_tipo_procedimiento: 'Grupo ' en descripción."""
        error_groups = {
            "Duplicados Farmacia": [
                {
                    "factura": "FAC-001",
                    "codigo_tipo_procedimiento": "12",
                    "total_pares": 2,
                    "pares_duplicados": [
                        {"codigo": "A001", "cantidad": 1, "count": 2},
                        {"codigo": "A002", "cantidad": 2, "count": 2},
                    ],
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "⚠️ Revisión Necesaria"
        assert r["factura"] == "FAC-001"
        assert "Grupo 12" in r["descripcion"]
        assert "2 par(es) duplicado(s)" in r["descripcion"]
        assert r["procedimiento"] == "Grupo 12"

    def test_duplicados_farmacia_sin_tipo_proc(self):
        """Duplicados Farmacia sin codigo_tipo_procedimiento: NO 'Grupo ' en descripción."""
        error_groups = {
            "Duplicados Farmacia": [
                {
                    "factura": "FAC-001",
                    "total_pares": 2,
                    "pares_duplicados": [
                        {"codigo": "A001", "cantidad": 1, "count": 2},
                        {"codigo": "A002", "cantidad": 2, "count": 2},
                    ],
                }
            ]
        }
        rows = build_normalized_rows(error_groups=error_groups, responsables_map={})
        assert len(rows) == 1
        r = rows[0]
        assert r["tipo_error"] == "⚠️ Revisión Necesaria"
        assert r["factura"] == "FAC-001"
        assert "Grupo" not in r["descripcion"]
        assert r["procedimiento"] == ""
        assert "2 par(es) duplicado(s)" in r["descripcion"]


class TestSharedHandlerConsistency:
    """Tests for standardized handler pattern (desc=problema, proc=_build_procedimiento, det=key)."""

    # --- 2.1 Centros Costo ---

    def test_centros_costo_engine_enriched(self):
        """Engine-enriched: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Centros de Costo": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "CONSULTA",
                "centro_costo": "CC-A", "centro_actual": "CC-A", "centro_deberia": "CC-B",
                "problema": "Centro costo no coincide",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Centro costo no coincide"
        assert r["procedimiento"] == "C001 - CONSULTA"
        assert r["detalle"] == "CC-A"

    def test_centros_costo_legacy_format(self):
        """No problema: fallback to template."""
        rows = build_normalized_rows(error_groups={
            "Centros de Costo": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "P",
                "centro_actual": "A", "centro_deberia": "B",
            }]
        }, responsables_map={})
        assert "Centro de costo debería ser" in rows[0]["descripcion"]

    # --- 2.2 IDE Contrato ---

    def test_ide_contrato_engine_enriched(self):
        """Engine-enriched: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "IDE Contrato": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "P",
                "ide_contrato_actual": "OLD", "ide_contrato_deberia": "NEW",
                "problema": "IDE no coincide",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "IDE no coincide"

    # --- 2.3 Cups Equivalentes ---

    def test_cups_equivalentes_engine_enriched(self):
        """Engine-enriched: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Cups Equivalentes": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "EQUIV",
                "estancia_str": "5 dias",
                "problema": "Cups equivalentes detectado",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Cups equivalentes detectado"

    def test_cups_equivalentes_legacy_format(self):
        """No problema: fallback to accion field."""
        rows = build_normalized_rows(error_groups={
            "Cups Equivalentes": [{
                "factura": "FAC-001", "codigo": "C001",
                "accion": "Reemplazar cup",
                "estancia_str": "3 dias",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Reemplazar cup"

    # --- 2.4 MAL CAPITADO ---

    def test_mal_capitado_engine_enriched(self):
        """Engine-enriched: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "MAL CAPITADO": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "P",
                "ide_contrato_actual": "IDE-X",
                "problema": "Mal capitado detectado",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Mal capitado detectado"
        assert rows[0]["procedimiento"] == "C001 - P"
        assert rows[0]["detalle"] == "IDE-X"

    def test_mal_capitado_legacy_format(self):
        """No problema: fallback to observacion field."""
        rows = build_normalized_rows(error_groups={
            "MAL CAPITADO": [{
                "factura": "FAC-001",
                "observacion": "Capitado invalido",
                "ide_contrato_actual": "IDE-X",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Capitado invalido"

    # --- 2.5 Cantidades (P0) ---

    def test_cantidades_engine_enriched(self):
        """Engine provides cantidad, no cantidad_esperada."""
        rows = build_normalized_rows(error_groups={
            "Cantidades": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "URG",
                "cantidad": "3",
                "problema": "Cantidad debe ser <= 1 en Urgencias",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Cantidad debe ser <= 1 en Urgencias"
        assert r["procedimiento"] == "C001 - URG"
        assert r["detalle"] == "3"

    def test_cantidades_legacy_con_cantidad_esperada(self):
        """Legacy: template with cantidad_esperada."""
        rows = build_normalized_rows(error_groups={
            "Cantidades Hospitalización": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "HOSP",
                "cantidad": "5", "cantidad_esperada": "1",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Cantidad 5 debería ser 1"
        assert r["detalle"] == "5"

    def test_cantidades_sin_cantidad_esperada(self):
        """P0: no cantidad_esperada in engine output, must not crash."""
        rows = build_normalized_rows(error_groups={
            "Cantidades Hospitalización": [{
                "factura": "FAC-001", "codigo": "C001", "procedimiento": "HOSP",
                "cantidad": "5",
                "problema": "Cantidad hospitalizacion incorrecta",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Cantidad hospitalizacion incorrecta"
        assert r["detalle"] == "5"

    # --- 2.6 Decimales (string list) ---

    def test_decimales_string_list(self):
        """Decimales as string list: keep as-is."""
        rows = build_normalized_rows(error_groups={
            "Decimales": ["FAC-001"]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Valores con decimales"
        assert rows[0]["procedimiento"] == "Vlr. Procedimiento"
        assert rows[0]["detalle"] == "Vlr. Subsidiado"

    # --- 2.7 Tipo ID / Edad ---

    def test_tipo_id_edad_engine_enriched(self):
        """Engine-enriched: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Tipo Identificación / Edad": [{
                "factura": "FAC-001",
                "numero_identificacion": "12345",
                "edad_anios": "25", "edad_meses": "0",
                "tipo_actual": "CC", "tipo_deberia": "TI",
                "problema": "Tipo ID debe ser TI",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Tipo ID debe ser TI"

    def test_tipo_id_edad_legacy_format(self):
        """No problema: fallback to tipo_deberia template."""
        rows = build_normalized_rows(error_groups={
            "Tipo Identificación / Edad": [{
                "factura": "FAC-001",
                "tipo_actual": "CC", "tipo_deberia": "TI",
            }]
        }, responsables_map={})
        assert "debería ser" in rows[0]["descripcion"]

    # --- 2.8 Profesionales ---

    def test_profesionales_engine_enriched(self):
        """Profesionales: desc from problema, proc from _build_procedimiento."""
        rows = build_normalized_rows(error_groups={
            "Profesionales": [{
                "factura": "FAC-001",
                "codigo_profesional": "DOC123",
                "procedimiento": "CONSULTA",
                "problema": "Profesional no habilitado",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Profesional no habilitado"
        assert r["procedimiento"] == "DOC123 - CONSULTA"

    # --- 2.9 Código Entidad vs Af. ---

    def test_entidad_vs_afiliacion_engine_enriched(self):
        """Código Entidad vs Af.: desc from problema, already correct."""
        rows = build_normalized_rows(error_groups={
            "Código Entidad vs Afiliación": [{
                "factura": "FAC-001",
                "codigo_entidad_cobrar": "85700",
                "entidad_cobrar_nombre": "SALUD TOTAL",
                "entidad_afiliacion": "EPS",
                "problema": "Entidad no coincide con afiliacion",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Entidad no coincide con afiliacion"

    # --- 2.10 Tipo Usuario ---

    def test_tipo_usuario_engine_enriched(self):
        """Tipo Usuario: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Tipo Usuario": [{
                "factura": "FAC-001",
                "codigo": "C001", "procedimiento": "P",
                "tipo_actual": "BENEFICIARIO",
                "problema": "Tipo usuario incorrecto",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Tipo usuario incorrecto"
        assert rows[0]["procedimiento"] == "C001 - P"
        assert rows[0]["detalle"] == "BENEFICIARIO"

    def test_tipo_usuario_legacy_format(self):
        """No problema: hardcoded desc."""
        rows = build_normalized_rows(error_groups={
            "Tipo Usuario": [{
                "factura": "FAC-001",
                "tipo_actual": "BENEFICIARIO",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Revisar tipo usuario en Targetero"

    # --- 2.11 Revisión Necesaria ---

    def test_revision_necesaria_engine_enriched(self):
        """Revisión Necesaria: already correct."""
        rows = build_normalized_rows(error_groups={
            "⚠️ Revisión Necesaria": [{
                "factura": "FAC-001",
                "codigo": "C001", "procedimiento": "P",
                "detalle": "86",
                "descripcion": "Entidad 86 requiere revision",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Entidad 86 requiere revision"

    # --- 2.12 Copago vs Entidad ---

    def test_copago_entidad_enriched(self):
        """Copago vs Entidad: already correct with _build_procedimiento."""
        rows = build_normalized_rows(error_groups={
            "Copago vs Entidad": [{
                "factura": "FAC-001",
                "codigo": "C001", "procedimiento": "CONSULTA",
                "entidad_cobrar": "85700",
                "vlr_copago": "5000",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["procedimiento"] == "C001 - CONSULTA"
        assert "Copago" in r["detalle"]

    # --- 2.13 Duplicados Farmacia (P0) ---

    def test_duplicados_farmacia_engine_enriched(self):
        """Engine provides codigo, cantidad in pares; must not crash."""
        rows = build_normalized_rows(error_groups={
            "Duplicados Farmacia": [{
                "factura": "FAC-001",
                "codigo_tipo_procedimiento": "12",
                "problema": "Duplicados de farmacia detectados",
                "total_pares": 1,
                "pares_duplicados": [
                    {"codigo": "A001", "cantidad": 1, "count": 2},
                ],
            }]
        }, responsables_map={})
        r = rows[0]
        assert "Duplicados" in r["descripcion"]
        assert "A001" in r["detalle"]

    def test_duplicados_farmacia_sin_pares(self):
        """P0: no pares_duplicados list, must not crash."""
        rows = build_normalized_rows(error_groups={
            "Duplicados Farmacia": [{
                "factura": "FAC-001",
                "problema": "Duplicados farmacia",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Duplicados farmacia"
        assert r["detalle"] is not None

    # --- 2.14 Cups Sin Contrato ---

    def test_cups_sin_contrato_enriched(self):
        """Cups Sin Contrato: desc from problema, proc from _build_procedimiento."""
        rows = build_normalized_rows(error_groups={
            "Cups Sin Contrato": [{
                "factura": "FAC-001",
                "codigo": "C001", "procedimiento": "CONSULTA",
                "codigo_entidad_cobrar": "85700",
                "entidad": "EPS",
                "problema": "CUPS sin contrato vigente",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "CUPS sin contrato vigente"
        assert r["procedimiento"] == "C001 - CONSULTA"

    # --- 2.15 Cups No CAPITA ---

    def test_cups_no_capita_engine_enriched(self):
        """Cups No CAPITA: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Cups No CAPITA": [{
                "factura": "FAC-001",
                "codigo": "C001", "procedimiento": "P",
                "problema": "Cups no cubierto por capitacion",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Cups no cubierto por capitacion"
        assert rows[0]["procedimiento"] == "C001 - P"

    def test_cups_no_capita_legacy_format(self):
        """No problema: fallback to observacion."""
        rows = build_normalized_rows(error_groups={
            "Cups No CAPITA": [{
                "factura": "FAC-001",
                "observacion": "No cubierto",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "No cubierto"

    # --- 2.16 Duplicado ID+Código ---

    def test_duplicado_id_codigo_engine_enriched(self):
        """Duplicado ID+Código: desc from problema."""
        rows = build_normalized_rows(error_groups={
            "Duplicado ID+Código": [{
                "factura": "FAC-001",
                "identificacion": "ID-123",
                "codigo": "C001", "procedimiento": "P",
                "cantidad_repeticiones": 3,
                "facturas": ["FAC-001", "FAC-002"],
                "problema": "Procedimiento duplicado x3",
            }]
        }, responsables_map={})
        assert rows[0]["descripcion"] == "Procedimiento duplicado x3"
        assert rows[0]["procedimiento"] == "C001 - P"

    def test_duplicado_id_codigo_legacy_format(self):
        """No problema: fallback to template."""
        rows = build_normalized_rows(error_groups={
            "Duplicado ID+Código": [{
                "factura": "FAC-001",
                "identificacion": "ID-123",
                "codigo": "C001",
                "cantidad_repeticiones": 2,
            }]
        }, responsables_map={})
        assert "duplicado x2" in rows[0]["descripcion"]

    # --- 2.17 Generic Fallback (shared) ---

    def test_generic_fallback_empty_proc_and_det(self):
        """Generic fallback: if proc AND det empty, first non-factura key used."""
        rows = build_normalized_rows(error_groups={
            "MAL CAPITADO": [{
                "factura": "FAC-001",
                "problema": "Problema de capitado",
                "observacion": "Capitado invalido",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Problema de capitado"
        # Fallback should fill procedimiento or detalle from first non-factura key
        assert r["procedimiento"] or r["detalle"]


class TestSharedP0Fixes:
    """P0 fix tests for cantidades_urgencias and duplicados_farmacia."""

    def test_cantidades_soat_hospitalizacion_sin_cantidad_esperada(self):
        """P0: Cantidades SOAT Hospitalización sin cantidad_esperada no debe fallar."""
        rows = build_normalized_rows(error_groups={
            "Cantidades SOAT Hospitalización": [{
                "factura": "FAC-001",
                "codigo": "C001",
                "procedimiento": "PROC",
                "cantidad": "2",
                "problema": "Cantidad SOAT hospitalizacion incorrecta",
            }]
        }, responsables_map={})
        r = rows[0]
        assert r["descripcion"] == "Cantidad SOAT hospitalizacion incorrecta"
        assert r["detalle"] == "2"

    def test_duplicados_farmacia_sin_pares_duplicados_key(self):
        """P0: no 'pares_duplicados' key at all, must not crash."""
        rows = build_normalized_rows(error_groups={
            "Duplicados Farmacia": [{
                "factura": "FAC-001",
                "codigo_tipo_procedimiento": "12",
                "total_pares": 1,
            }]
        }, responsables_map={})
        assert len(rows) == 1
        assert rows[0]["detalle"] is not None
