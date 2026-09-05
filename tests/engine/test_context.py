"""Unit tests for EvaluationContext dataclass."""

from __future__ import annotations

import pytest


class TestEvaluationContext:
    """EvaluationContext carries row data, reference data, and session for rule evaluation."""

    def test_import_exists(self):
        """Verify EvaluationContext can be imported."""
        from app.services.engine.context import EvaluationContext
        assert EvaluationContext is not None

    def test_default_fields_are_none(self):
        """All optional fields default to None or empty."""
        from app.services.engine.context import EvaluationContext
        ctx = EvaluationContext()
        assert ctx.invoice_data is None
        assert ctx.patient_data is None
        assert ctx.reference_data is None
        assert ctx.indices is None
        assert ctx.session is None

    def test_can_set_invoice_data(self):
        from app.services.engine.context import EvaluationContext
        ctx = EvaluationContext(
            invoice_data={"vlr_subsidiado": 1500, "vlr_procedimiento": 2000}
        )
        assert ctx.invoice_data["vlr_subsidiado"] == 1500
        assert ctx.invoice_data["vlr_procedimiento"] == 2000

    def test_can_set_patient_data(self):
        from app.services.engine.context import EvaluationContext
        ctx = EvaluationContext(patient_data={"edad": 35, "tipo_doc": "CC"})
        assert ctx.patient_data["edad"] == 35
        assert ctx.patient_data["tipo_doc"] == "CC"

    def test_can_set_reference_data(self):
        from app.services.engine.context import EvaluationContext
        ctx = EvaluationContext(reference_data={"contracts": [], "procedures": {}})
        assert ctx.reference_data["contracts"] == []

    def test_can_set_indices(self):
        from app.services.engine.context import EvaluationContext
        ctx = EvaluationContext(indices={"numero_factura": 0, "vlr_subsidiado": 3})
        assert ctx.indices["numero_factura"] == 0

    def test_can_set_session(self):
        from app.services.engine.context import EvaluationContext
        mock_session = object()
        ctx = EvaluationContext(session=mock_session)
        assert ctx.session is mock_session

    def test_is_dataclass(self):
        """Verify EvaluationContext is a dataclass (supports equality)."""
        from app.services.engine.context import EvaluationContext
        ctx1 = EvaluationContext(invoice_data={"a": 1})
        ctx2 = EvaluationContext(invoice_data={"a": 1})
        ctx3 = EvaluationContext(invoice_data={"b": 2})
        assert ctx1 == ctx2
        assert ctx1 != ctx3

    def test_has_required_fields_per_design(self):
        """Fields match design spec: invoice_data, patient_data, reference_data, indices, session."""
        from app.services.engine.context import EvaluationContext
        import dataclasses
        fields = {f.name for f in dataclasses.fields(EvaluationContext)}
        assert "invoice_data" in fields
        assert "patient_data" in fields
        assert "reference_data" in fields
        assert "indices" in fields
        assert "session" in fields
