"""TDD tests for dominio-grupo-error T7: rule_service grouping fields.

Spec manageable grouping metadata: UPDATABLE_FIELDS (_MUTABLE_FIELDS) MUST
expose the 4 grouping fields; update + duplicate preserve them; NULL
allowed during rollout.
"""

from __future__ import annotations


def _session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _create_rule(db):
    from app.services.reglas import rule_service

    return rule_service.create_rule(db, {"nombre": "grupo_test", "dominio": "urgencias"})


class TestMutableFields:
    def test_grouping_fields_updatable(self):
        from app.services.reglas import rule_service

        for field in (
            "grupo_error",
            "detalle_a_campo",
            "detalle_b_campo",
            "descripcion_template",
        ):
            assert field in rule_service._MUTABLE_FIELDS, f"{field} not updatable"

    def test_update_preserves_grouping_fields(self):
        from app.services.reglas import rule_service

        db = _session()
        created = _create_rule(db)
        updated = rule_service.update_rule(
            db,
            created["id"],
            {
                "grupo_error": "Centros de Costo",
                "detalle_a_campo": "codigo,procedimiento",
                "detalle_b_campo": "centro_actual,centro_costo",
                "descripcion_template": None,
            },
        )
        assert updated["grupo_error"] == "Centros de Costo"
        assert updated["detalle_a_campo"] == "codigo,procedimiento"
        assert updated["detalle_b_campo"] == "centro_actual,centro_costo"
        assert updated["descripcion_template"] is None

    def test_null_grouping_allowed_during_rollout(self):
        from app.services.reglas import rule_service

        db = _session()
        created = _create_rule(db)
        updated = rule_service.update_rule(db, created["id"], {"descripcion": "x"})
        assert updated["grupo_error"] is None

    def test_duplicate_copies_grouping_fields(self):
        from app.services.reglas import rule_service

        db = _session()
        created = _create_rule(db)
        rule_service.update_rule(
            db,
            created["id"],
            {
                "grupo_error": "Tipo Identificacion / Edad",
                "detalle_a_campo": "numero_identificacion",
                "detalle_b_campo": "edad_detalle",
                "descripcion_template": "Tipo {tipo_actual}",
            },
        )
        dup = rule_service.duplicate_rule(db, created["id"])
        assert dup["grupo_error"] == "Tipo Identificacion / Edad"
        assert dup["detalle_a_campo"] == "numero_identificacion"
        assert dup["detalle_b_campo"] == "edad_detalle"
        assert dup["descripcion_template"] == "Tipo {tipo_actual}"
