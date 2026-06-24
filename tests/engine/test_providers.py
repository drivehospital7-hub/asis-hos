"""Unit tests for ContextProvider registry and InvoiceProvider."""

from __future__ import annotations

import pytest


class TestInvoiceProvider:
    """Tests for InvoiceProvider (prefix='invoice')."""

    def test_resolves_simple_path(self):
        from app.services.engine.providers import InvoiceProvider
        from app.services.engine.context import EvaluationContext
        provider = InvoiceProvider()
        ctx = EvaluationContext(invoice_data={"vlr_subsidiado": 1500.0})
        result = provider.resolve("invoice.vlr_subsidiado", ctx)
        assert result == 1500.0

    def test_resolves_last_path_component(self):
        from app.services.engine.providers import InvoiceProvider
        from app.services.engine.context import EvaluationContext
        provider = InvoiceProvider()
        ctx = EvaluationContext(invoice_data={"convenio_facturado": "PyP"})
        result = provider.resolve("invoice.convenio_facturado", ctx)
        assert result == "PyP"

    def test_returns_none_for_missing_key(self):
        from app.services.engine.providers import InvoiceProvider
        from app.services.engine.context import EvaluationContext
        provider = InvoiceProvider()
        ctx = EvaluationContext(invoice_data={})
        result = provider.resolve("invoice.missing_key", ctx)
        assert result is None

    def test_none_invoice_data(self):
        from app.services.engine.providers import InvoiceProvider
        from app.services.engine.context import EvaluationContext
        provider = InvoiceProvider()
        ctx = EvaluationContext(invoice_data=None)
        result = provider.resolve("invoice.any", ctx)
        assert result is None

    def test_prefix_property(self):
        from app.services.engine.providers import InvoiceProvider
        provider = InvoiceProvider()
        assert provider.prefix == "invoice"


class TestProviderRegistry:
    """Tests for PROVIDER_REGISTRY."""

    def test_invoice_provider_registered(self):
        from app.services.engine.providers import PROVIDER_REGISTRY
        assert "invoice" in PROVIDER_REGISTRY

    def test_registry_values_are_providers(self):
        from app.services.engine.providers import ContextProvider, PROVIDER_REGISTRY
        for provider in PROVIDER_REGISTRY.values():
            assert isinstance(provider, ContextProvider)

    def test_resolve_via_registry(self):
        from app.services.engine.providers import PROVIDER_REGISTRY
        from app.services.engine.context import EvaluationContext
        provider = PROVIDER_REGISTRY["invoice"]
        ctx = EvaluationContext(invoice_data={"vlr_procedimiento": 2000.0})
        result = provider.resolve("invoice.vlr_procedimiento", ctx)
        assert result == 2000.0

    def test_unknown_prefix_returns_none(self):
        from app.services.engine.providers import PROVIDER_REGISTRY
        assert "unknown_prefix" not in PROVIDER_REGISTRY

    def test_each_provider_has_prefix(self):
        from app.services.engine.providers import PROVIDER_REGISTRY
        for prefix, provider in PROVIDER_REGISTRY.items():
            assert provider.prefix == prefix


class TestContextProviderABC:
    """Verify ContextProvider is an abstract base class."""

    def test_is_abstract(self):
        from app.services.engine.providers import ContextProvider
        import inspect
        assert inspect.isabstract(ContextProvider)
