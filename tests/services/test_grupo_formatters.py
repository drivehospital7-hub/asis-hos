"""TDD tests for dominio-grupo-error T10: GRUPO_FORMATTERS registry.

Spec named formatters escape hatch: only these grupo_error values route to
named formatters — Tipo ID/Edad, Codigo-Entidad-vs-Afiliacion,
Duplicados-Farmacia, Cups-Equivalentes, Revision-Necesaria.
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
        assert rows[0]["procedimiento"] == "123"
        assert rows[0]["descripcion"] == "Tipo actual TI debería ser CC"
        assert rows[0]["detalle"] == "10 años 5 meses 10 días"


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
        assert rows[0]["detalle"] == "Actual: 5123"
        assert rows[0]["procedimiento"] == "5123"

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
        assert rows[0]["procedimiento"] == "5177 - MALLAMAS"
        assert rows[0]["detalle"] == "Afiliación: ESS118"


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
        assert rows[0]["detalle"] == "c1 x1 (2 veces); c2 x2 (3 veces)"
        assert "Grupo 01" in rows[0]["descripcion"]
        assert rows[0]["procedimiento"] == "Grupo 01"


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
        assert rows[0]["procedimiento"] == "a1, a2"
        assert rows[0]["detalle"] == "Estancia: 2 días 3 horas"
        assert rows[0]["descripcion"] == "equiv"


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
        assert rows[0]["procedimiento"] == "c9 - p9"
        assert rows[0]["detalle"] == "86"
