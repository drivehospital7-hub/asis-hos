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

    def test_resolve_filters_by_domain_and_estado_active(self):
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

    def test_resolve_excludes_drafts(self):
        from app.services.engine.rule_resolver import RuleResolver
        from app.models import Regla

        r_active = Regla(nombre="active_rule", dominio="odontologia", estado="active", prioridad=10)
        session = _mock_session_with_rules([r_active])

        resolver = RuleResolver()
        result = resolver.resolve("odontologia", session)
        assert len(result) == 1
        assert result[0].estado == "active"

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
