"""TDD tests for dominio-grupo-error T9: generic Detalle A/B mapper + cutover.

Spec procesar-detalle-mapping:
- plain groups render via detalle_a/b_campo + descripcion_template (~70%)
- group-by key order replicates the legacy fallback order
- unknown grupo_error with empty mapping -> generic fallback + flagged
- legacy blocks stay behind the cutover flag (default OFF)
"""

from __future__ import annotations

CENTROS_ITEMS = [
    {
        "factura": "F001",
        "codigo": "890201",
        "procedimiento": "Consulta",
        "problema": "Centro de costo invalido",
        "centro_actual": "URGENCIAS",
        "centro_costo": "URGENCIAS",
        "regla": "#7",
    },
    {
        "factura": "F002",
        "codigo": "890202",
        "procedimiento": "Control",
        "problema": "Centro de costo invalido",
        "centro_actual": "",
        "centro_costo": "PISO",
        "regla": "#7",
    },
]

CENTROS_MAPPINGS = {
    "Centros de Costo": {
        "detalle_a_campo": "codigo,procedimiento",
        "detalle_b_campo": "centro_actual,centro_costo",
        "descripcion_template": None,
    },
}

LEGACY_KEY_ORDER = (
    "codigo",
    "vlr_subsidiado",
    "tipo_identificacion",
    "cantidad",
    "centro_costo",
    "codigo_entidad_cobrar",
    "observacion",
    "accion",
    "identificacion",
)


def _strip(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "mapping_completa"}


class TestGenericMapperParity:
    def test_plain_group_byte_equal_legacy_with_flag_on(self):
        from app.services.normalized_rows import build_normalized_rows

        groups = {"Centros de Costo": [dict(i) for i in CENTROS_ITEMS]}
        legacy = build_normalized_rows(
            error_groups={k: [dict(i) for i in v] for k, v in groups.items()},
            responsables_map={},
            use_grupo_mapping=False,
        )
        mapped = build_normalized_rows(
            error_groups={k: [dict(i) for i in v] for k, v in groups.items()},
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=CENTROS_MAPPINGS,
        )
        assert len(mapped) == len(legacy) == 2
        for new_row, old_row in zip(mapped, legacy):
            assert "mapping_completa" not in new_row
            assert _strip(new_row) == old_row

    def test_second_fallback_field_used_when_first_empty(self):
        from app.services.normalized_rows import build_normalized_rows

        rows = build_normalized_rows(
            error_groups={"Centros de Costo": [dict(CENTROS_ITEMS[1])]},
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=CENTROS_MAPPINGS,
        )
        assert rows[0]["detalle"] == "PISO"

    def test_template_descripcion_overrides_problema(self):
        from app.services.normalized_rows import build_normalized_rows

        mappings = {
            "Copago vs Entidad": {
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "Ent: {entidad_cobrar}, Copago: {vlr_copago}",
                "descripcion_template": "Vlr. Copago debe ser 0 cuando entidad no es default",
            },
        }
        rows = build_normalized_rows(
            error_groups={
                "Copago vs Entidad": [
                    {
                        "factura": "F9",
                        "codigo": "c1",
                        "procedimiento": "p1",
                        "problema": "engine text",
                        "entidad_cobrar": "E1",
                        "vlr_copago": 500,
                    }
                ]
            },
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings=mappings,
        )
        assert rows[0]["descripcion"] == "Vlr. Copago debe ser 0 cuando entidad no es default"
        assert rows[0]["detalle"] == "Ent: E1, Copago: 500"
        assert rows[0]["procedimiento"] == "c1 - p1"


class TestKeyOrderStability:
    def test_sparse_item_uses_legacy_key_order(self):
        from app.services import normalized_rows as nr

        assert nr.GENERIC_FALLBACK_KEY_ORDER == LEGACY_KEY_ORDER

    def test_fallback_picks_first_matching_key(self):
        from app.services.normalized_rows import build_normalized_rows

        rows = build_normalized_rows(
            error_groups={
                "Ruta Duplicada": [
                    {"factura": "F5", "problema": "ruta", "cantidad": 3, "accion": "x"}
                ]
            },
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings={
                "Ruta Duplicada": {
                    "detalle_a_campo": None,
                    "detalle_b_campo": None,
                    "descripcion_template": None,
                }
            },
        )
        assert rows[0]["procedimiento"] == "3"
        assert rows[0]["mapping_completa"] is False


