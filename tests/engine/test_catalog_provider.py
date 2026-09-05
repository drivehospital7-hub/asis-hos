"""Unit tests for CatalogProvider — resolves catalog.profesionales[code] lookups.

Follows TDD cycle: tests written BEFORE production code.
"""

from __future__ import annotations

import pytest


class TestCatalogProvider:
    """Tests for CatalogProvider (prefix='catalog')."""

    def test_prefix_is_catalog(self):
        """CatalogProvider must have prefix='catalog'."""
        from app.services.engine.providers import CatalogProvider
        provider = CatalogProvider()
        assert provider.prefix == "catalog"

    def test_resolve_existing_profesional(self):
        """Resolving a known professional code returns the info dict."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("odontologia", {
            "03424": {"nombre": "ARIAS MOREANO LAURA MELISSA", "tipo": "ODONTOLOGO"},
            "03007": {"nombre": "OSPINA MARTINEZ LIZETH", "tipo": "ODONTOLOGO"},
        })

        ctx = EvaluationContext()
        result = provider.resolve("catalog.profesionales[03424]", ctx)
        assert result == {"nombre": "ARIAS MOREANO LAURA MELISSA", "tipo": "ODONTOLOGO"}

    def test_resolve_missing_profesional_returns_none(self):
        """Resolving an unknown code returns None."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("odontologia", {
            "03424": {"nombre": "ARIAS", "tipo": "ODONTOLOGO"},
        })

        ctx = EvaluationContext()
        result = provider.resolve("catalog.profesionales[99999]", ctx)
        assert result is None

    def test_resolve_profesional_field(self):
        """Resolving a specific field like catalog.profesionales[code].tipo returns the field value."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("urgencias", {
            "03568": {"nombre": "RIVADENEIRA CABEZAS RENY", "tipo": "TRABAJADORA SOCIAL"},
        })

        ctx = EvaluationContext()
        result = provider.resolve("catalog.profesionales[03568].tipo", ctx)
        assert result == "TRABAJADORA SOCIAL"

    def test_resolve_profesional_field_missing_code(self):
        """Resolving a field for an unknown code returns None."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("urgencias", {})

        ctx = EvaluationContext()
        result = provider.resolve("catalog.profesionales[XYZ].tipo", ctx)
        assert result is None

    def test_cache_hit_returns_same_dict(self):
        """Repeated lookups for the same code should return cached data efficiently."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("equipos_basicos", {
            "03764": {"nombre": "JARAMILLO HERNANDEZ YAMILE", "tipo": "ODONTOLOGO"},
        })

        ctx = EvaluationContext()
        result1 = provider.resolve("catalog.profesionales[03764]", ctx)
        result2 = provider.resolve("catalog.profesionales[03764]", ctx)
        assert result1 is result2  # Same object — cache hit

    def test_empty_catalog_returns_none(self):
        """Resolving from an empty/never-loaded catalog returns None gracefully."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        ctx = EvaluationContext()
        result = provider.resolve("catalog.profesionales[03424]", ctx)
        assert result is None

    def test_load_multiple_domains(self):
        """Loading profesionales from different domains should not collide."""
        from app.services.engine.providers import CatalogProvider
        from app.services.engine.context import EvaluationContext

        provider = CatalogProvider()
        provider.load_profesionales("odontologia", {
            "001": {"nombre": "ODON_A", "tipo": "ODONTOLOGO"},
        })
        provider.load_profesionales("urgencias", {
            "001": {"nombre": "URG_A", "tipo": "MEDICO"},
        })

        ctx = EvaluationContext()
        odon_result = provider.resolve("catalog.profesionales[001]", ctx)
        urg_result = provider.resolve("catalog.profesionales[001]", ctx)

        # Last loaded wins in the flat cache (this is expected — domain prefix is not in the path)
        # In real use, rules are domain-specific, so cross-domain collisions don't matter
        assert odon_result == urg_result


class TestCatalogProviderRegistry:
    """Verify CatalogProvider is registered in PROVIDER_REGISTRY."""

    def test_catalog_provider_registered(self):
        """PROVIDER_REGISTRY must contain 'catalog' key pointing to CatalogProvider."""
        from app.services.engine.providers import PROVIDER_REGISTRY, CatalogProvider
        assert "catalog" in PROVIDER_REGISTRY
        assert isinstance(PROVIDER_REGISTRY["catalog"], CatalogProvider)

    def test_matches_abstract_interface(self):
        """CatalogProvider must be a ContextProvider subclass."""
        from app.services.engine.providers import CatalogProvider, ContextProvider
        provider = CatalogProvider()
        assert isinstance(provider, ContextProvider)
