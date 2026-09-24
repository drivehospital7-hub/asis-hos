"""Engine multi-dominio resolution (strict TDD).

Spec multi-dominio-scope / design D3:
- rule_matches_domain EXISTS helper shared by resolver, domain_detection,
  and engine._load_rule_by_name (exact-first ordering preserved).
- Scope-less rows fall back to legacy single-column semantics.
"""
from __future__ import annotations


def _session_with_scope(rowspec, scopespec=()):
    """Real SQLite session.

    rowspec: (nombre, dominio legacy, estado, activo, prioridad[, version]).
    scopespec: {nombre: [dominios]} — rules absent here get legacy fallback
      (zero bridge rows) unless scopespec maps them to an explicit list.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import Regla, ReglaDominio
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    by_name: dict[str, list] = {}
    for row in rowspec:
        nombre, dominio, estado, activo, prioridad = row[:5]
        version = row[5] if len(row) > 5 else 1
        regla = Regla(
            nombre=nombre, dominio=dominio, estado=estado,
            version=version, prioridad=prioridad, severidad="error",
            activo=activo,
        )
        session.add(regla)
        session.flush()
        by_name.setdefault(nombre, []).append(regla)
    session.commit()
    for nombre, dominios in scopespec:
        for regla in by_name.get(nombre, []):
            for dom in dominios:
                session.add(ReglaDominio(regla_id=regla.id, dominio=dom))
    session.commit()
    return session


class TestRuleMatchesDomainHelper:
    def test_helper_exists_and_is_portable_exists(self) -> None:
        from sqlalchemy import exists as _exists

        from app.services.engine.rule_resolver import rule_matches_domain
        from app.models import Regla

        clause = rule_matches_domain(Regla.id, "urgencias")
        assert isinstance(clause, _exists.__class__) or hasattr(clause, "element")


class TestResolverMultiDominio:
    def test_multi_scope_loads_in_both_domains_only(self) -> None:
        from app.services.engine.rule_resolver import RuleResolver

        session = _session_with_scope(
            [("prof_trab", "hospitalizacion", "active", True, 10)],
            scopespec=[("prof_trab", ["urgencias", "hospitalizacion"])],
        )
        try:
            assert [r.nombre for r in RuleResolver().resolve("hospitalizacion", session)] == [
                "prof_trab"
            ]
            assert [r.nombre for r in RuleResolver().resolve("urgencias", session)] == [
                "prof_trab"
            ]
            assert RuleResolver().resolve("odontologia", session) == []
        finally:
            session.close()

    def test_transversal_scope_matches_all(self) -> None:
        from app.services.engine.rule_resolver import RuleResolver

        session = _session_with_scope(
            [("decimales", "transversal", "active", True, 10)],
            scopespec=[("decimales", ["transversal"])],
        )
        try:
            for domain in ("urgencias", "odontologia", "intramural"):
                assert [r.nombre for r in RuleResolver().resolve(domain, session)] == [
                    "decimales"
                ]
        finally:
            session.close()

    def test_single_scope_unaffected(self) -> None:
        from app.services.engine.rule_resolver import RuleResolver

        session = _session_with_scope(
            [("solo_odon", "odontologia", "active", True, 10)],
            scopespec=[("solo_odon", ["odontologia"])],
        )
        try:
            assert len(RuleResolver().resolve("odontologia", session)) == 1
            assert RuleResolver().resolve("urgencias", session) == []
        finally:
            session.close()

    def test_scope_less_row_falls_back_to_legacy(self) -> None:
        from app.services.engine.rule_resolver import RuleResolver

        session = _session_with_scope(
            [("legacy_r", "odontologia", "active", True, 10)],
            scopespec=[],
        )
        try:
            assert [r.nombre for r in RuleResolver().resolve("odontologia", session)] == [
                "legacy_r"
            ]
            assert RuleResolver().resolve("urgencias", session) == []
        finally:
            session.close()

    def test_inactive_scope_row_never_loads(self) -> None:
        from app.services.engine.rule_resolver import RuleResolver

        session = _session_with_scope(
            [("off_r", "odontologia", "active", False, 10)],
            scopespec=[("off_r", ["odontologia"])],
        )
        try:
            assert RuleResolver().resolve("odontologia", session) == []
        finally:
            session.close()


class TestLoadRuleByNameMultiDominio:
    def test_exact_scope_beats_transversal_version(self) -> None:
        from app.services.engine.engine import RuleEvaluationEngine

        session = _session_with_scope(
            [
                ("codigo_entidad", "odontologia", "active", True, 10, 2),
                ("codigo_entidad", "transversal", "active", True, 20, 9),
            ],
            scopespec=[
                ("codigo_entidad", ["odontologia", "transversal"]),
            ],
        )
        try:
            # per-row scope would merge; rebuild exact split instead
            from app.models import Regla, ReglaDominio

            session.query(ReglaDominio).delete()
            session.commit()
            exact = session.query(Regla).filter(
                Regla.nombre == "codigo_entidad",
                Regla.dominio == "odontologia",
            ).one()
            trans = session.query(Regla).filter(
                Regla.nombre == "codigo_entidad",
                Regla.dominio == "transversal",
            ).one()
            session.add(ReglaDominio(regla_id=exact.id, dominio="odontologia"))
            session.add(ReglaDominio(regla_id=trans.id, dominio="transversal"))
            session.commit()
            loaded = RuleEvaluationEngine(session)._load_rule_by_name(
                "codigo_entidad", "odontologia"
            )
            assert loaded is not None
            assert loaded.dominio == "odontologia"
            assert loaded.version == 2
        finally:
            session.close()

    def test_scope_less_fallback_uses_legacy_column(self) -> None:
        from app.services.engine.engine import RuleEvaluationEngine

        session = _session_with_scope(
            [("legacy_one", "odontologia", "active", True, 10)],
            scopespec=[],
        )
        try:
            engine = RuleEvaluationEngine(session)
            assert engine._load_rule_by_name("legacy_one", "odontologia") is not None
            assert engine._load_rule_by_name("legacy_one", "urgencias") is None
        finally:
            session.close()


class TestSelectedRulesSimulatorScope:
    def test_load_selected_rules_uses_scope_semantics(self) -> None:
        from app.services.engine.domain_detection import _load_selected_rules

        session = _session_with_scope(
            [
                ("multi_r", "hospitalizacion", "active", False, 10),
                ("other_r", "odontologia", "active", False, 20),
            ],
            scopespec=[
                ("multi_r", ["urgencias", "hospitalizacion"]),
                ("other_r", ["odontologia"]),
            ],
        )
        try:
            from app.models import Regla

            ids = frozenset(r.id for r in session.query(Regla).all())
            loaded = _load_selected_rules(session, "urgencias", ids)
            assert [r.nombre for r in loaded] == ["multi_r"]
        finally:
            session.close()
