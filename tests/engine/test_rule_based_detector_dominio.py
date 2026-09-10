"""TDD tests for dominio-grupo-error T5: RuleBasedDetector dominio ctor param.

Spec dominio threading: detector MUST accept dominio; detect() forwards it
to evaluate_sheet(nombre, dominio); detector without dominio fails fast.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


class TestDetectorDominioCtor:
    def test_requires_dominio_argument(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector

        session = MagicMock()
        with pytest.raises(TypeError):
            RuleBasedDetector("valores_decimales", session)  # type: ignore[call-arg]

    def test_stores_dominio(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector

        session = MagicMock()
        detector = RuleBasedDetector(
            "valores_decimales", session, dominio="urgencias"
        )
        assert detector._dominio == "urgencias"

    def test_detect_forwards_dominio_to_engine(self):
        from app.services.engine.rule_based_detector import RuleBasedDetector

        session = MagicMock()
        detector = RuleBasedDetector(
            "codigo_entidad", session, dominio="odontologia"
        )
        with patch.object(
            detector._engine, "evaluate_sheet", return_value=[]
        ) as evaluate:
            detector.detect(None, {"numero_factura": 0}, persist=False)
            assert evaluate.called
            _, kwargs = evaluate.call_args
            assert kwargs.get("dominio") == "odontologia"
            assert kwargs.get("rule_name") == "codigo_entidad"
