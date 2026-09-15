"""Unit tests for RuleResolver — loads active rules by domain."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


def _mock_session_with_rules(rules: list):
    """Create a mock session whose query(...).filter(...)...all() returns rules."""
    session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value = rules
    session.query.return_value = mock_query
    return session


def _real_session(rowspec: list[tuple]):
    """Real SQLite session with Regla rows: (nombre, dominio, estado, activo, version, prioridad)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from app.models import Regla
    import app.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    for nombre, dominio, estado, activo, version, prioridad in rowspec:
        session.add(
            Regla(
                nombre=nombre, dominio=dominio, estado=estado,
                version=version, prioridad=prioridad, severidad="error",
                activo=activo,
            )
        )
    session.commit()
    return session


class TestRuleResolver:
    """Tests for RuleResolver.resolve(domain, session)."""

    def test_import_exists(self):
        from app.services.engine.rule_resolver import RuleResolver
        assert RuleResolver is not None

    def test_resolve_returns_empty_for_no_rules(self):
        from app.services.engine.rule_resolver import RuleResolver
        session = _mock_session_with_rules([])
        resolver = RuleResolver()
        result = resolver.resolve("odontologia", session)
        assert result == []

    def test_resolve_filters_by_domain_and_activo_true(self):
        from app.services.engine.rule_resolver import RuleResolver
        from app.models import Regla

        r1 = Regla(nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        r2 = Regla(nombre="r2", dominio="odontologia", estado="active", prioridad=20)
        session = _mock_session_with_rules([r1, r2])

        resolver = RuleResolver()
        result = resolver.resolve("odontologia", session)
        assert len(result) == 2
        assert result[0].nombre == "r1"
        assert result[1].nombre == "r2"

    def test_resolve_includes_retired_when_activo_true(self):
        """Single-flag cutover: retired+activo=True still resolves (no estado filter)."""
        from app.services.engine.rule_resolver import RuleResolver

        engine_session = _real_session([
            ("drift_rule", "odontologia", "retired", True, 1, 10),
        ])
        try:
            result = RuleResolver().resolve("odontologia", engine_session)
        finally:
            engine_session.close()
        assert [r.nombre for r in result] == ["drift_rule"]

    def test_resolve_excludes_activo_false(self):
        """Single-flag cutover: activo=False never resolves, whatever estado says."""
        from app.services.engine.rule_resolver import RuleResolver

        engine_session = _real_session([
            ("off_rule", "odontologia", "active", False, 1, 10),
            ("off_retired", "odontologia", "retired", False, 1, 20),
        ])
        try:
            result = RuleResolver().resolve("odontologia", engine_session)
        finally:
            engine_session.close()
        assert result == []

    def test_resolve_sorts_by_priority(self):
        from app.services.engine.rule_resolver import RuleResolver
        from app.models import Regla

        r1 = Regla(nombre="low", dominio="odontologia", estado="active", prioridad=100)
        r2 = Regla(nombre="high", dominio="odontologia", estado="active", prioridad=10)
        r3 = Regla(nombre="mid", dominio="odontologia", estado="active", prioridad=50)
        session = _mock_session_with_rules([r2, r3, r1])

        resolver = RuleResolver()
        result = resolver.resolve("odontologia", session)
        assert result[0].prioridad == 10
        assert result[1].prioridad == 50
        assert result[2].prioridad == 100

    def test_different_domain_returns_empty(self):
        from app.services.engine.rule_resolver import RuleResolver
        session = _mock_session_with_rules([])
        resolver = RuleResolver()
        result = resolver.resolve("urgencias", session)
        assert result == []
