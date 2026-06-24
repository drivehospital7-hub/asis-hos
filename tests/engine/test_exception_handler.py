"""Unit tests for ExceptionHandler — skip/downgrade/override logic."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestExceptionHandler:
    """Tests for ExceptionHandler.apply_exceptions(rule, context)."""

    def test_import_exists(self):
        from app.services.engine.exception_handler import ExceptionHandler
        assert ExceptionHandler is not None

    def test_no_exceptions_returns_normal(self):
        from app.services.engine.exception_handler import ExceptionHandler
        from app.services.engine.context import EvaluationContext
        from app.models import Regla

        session = MagicMock()
        session.query().filter().filter().all.return_value = []

        handler = ExceptionHandler()
        rule = Regla(nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        ctx = EvaluationContext(invoice_data={"convenio": "PyP"})

        effect, overrides = handler.apply_exceptions(rule, ctx, session)
        assert effect == "normal"
        assert overrides is None

    def test_skip_exception(self):
        from app.services.engine.exception_handler import ExceptionHandler
        from app.services.engine.context import EvaluationContext
        from app.models import Regla, Excepcion

        session = MagicMock()
        exc = Excepcion(
            id=1, regla_id=1, tipo_efecto="skip",
            condicion_json={"convenio": "PyP"},
            activo=True,
        )
        session.query().filter().filter().all.return_value = [exc]

        handler = ExceptionHandler()
        rule = Regla(id=1, nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        ctx = EvaluationContext(invoice_data={"convenio": "PyP"})

        effect, overrides = handler.apply_exceptions(rule, ctx, session)
        assert effect == "skip"

    def test_override_exception(self):
        from app.services.engine.exception_handler import ExceptionHandler
        from app.services.engine.context import EvaluationContext
        from app.models import Regla, Excepcion

        session = MagicMock()
        exc = Excepcion(
            id=1, regla_id=1, tipo_efecto="override",
            condicion_json={"convenio": "PyP"},
            parametros_override={"umbral": 500},
            activo=True,
        )
        session.query().filter().filter().all.return_value = [exc]

        handler = ExceptionHandler()
        rule = Regla(id=1, nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        ctx = EvaluationContext(invoice_data={"convenio": "PyP"})

        effect, overrides = handler.apply_exceptions(rule, ctx, session)
        assert effect == "override"
        assert overrides == {"umbral": 500}

    def test_exception_not_matching_conditions(self):
        from app.services.engine.exception_handler import ExceptionHandler
        from app.services.engine.context import EvaluationContext
        from app.models import Regla, Excepcion

        session = MagicMock()
        exc = Excepcion(
            id=1, regla_id=1, tipo_efecto="skip",
            condicion_json={"convenio": "Asistencial"},  # Different value
            activo=True,
        )
        session.query().filter().filter().all.return_value = [exc]

        handler = ExceptionHandler()
        rule = Regla(id=1, nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        ctx = EvaluationContext(invoice_data={"convenio": "PyP"})

        effect, overrides = handler.apply_exceptions(rule, ctx, session)
        assert effect == "normal"

    def test_inactive_exception_ignored(self):
        from app.services.engine.exception_handler import ExceptionHandler
        from app.services.engine.context import EvaluationContext
        from app.models import Regla, Excepcion

        session = MagicMock()
        # No active exceptions returned by query
        session.query().filter().filter().all.return_value = []

        handler = ExceptionHandler()
        rule = Regla(id=1, nombre="r1", dominio="odontologia", estado="active", prioridad=10)
        ctx = EvaluationContext(invoice_data={"convenio": "PyP"})

        effect, overrides = handler.apply_exceptions(rule, ctx, session)
        assert effect == "normal"
