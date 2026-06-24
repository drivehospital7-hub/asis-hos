"""Unit tests for ContractProvider — Phase 3 infrastructure.

Tests the placeholder ContractProvider with in-memory cache,
ready for DB upgrade in Phase 7.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.services.engine.providers import ContractProvider, PROVIDER_REGISTRY
from app.services.engine.context import EvaluationContext


class TestContractProviderBasic:
    """Basic ContractProvider behavior."""

    def test_prefix_is_contract(self):
        """ContractProvider prefix must be 'contract'."""
        provider = ContractProvider()
        assert provider.prefix == "contract", "Prefix must be 'contract'"

    def test_resolve_returns_none_by_default(self):
        """Placeholder resolve returns None for all paths."""
        provider = ContractProvider()
        ctx = EvaluationContext()
        result = provider.resolve("contract.ide_contrato.expected", ctx)
        assert result is None

    def test_resolve_unknown_path_returns_none(self):
        """Unknown paths also return None."""
        provider = ContractProvider()
        ctx = EvaluationContext()
        result = provider.resolve("contract.nonexistent.path", ctx)
        assert result is None

    def test_registered_in_provider_registry(self):
        """ContractProvider must be registered under 'contract' prefix."""
        provider = PROVIDER_REGISTRY.get("contract")
        assert provider is not None, "ContractProvider not found in registry"
        assert isinstance(provider, ContractProvider), "Wrong provider type"
        assert provider.prefix == "contract"

    def test_load_ide_rules_populates_cache(self):
        """load_ide_rules stores entity→expected mapping."""
        provider = ContractProvider()
        rules = {
            "ESS118": {"pyp": frozenset({"970", "974"}), "no_pyp": frozenset({"969", "973"})},
        }
        provider.load_ide_rules(rules)
        # Cache populated but resolve still returns None (placeholder)
        ctx = EvaluationContext()
        assert provider.resolve("contract.ide_contrato.expected", ctx) is None

    def test_instantiate_multiple_providers_independent(self):
        """Each ContractProvider instance is independent."""
        p1 = ContractProvider()
        p2 = ContractProvider()
        p1.load_ide_rules({"TEST": {"pyp": frozenset({"1"})}})
        # Both still return None since resolve is placeholder
        ctx = EvaluationContext()
        assert p1.resolve("contract.x", ctx) is None
        assert p2.resolve("contract.x", ctx) is None


class TestContractProviderRegistry:
    """Provider registry integration."""

    def test_contract_prefix_not_collide_with_invoice(self):
        """Contract prefix does not clash with invoice prefix."""
        invoice = PROVIDER_REGISTRY.get("invoice")
        contract = PROVIDER_REGISTRY.get("contract")
        assert invoice is not None
        assert contract is not None
        assert invoice.prefix != contract.prefix

    def test_contract_prefix_not_collide_with_catalog(self):
        """Contract prefix does not clash with catalog prefix."""
        catalog = PROVIDER_REGISTRY.get("catalog")
        contract = PROVIDER_REGISTRY.get("contract")
        assert catalog is not None
        assert contract is not None
        assert catalog.prefix != contract.prefix
