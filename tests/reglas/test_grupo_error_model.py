"""TDD tests for dominio-grupo-error T1: Regla grouping columns + to_dict.

Spec: rule-declared-grouping — migration adds nullable TEXT
grupo_error, detalle_a_campo, detalle_b_campo, descripcion_template;
Regla.to_dict exposes them; legacy insert without new cols succeeds (NULLs).
"""

from __future__ import annotations


def _make_rule(**overrides):
    from app.models import Regla

    base = {
        "nombre": "centro_costo_test",
        "dominio": "urgencias",
        "estado": "active",
        "version": 1,
    }
    base.update(overrides)
    return Regla(**base)


class TestGrupoErrorColumns:
    def test_legacy_insert_without_new_cols_yields_nulls(self):
        rule = _make_rule()
        assert rule.grupo_error is None
        assert rule.detalle_a_campo is None
        assert rule.detalle_b_campo is None
        assert rule.descripcion_template is None

    def test_new_columns_accept_values(self):
        rule = _make_rule(
            grupo_error="Tipo Identificacion / Edad",
            detalle_a_campo="numero_identificacion",
            detalle_b_campo="edad_detalle",
            descripcion_template="Tipo actual {tipo_actual}",
        )
        assert rule.grupo_error == "Tipo Identificacion / Edad"
        assert rule.detalle_a_campo == "numero_identificacion"
        assert rule.detalle_b_campo == "edad_detalle"
        assert rule.descripcion_template == "Tipo actual {tipo_actual}"


class TestGrupoErrorToDict:
    def test_to_dict_round_trips_grouping_fields(self):
        rule = _make_rule(
            grupo_error="Centros de Costo",
            detalle_a_campo="codigo",
            detalle_b_campo="centro_actual",
            descripcion_template="Centro {centro_actual}",
        )
        data = rule.to_dict()
        assert data["grupo_error"] == "Centros de Costo"
        assert data["detalle_a_campo"] == "codigo"
        assert data["detalle_b_campo"] == "centro_actual"
        assert data["descripcion_template"] == "Centro {centro_actual}"

    def test_to_dict_nulls_for_legacy_rule(self):
        data = _make_rule().to_dict()
        assert data["grupo_error"] is None
        assert data["detalle_a_campo"] is None
        assert data["detalle_b_campo"] is None
        assert data["descripcion_template"] is None
