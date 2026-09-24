"""Reglas multi-dominio: migration 023, model, and service scope (strict TDD).

Covers spec multi-dominio-scope:
- 023 SQL-text (precedent: tests/bre/test_migration_022_profesional_codigo.py)
- ReglaDominio model + to_dict dominios sorted (+ legacy dominio unchanged)
- Service: create/update dominios validation, legacy fallback, mirror,
  duplicate/version copy, list_rules ∈ semantics (transversals included).
"""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path("migrations")
MIGRATION = MIGRATIONS_DIR / "023_regla_dominios.sql"
ROLLBACK = MIGRATIONS_DIR / "023_regla_dominios_rollback.sql"


def _text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.strip().startswith("--")]


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


def _make_rule(session, nombre, dominio="odontologia", **kw):
    from app.models import Regla

    kw.setdefault("estado", "active")
    kw.setdefault("version", 1)
    kw.setdefault("prioridad", 100)
    kw.setdefault("severidad", "error")
    kw.setdefault("activo", True)
    rule = Regla(nombre=nombre, dominio=dominio, **kw)
    session.add(rule)
    session.commit()
    return rule


# ─── Migration 023 SQL-text ──────────────────────────────────────────


class TestMigration023SqlText:
    def test_023_files_exist(self) -> None:
        assert MIGRATION.exists(), "023 migration file missing"
        assert ROLLBACK.exists(), "023 rollback file missing"

    def test_023_planned_after_022(self) -> None:
        from run_migrations import plan_migrations

        planned = [
            p.stem
            for p in plan_migrations(MIGRATIONS_DIR, applied=set(), include_evidence=False)
        ]
        assert "022_seed_profesional_codigo_map" in planned
        assert "023_regla_dominios" in planned
        assert planned.index("022_seed_profesional_codigo_map") < planned.index(
            "023_regla_dominios"
        )

    def test_023_not_treated_as_evidence_seed(self) -> None:
        from run_migrations import should_skip_evidence

        assert should_skip_evidence(MIGRATION.name, include_evidence=False) is False
        assert should_skip_evidence(MIGRATION.name, include_evidence=True) is False

    def test_023_creates_bridge_table_with_pk(self) -> None:
        code = "\n".join(_code_lines(_text()))
        assert re.search(r"CREATE TABLE.*regla_dominios", code, re.IGNORECASE)
        assert re.search(
            r"PRIMARY KEY\s*\(\s*regla_id\s*,\s*dominio\s*\)", code, re.IGNORECASE
        )
        assert re.search(r"REFERENCES\s+reglas\s*\(\s*id\s*\)", code, re.IGNORECASE)
        assert re.search(r"ON DELETE CASCADE", code, re.IGNORECASE)

    def test_023_creates_dominio_index(self) -> None:
        code = "\n".join(_code_lines(_text()))
        assert re.search(
            r"CREATE INDEX.*regla_dominios\s*\(\s*dominio\s*,\s*regla_id\s*\)",
            code,
            re.IGNORECASE | re.DOTALL,
        )

    def test_023_guarded_backfill_from_reglas(self) -> None:
        code = "\n".join(_code_lines(_text()))
        assert re.search(
            r"INSERT INTO regla_dominios.*SELECT\s+id\s*,\s*dominio\s+FROM\s+reglas",
            code,
            re.IGNORECASE | re.DOTALL,
        )
        assert "NOT EXISTS" in code

    def test_023_no_hardcoded_rule_ids_or_tx_control(self) -> None:
        code = "\n".join(_code_lines(_text()))
        assert re.search(r"regla_id\s*=\s*\d+", code) is None
        assert re.search(r"^\s*BEGIN\s*;", code, re.MULTILINE) is None
        assert re.search(r"^\s*COMMIT\s*;", code, re.MULTILINE) is None

    def test_023_rollback_drops_bridge_only(self) -> None:
        code = "\n".join(
            ln
            for ln in ROLLBACK.read_text(encoding="utf-8").splitlines()
            if not ln.strip().startswith("--")
        )
        assert re.search(r"DROP TABLE.*regla_dominios", code, re.IGNORECASE)
        assert "reglas" not in code.replace("regla_dominios", "")


