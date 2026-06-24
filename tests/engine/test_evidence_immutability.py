"""Tests for Evidencia immutability guard — UPDATE/DELETE are forbidden.

Verifies that SQLAlchemy ORM-level event listeners block mutation of evidence
records. Bulk operations (session.query().update()) bypass ORM events per
SQLAlchemy docs — a DB-level trigger will be added in F2 for full coverage.
"""

from __future__ import annotations

import pytest

from app.database import get_session
from app.models import Regla, Evidencia


@pytest.fixture
def session_with_evidence():
    """Create a session with one Evidencia record (and parent Regla)."""
    s = get_session()
    r = Regla(nombre="immutability_test_rule", dominio="test", estado="active", prioridad=10)
    s.add(r)
    s.flush()

    ev = Evidencia(
        regla_id=r.id, regla_version=1, dominio="test",
        factura="IMM001", outcome="MATCH",
        arbol_evaluado={}, snapshot_fila={},
    )
    s.add(ev)
    s.flush()
    ev_id = ev.id

    yield s, ev_id

    s.rollback()
    s.close()


class TestEvidenciaImmutability:
    """Tests that ORM-level UPDATE and DELETE on Evidencia raise RuntimeError."""

    def test_update_evidence_raises_runtime_error(self, session_with_evidence):
        """Modifying an attribute on a tracked Evidencia instance should raise."""
        s, ev_id = session_with_evidence

        ev = s.query(Evidencia).filter(Evidencia.id == ev_id).first()
        assert ev is not None

        ev.outcome = "NO_MATCH"

        with pytest.raises(RuntimeError, match="immutable"):
            s.flush()

    def test_delete_evidence_raises_runtime_error(self, session_with_evidence):
        """Deleting a tracked Evidencia instance should raise RuntimeError."""
        s, ev_id = session_with_evidence

        ev = s.query(Evidencia).filter(Evidencia.id == ev_id).first()
        assert ev is not None

        s.delete(ev)

        with pytest.raises(RuntimeError, match="immutable"):
            s.flush()