class TestCutoverFlag:
    def test_default_on_runs_grupo_mapping(self):
        """Cutover default ON: sin override explícito corre el grupo mapping."""
        from app.services.normalized_rows import build_normalized_rows

        groups = {"Centros de Costo": [dict(i) for i in CENTROS_ITEMS]}
        default = build_normalized_rows(
            error_groups={k: [dict(i) for i in v] for k, v in groups.items()},
            responsables_map={},
            grupo_mappings=CENTROS_MAPPINGS,
        )
        assert default[0]["tipo_error"] == "Centros de Costo"
        assert "mapping_completa" not in default[0]

    def test_explicit_off_runs_legacy_blocks(self):
        from app.services.normalized_rows import build_normalized_rows

        groups = {"Centros de Costo": [dict(i) for i in CENTROS_ITEMS]}
        legacy = build_normalized_rows(
            error_groups={k: [dict(i) for i in v] for k, v in groups.items()},
            responsables_map={},
            use_grupo_mapping=False,
        )
        assert legacy[0]["tipo_error"] == "Centros de Costo"
        assert "mapping_completa" not in legacy[0]

    def test_unknown_group_empty_mapping_flagged(self):
        from app.services.normalized_rows import build_normalized_rows

        rows = build_normalized_rows(
            error_groups={
                "Grupo Inventado": [{"factura": "F7", "problema": "zzz"}]
            },
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings={},
        )
        assert len(rows) == 1
        assert rows[0]["descripcion"] == "zzz"
        assert rows[0]["mapping_completa"] is False


class TestEstanciaItemDetalleFallback:
    """Regla 74 y hermanas: el engine enriquece el item con detalle_b_campo.

    El mapper generico debe leer el fallback a nivel-item cuando el mapping
    de grupo viene vacio (caso prod: detect_all no pasa grupo_mappings).
    """

    def _rows(self, grupo, item):
        from app.services.normalized_rows import build_normalized_rows

        return build_normalized_rows(
            error_groups={grupo: [dict(item)]},
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings={},
        )

    def test_item_detalle_b_estancia_en_grupo_estancias(self):
        rows = self._rows("Estancias", {
            "factura": "F74",
            "problema": "Sala obs menor a 2 horas",
            "regla": "#74",
            "estancia_str": "1d 6h",
            "detalle_b_campo": "estancia_str",
        })
        assert rows[0]["tipo_error"] == "Estancias"
        assert rows[0]["detalle"] == "1d 6h"
        assert rows[0]["regla"] == "#74"
        assert "mapping_completa" not in rows[0]

    def test_item_detalle_b_estancia_en_cantidades(self):
        rows = self._rows("Cantidades", {
            "factura": "F72",
            "problema": "Estancia anomala",
            "regla": "#72",
            "codigo": "5DSB01",
            "estancia_str": "5h",
            "detalle_b_campo": "estancia_str",
        })
        assert rows[0]["detalle"] == "5h"
        assert "mapping_completa" not in rows[0]

    def test_resolve_detalle_estancia_str_directo(self):
        from app.services.normalized_rows import _resolve_detalle

        assert _resolve_detalle({"estancia_str": "2 días 3 horas"}, "estancia_str") == "2 días 3 horas"
        assert _resolve_detalle({}, "estancia_str") == ""

    def test_mapping_de_grupo_gana_sobre_item(self):
        from app.services.normalized_rows import build_normalized_rows

        rows = build_normalized_rows(
            error_groups={"Estancias": [{
                "factura": "F1",
                "problema": "p",
                "codigo": "C9",
                "estancia_str": "9h",
                "detalle_b_campo": "estancia_str",
            }]},
            responsables_map={},
            use_grupo_mapping=True,
            grupo_mappings={"Estancias": {
                "detalle_a_campo": None,
                "detalle_b_campo": "codigo",
                "descripcion_template": None,
            }},
        )
        assert rows[0]["detalle"] == "C9"

    def test_estancias_es_grupo_generico_sin_formatter(self):
        from app.constants.grupo_error import (
            ALL_GRUPO_ERROR_LABELS,
            GRUPO_ESTANCIAS,
            NAMED_FORMATTER_GROUPS,
        )
        from app.services.normalized_rows import GRUPO_FORMATTERS

        assert GRUPO_ESTANCIAS == "Estancias"
        assert GRUPO_ESTANCIAS in ALL_GRUPO_ERROR_LABELS
        assert GRUPO_ESTANCIAS not in NAMED_FORMATTER_GROUPS
        assert GRUPO_ESTANCIAS not in GRUPO_FORMATTERS


class TestEstanciasMigration:
    """Contrato minimo de migrations/020_grupo_error_estancias.sql."""

    def _sql(self):
        from pathlib import Path

        migration = Path(__file__).parents[2] / "migrations" / "020_grupo_error_estancias.sql"
        assert migration.exists(), "falta migrations/020_grupo_error_estancias.sql"
        return " ".join(migration.read_text(encoding="utf-8").split()).lower()

    def test_mueve_regla_74_y_hermanas_a_estancias(self):
        sql = self._sql()
        assert "grupo_error = 'estancias'" in sql
        assert "urg_sala_obs_menor_2_horas" in sql
        assert "detalle_b_campo = 'estancia_str'" in sql
        assert "cantidades" in sql

    def test_no_mueve_regla_61_ni_cups_equivalentes(self):
        sql = self._sql()
        assert "id <> 61" in sql
        assert "cups-equivalentes" in sql
