"""Unit tests for EvidenceCollector — immutable batch insert."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call


class TestEvidenceCollector:
    """Tests for EvidenceCollector.record() and flush_batch()."""

    def test_import_exists(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        assert EvidenceCollector is not None

    def test_record_adds_to_buffer(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        collector = EvidenceCollector()
        collector.record(
            regla_id=1,
            regla_version=1,
            dominio="odontologia",
            factura="F001",
            outcome="MATCH",
            arbol_evaluado={"tipo": "atomic", "operador": "eq", "outcome": True},
            snapshot_fila={"vlr_subsidiado": 1500},
        )
        assert len(collector._buffer) == 1
        assert collector._buffer[0].regla_id == 1
        assert collector._buffer[0].factura == "F001"

    def test_record_multiple_adds_to_buffer(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        collector = EvidenceCollector()
        for i in range(3):
            collector.record(
                regla_id=1,
                regla_version=1,
                dominio="odontologia",
                factura=f"F00{i+1}",
                outcome="MATCH",
                arbol_evaluado={},
                snapshot_fila={},
            )
        assert len(collector._buffer) == 3

    def test_flush_batch_inserts_all(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        session = MagicMock()
        collector = EvidenceCollector()
        collector.record(
            regla_id=1,
            regla_version=1,
            dominio="odontologia",
            factura="F001",
            outcome="MATCH",
            arbol_evaluado={},
            snapshot_fila={},
        )
        collector.record(
            regla_id=1,
            regla_version=1,
            dominio="odontologia",
            factura="F002",
            outcome="NO_MATCH",
            arbol_evaluado={},
            snapshot_fila={},
        )
        collector.flush_batch(session)
        # Verify session.add_all was called
        session.add_all.assert_called_once()
        # Verify session.flush was called
        session.flush.assert_called_once()
        # Buffer should be empty after flush
        assert len(collector._buffer) == 0

    def test_flush_empty_buffer_noop(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        session = MagicMock()
        collector = EvidenceCollector()
        collector.flush_batch(session)
        session.add_all.assert_not_called()
        session.flush.assert_not_called()

    def test_evidence_record_has_all_fields(self):
        from app.services.engine.evidence_collector import EvidenceCollector
        collector = EvidenceCollector()
        collector.record(
            regla_id=42,
            regla_version=3,
            dominio="odontologia",
            factura="FAC-001",
            param_config_id=0,
            outcome="MATCH",
            arbol_evaluado=[{"node": "root", "outcome": True}],
            snapshot_fila={"valor": 100},
            snapshot_referencia={"contract": "C1"},
            error_mensaje=None,
        )
        record = collector._buffer[0]
        d = record.to_dict()
        assert d["regla_id"] == 42
        assert d["regla_version"] == 3
        assert d["dominio"] == "odontologia"
        assert d["factura"] == "FAC-001"
        assert d["param_config_id"] == 0
        assert d["outcome"] == "MATCH"
        assert d["arbol_evaluado"] == [{"node": "root", "outcome": True}]
        assert d["snapshot_fila"] == {"valor": 100}
        assert d["snapshot_referencia"] == {"contract": "C1"}
        assert d["error_mensaje"] is None
