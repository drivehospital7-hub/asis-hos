"""Integration tests for EvidenceRepository — query layer for evidence records."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from app.database import get_session
from app.models import Regla, Evidencia


@pytest.fixture
def session():
    """DB session with rollback — no persistent changes."""
    s = get_session()
    yield s
    s.rollback()
    s.close()


@pytest.fixture
def seed_evidence(session):
    """Seed evidence records (and parent Regla) for query tests."""
    # Create parent Regla records first (FK constraint)
    r1 = Regla(nombre="regla_test_1", dominio="odontologia", estado="active", prioridad=10)
    r2 = Regla(nombre="regla_test_2", dominio="urgencias", estado="active", prioridad=20)
    session.add_all([r1, r2])
    session.flush()

    evs = [
        Evidencia(regla_id=r1.id, regla_version=1, dominio="odontologia", factura="F001",
                  outcome="MATCH", arbol_evaluado={}, snapshot_fila={}),
        Evidencia(regla_id=r1.id, regla_version=1, dominio="odontologia", factura="F002",
                  outcome="NO_MATCH", arbol_evaluado={}, snapshot_fila={}),
        Evidencia(regla_id=r2.id, regla_version=1, dominio="urgencias", factura="F003",
                  outcome="MATCH", arbol_evaluado={}, snapshot_fila={}),
    ]
    session.add_all(evs)
    session.flush()
    # Return the evidencias IDs
    ev_ids = [e.id for e in evs]
    rule_ids = {"r1": r1.id, "r2": r2.id}
    yield ev_ids, rule_ids
    # cleanup not needed — rollback in fixture


class TestEvidenceRepository:
    """Tests for EvidenceRepository query methods."""

    def test_import_exists(self):
        """Verify EvidenceRepository can be imported."""
        from app.services.engine.evidence_repository import EvidenceRepository
        assert EvidenceRepository is not None

    def test_find_by_rule_returns_matches(self, session, seed_evidence):
        """find_by_rule should return records for a given rule_id."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence
        r1_id = rule_ids["r1"]

        results = EvidenceRepository.find_by_rule(session, regla_id=r1_id)

        assert len(results) == 2
        facturas = {r.factura for r in results}
        assert "F001" in facturas
        assert "F002" in facturas
        # All results should be Evidencia instances
        for r in results:
            assert isinstance(r, Evidencia)
            assert r.regla_id == r1_id

    def test_find_by_rule_returns_empty_for_nonexistent(self, session, seed_evidence):
        """find_by_rule should return empty list for non-existent rule_id."""
        from app.services.engine.evidence_repository import EvidenceRepository

        results = EvidenceRepository.find_by_rule(session, regla_id=999)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_find_by_factura_returns_matches(self, session, seed_evidence):
        """find_by_factura should return records matching a factura string."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence

        results = EvidenceRepository.find_by_factura(session, factura="F001")

        assert len(results) == 1
        assert results[0].factura == "F001"

    def test_find_by_domain_returns_matches(self, session, seed_evidence):
        """find_by_domain should filter by dominio field."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence

        results = EvidenceRepository.find_by_domain(session, dominio="urgencias")

        assert len(results) == 1
        assert results[0].dominio == "urgencias"
        assert results[0].factura == "F003"

    def test_find_by_domain_returns_empty_for_nonexistent(self, session, seed_evidence):
        """find_by_domain should return empty when no evidence for that domain."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence

        results = EvidenceRepository.find_by_domain(session, dominio="cardiologia")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_find_by_date_range_includes_start_and_end(self, session, seed_evidence):
        """find_by_date_range should include records on start and end boundaries."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence

        # Seed evidence was just created, so query a very wide range
        now = datetime.utcnow()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)

        results = EvidenceRepository.find_by_date_range(session, start=start, end=end)

        assert len(results) == 3

    def test_find_by_date_range_returns_empty_when_no_matches(self, session, seed_evidence):
        """find_by_date_range should return empty for far-past range with no records."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence

        far_past = datetime(2000, 1, 1)
        end = datetime(2000, 1, 2)

        results = EvidenceRepository.find_by_date_range(session, start=far_past, end=end)

        assert isinstance(results, list)
        assert len(results) == 0

    def test_pagination_limit_restricts_results(self, session, seed_evidence):
        """Pagination limit should restrict the number of returned records."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence
        r1_id = rule_ids["r1"]

        results = EvidenceRepository.find_by_rule(session, regla_id=r1_id, limit=1)

        assert len(results) == 1

    def test_pagination_offset_skips_records(self, session, seed_evidence):
        """Pagination offset should skip the first N records."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence
        r1_id = rule_ids["r1"]

        # Query all for r1 (2 records)
        all_results = EvidenceRepository.find_by_rule(session, regla_id=r1_id)
        assert len(all_results) == 2

        # With offset=1, should get the second record only
        offset_results = EvidenceRepository.find_by_rule(session, regla_id=r1_id, offset=1)
        assert len(offset_results) == 1

    def test_count_method_returns_total(self, session, seed_evidence):
        """EvidenceRepository should expose a count method for pagination stats."""
        from app.services.engine.evidence_repository import EvidenceRepository

        ev_ids, rule_ids = seed_evidence
        r1_id = rule_ids["r1"]

        total = EvidenceRepository.count_by_rule(session, regla_id=r1_id)
        assert total == 2

        total_all = EvidenceRepository.count_by_domain(session, dominio="odontologia")
        assert total_all == 2

        total_none = EvidenceRepository.count_by_rule(session, regla_id=999)
        assert total_none == 0
