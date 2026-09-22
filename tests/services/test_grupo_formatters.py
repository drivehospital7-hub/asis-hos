"""TDD tests for dominio-grupo-error T10: GRUPO_FORMATTERS registry.

Spec named formatters escape hatch: only these grupo_error values route to
named formatters — Tipo ID/Edad, Codigo-Entidad-vs-Afiliacion,
Duplicados-Farmacia, Cups-Equivalentes, Revision-Necesaria.

Strict semantics: formatter keeps descripcion/tipo_error/header only.
Procedimiento/detalle come exclusively from live detalle_a/b (mapping
first, item second); without declared A/B they stay blank ("").
"""

from __future__ import annotations

from app.services.normalized_rows import GRUPO_FORMATTERS

EXPECTED_KEYS = frozenset({
    "Tipo Identificacion / Edad",
    "Codigo-Entidad-vs-Afiliacion",
    "Duplicados-Farmacia",
    "Cups-Equivalentes",
    "Revision-Necesaria",
})


def _rows(grupo: str, items: list[dict]) -> list[dict]:
    from app.services.normalized_rows import build_normalized_rows

    return build_normalized_rows(
        error_groups={grupo: [dict(i) for i in items]},
        responsables_map={},
        use_grupo_mapping=True,
        grupo_mappings={},
    )


class TestFormatterRegistry:
    def test_exactly_five_named_formatters(self):
        assert set(GRUPO_FORMATTERS.keys()) == EXPECTED_KEYS

    def test_no_sixth_formatter(self):
        assert len(GRUPO_FORMATTERS) == 5


class TestTipoIdEdadFormatter:
    def test_edad_recompute_and_identificacion_procedimiento(self):
        rows = _rows("Tipo Identificacion / Edad", [
            {
                "factura": "F1",
                "identificacion": "123",
                "tipo_actual": "TI",
                "tipo_deberia": "CC",
                "problema": "",
                "edad_anios": 10,
                "edad_meses": 25,
                "fec_nacimiento": "2015-03-10",
                "fec_factura": "2025-08-20",
            }
        ])
        assert rows[0]["tipo_error"] == "Tipo Identificacion / Edad"
        assert rows[0]["descripcion"] == "Tipo actual TI debería ser CC"
        # Sin A/B declarado: blanco, sin valores automaticos.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_live_ab_respected(self):
        rows = _rows("Tipo Identificacion / Edad", [
            {
                "factura": "F1",
                "identificacion": "123",
                "tipo_actual": "TI",
                "tipo_deberia": "CC",
                "problema": "",
                "edad_anios": 10,
                "edad_meses": 25,
                "fec_nacimiento": "2015-03-10",
                "fec_factura": "2025-08-20",
                "detalle_a_campo": "identificacion",
                "detalle_b_campo": "Tipo: {tipo_actual}",
            }
        ])
        assert rows[0]["descripcion"] == "Tipo actual TI debería ser CC"
        assert rows[0]["procedimiento"] == "123"
        assert rows[0]["detalle"] == "Tipo: TI"


class TestCodigoEntidadFormatter:
    def test_as_ms_requiere_86000_branch(self):
        rows = _rows("Codigo-Entidad-vs-Afiliacion", [
            {
                "factura": "F2",
                "tipo_identificacion": "AS",
                "cod_entidad_actual": "5123",
                "cod_entidad_esperado": "86000",
                "problema": "as_ms_requiere_86000",
            }
        ])
        assert rows[0]["descripcion"] == "Tipo ID AS requiere Cód Entidad Cobrar = 86000"
        # Sin A/B declarado: blanco, sin valores automaticos.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_legacy_codigo_entidad_branch(self):
        rows = _rows("Codigo-Entidad-vs-Afiliacion", [
            {
                "factura": "F3",
                "codigo_entidad_cobrar": "5177",
                "entidad_cobrar_nombre": "MALLAMAS",
                "entidad_afiliacion": "ESS118",
                "problema": "sin codigo",
            }
        ])
        # Sin A/B declarado: blanco, sin valores automaticos.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_live_ab_respected(self):
        rows = _rows("Codigo-Entidad-vs-Afiliacion", [
            {
                "factura": "F2",
                "tipo_identificacion": "AS",
                "cod_entidad_actual": "5123",
                "cod_entidad_esperado": "86000",
                "problema": "as_ms_requiere_86000",
                "detalle_a_campo": "cod_entidad_actual",
                "detalle_b_campo": "Actual: {cod_entidad_actual}",
            }
        ])
        assert rows[0]["descripcion"] == "Tipo ID AS requiere Cód Entidad Cobrar = 86000"
        assert rows[0]["procedimiento"] == "5123"
        assert rows[0]["detalle"] == "Actual: 5123"