# ─── Vocabulary constant ─────────────────────────────────────────────


class TestReglaDominiosVocabulario:
    def test_vocabulario_has_8_values(self) -> None:
        from app.constants.base import REGLA_DOMINIOS_VALIDOS

        assert REGLA_DOMINIOS_VALIDOS == frozenset({
            "urgencias", "hospitalizacion", "odontologia", "equipos_basicos",
            "transversal", "farmacia", "intramural", "ambulatoria",
        })


# ─── Model: ReglaDominio + to_dict ───────────────────────────────────


class TestReglaDominioModel:
    def test_to_dict_returns_sorted_dominios(self) -> None:
        from app.models import ReglaDominio

        session = _session()
        try:
            rule = _make_rule(session, "r_multi", dominio="urgencias")
            session.add_all([
                ReglaDominio(regla_id=rule.id, dominio="urgencias"),
                ReglaDominio(regla_id=rule.id, dominio="hospitalizacion"),
            ])
            session.commit()
            session.expire_all()
            fresh = session.query(type(rule)).filter_by(id=rule.id).one()
            assert fresh.to_dict()["dominios"] == ["hospitalizacion", "urgencias"]
            assert fresh.to_dict()["dominio"] == "urgencias"
        finally:
            session.close()

    def test_scope_entries_unique_per_rule(self) -> None:
        from sqlalchemy.exc import IntegrityError

        from app.models import ReglaDominio

        session = _session()
        try:
            rule = _make_rule(session, "r_dup_scope", dominio="urgencias")
            session.add(ReglaDominio(regla_id=rule.id, dominio="urgencias"))
            session.commit()
            session.add(ReglaDominio(regla_id=rule.id, dominio="urgencias"))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
            else:
                raise AssertionError("duplicate scope insert must be rejected")
        finally:
            session.close()

    def test_backfill_shape_covers_every_rule(self) -> None:
        from app.models import Regla, ReglaDominio

        session = _session()
        try:
            r1 = _make_rule(session, "r_bf_1", dominio="urgencias")
            r2 = _make_rule(session, "r_bf_2", dominio="odontologia")
            session.execute(
                ReglaDominio.__table__.insert().from_select(
                    ["regla_id", "dominio"],
                    session.query(Regla.id, Regla.dominio),
                )
            )
            session.commit()
            rows = (
                session.query(ReglaDominio)
                .order_by(ReglaDominio.regla_id)
                .all()
            )
            assert [(r.regla_id, r.dominio) for r in rows] == [
                (r1.id, "urgencias"),
                (r2.id, "odontologia"),
            ]
        finally:
            session.close()


# ─── Service: create/update/duplicate/version/list ───────────────────


class TestRuleServiceDominios:
    def test_create_with_multiple_dominios(self) -> None:
        from app.services.reglas.rule_service import create_rule

        session = _session()
        try:
            result = create_rule(session, {
                "nombre": "r_svc_multi",
                "dominio": "urgencias",
                "dominios": ["urgencias", "hospitalizacion"],
            })
            assert result["dominios"] == ["hospitalizacion", "urgencias"]
            assert result["dominio"] == "hospitalizacion"
            from app.models import ReglaDominio

            rows = (
                session.query(ReglaDominio)
                .filter(ReglaDominio.regla_id == result["id"])
                .order_by(ReglaDominio.dominio)
                .all()
            )
            assert [r.dominio for r in rows] == ["hospitalizacion", "urgencias"]
        finally:
            session.close()

    def test_create_rejects_empty_dominios_with_rollback(self) -> None:
        import pytest

        from app.models import Regla
        from app.services.reglas.rule_service import create_rule

        session = _session()
        try:
            before = session.query(Regla).count()
            with pytest.raises(ValueError):
                create_rule(session, {"nombre": "r_empty", "dominios": []})
            assert session.query(Regla).count() == before
        finally:
            session.close()

    def test_create_rejects_invalid_dominio_with_rollback(self) -> None:
        import pytest

        from app.models import Regla
        from app.services.reglas.rule_service import create_rule

        session = _session()
        try:
            before = session.query(Regla).count()
            with pytest.raises(ValueError):
                create_rule(session, {
                    "nombre": "r_bad", "dominios": ["urgencias", "no_existe"],
                })
            assert session.query(Regla).count() == before
        finally:
            session.close()

    def test_legacy_single_dominio_caller_keeps_working(self) -> None:
        from app.services.reglas.rule_service import create_rule

        session = _session()
        try:
            result = create_rule(session, {
                "nombre": "r_legacy", "dominio": "odontologia",
            })
            assert result["dominios"] == ["odontologia"]
            assert result["dominio"] == "odontologia"
        finally:
            session.close()

    def test_update_dominios_rewrites_scope_and_mirror(self) -> None:
        from app.services.reglas.rule_service import create_rule, update_rule

        session = _session()
        try:
            created = create_rule(session, {
                "nombre": "r_upd", "dominios": ["urgencias"],
            })
            updated = update_rule(
                session, created["id"],
                {"dominios": ["odontologia", "farmacia"]},
                responsible="admin",
            )
            assert updated["dominios"] == ["farmacia", "odontologia"]
            assert updated["dominio"] == "farmacia"
        finally:
            session.close()

    def test_update_rejects_invalid_dominios(self) -> None:
        import pytest

        from app.services.reglas.rule_service import create_rule, update_rule

        session = _session()
        try:
            created = create_rule(session, {
                "nombre": "r_upd_bad", "dominios": ["urgencias"],
            })
            with pytest.raises(ValueError):
                update_rule(
                    session, created["id"], {"dominios": ["zzz"]},
                    responsible="admin",
                )
        finally:
            session.close()

    def test_duplicate_and_version_copy_scope(self) -> None:
        from app.services.reglas.rule_service import (
            create_rule,
            create_version,
            duplicate_rule,
            get_rule,
        )

        session = _session()
        try:
            created = create_rule(session, {
                "nombre": "r_copy_src",
                "dominios": ["urgencias", "hospitalizacion"],
            })
            dup = duplicate_rule(session, created["id"])
            assert dup["dominios"] == ["hospitalizacion", "urgencias"]
            ver = create_version(session, created["id"])
            assert get_rule(session, ver["id"])["dominios"] == [
                "hospitalizacion", "urgencias",
            ]
        finally:
            session.close()

    def test_update_legacy_dominio_rewrites_single_scope(self) -> None:
        from app.services.reglas.rule_service import create_rule, update_rule

        session = _session()
        try:
            created = create_rule(session, {
                "nombre": "r_upd_leg", "dominios": ["urgencias"],
            })
            updated = update_rule(
                session, created["id"], {"dominio": "farmacia"},
                responsible="admin",
            )
            assert updated["dominios"] == ["farmacia"]
            assert updated["dominio"] == "farmacia"
        finally:
            session.close()

    def test_update_dominios_absent_leaves_scope_unchanged(self) -> None:
        from app.services.reglas.rule_service import create_rule, update_rule

        session = _session()
        try:
            created = create_rule(session, {
                "nombre": "r_upd_keep",
                "dominios": ["urgencias", "farmacia"],
            })
            updated = update_rule(
                session, created["id"], {"prioridad": 5},
                responsible="admin",
            )
            assert updated["dominios"] == ["farmacia", "urgencias"]
        finally:
            session.close()

    def test_list_rules_dominio_includes_transversal(self) -> None:
        from app.services.reglas.rule_service import create_rule, list_rules

        session = _session()
        try:
            create_rule(session, {"nombre": "r_l_urg", "dominios": ["urgencias"]})
            create_rule(session, {"nombre": "r_l_trans", "dominios": ["transversal"]})
            create_rule(session, {"nombre": "r_l_odon", "dominios": ["odontologia"]})
            names = sorted(r["nombre"] for r in list_rules(session, dominio="urgencias"))
            assert names == ["r_l_trans", "r_l_urg"]
        finally:
            session.close()