class TestDuplicadosFarmaciaFormatter:
    def test_pares_join_and_tipo_remap(self):
        rows = _rows("Duplicados-Farmacia", [
            {
                "factura": "F4",
                "codigo_tipo_procedimiento": "01",
                "total_pares": 2,
                "pares_duplicados": [
                    {"codigo": "c1", "cantidad": 1, "count": 2},
                    {"codigo": "c2", "cantidad": 2, "count": 3},
                ],
                "problema": "",
            }
        ])
        assert rows[0]["tipo_error"] == "Revision-Necesaria"
        assert "Grupo 01" in rows[0]["descripcion"]
        # Sin A/B declarado: blanco, sin valores automaticos.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_live_ab_respected(self):
        rows = _rows("Duplicados-Farmacia", [
            {
                "factura": "F4",
                "codigo_tipo_procedimiento": "01",
                "total_pares": 2,
                "pares_duplicados": [
                    {"codigo": "c1", "cantidad": 1, "count": 2},
                ],
                "problema": "",
                "detalle_a_campo": "codigo_tipo_procedimiento",
                "detalle_b_campo": "Pares: {total_pares}",
            }
        ])
        assert rows[0]["tipo_error"] == "Revision-Necesaria"
        assert "Grupo 01" in rows[0]["descripcion"]
        assert rows[0]["procedimiento"] == "01"
        assert rows[0]["detalle"] == "Pares: 2"


class TestCupsEquivalentesFormatter:
    def test_codigo_list_and_estancia(self):
        rows = _rows("Cups-Equivalentes", [
            {
                "factura": "F5",
                "codigo": ["a1", "a2"],
                "procedimiento": "",
                "estancia_str": "2 días 3 horas",
                "problema": "equiv",
            }
        ])
        assert rows[0]["tipo_error"] == "Cups-Equivalentes"
        assert rows[0]["descripcion"] == "equiv"
        # Sin A/B declarado: blanco, sin valores automaticos.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_live_ab_respected(self):
        rows = _rows("Cups-Equivalentes", [
            {
                "factura": "F5",
                "codigo": "CUPS1",
                "procedimiento": "Proc1",
                "estancia_str": "2 días 3 horas",
                "problema": "equiv",
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "Estancia: {estancia_str}",
            }
        ])
        assert rows[0]["tipo_error"] == "Cups-Equivalentes"
        assert rows[0]["descripcion"] == "equiv"
        assert rows[0]["procedimiento"] == "CUPS1 - Proc1"
        assert rows[0]["detalle"] == "Estancia: 2 días 3 horas"


class TestRevisionNecesariaFormatter:
    def test_passthrough_with_inference(self):
        rows = _rows("Revision-Necesaria", [
            {
                "factura": "F6",
                "codigo": "c9",
                "procedimiento": "p9",
                "detalle": "86",
                "descripcion": "",
                "problema": "x",
            }
        ])
        assert rows[0]["tipo_error"] == "Revision-Necesaria"
        assert rows[0]["descripcion"] == "Cód Entidad Cobrar = 86 requiere revisión manual"
        # Detalle en item pero sin B declarado: queda blanco.
        assert rows[0]["procedimiento"] == ""
        assert rows[0]["detalle"] == ""

    def test_live_ab_respected(self):
        rows = _rows("Revision-Necesaria", [
            {
                "factura": "F6",
                "codigo": "c9",
                "procedimiento": "p9",
                "detalle": "86",
                "descripcion": "",
                "problema": "x",
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "detalle",
            }
        ])
        assert rows[0]["tipo_error"] == "Revision-Necesaria"
        assert rows[0]["descripcion"] == "Cód Entidad Cobrar = 86 requiere revisión manual"
        assert rows[0]["procedimiento"] == "c9 - p9"
        assert rows[0]["detalle"] == "86"
