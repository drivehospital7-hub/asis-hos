"""ContextProvider registry and built-in data resolvers.

Each provider resolves a data path (e.g., "invoice.vlr_subsidiado") against
the EvaluationContext. Matched by prefix ("invoice" → InvoiceProvider).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.engine.context import EvaluationContext

logger = logging.getLogger(__name__)


class ContextProvider(ABC):
    """Abstract base for data resolution providers.

    prefix: str — matched against the first segment of a data path.
    """

    prefix: str = ""

    @abstractmethod
    def resolve(self, path: str, context: "EvaluationContext") -> Any:
        """Resolve a data path against the evaluation context."""
        ...


class InvoiceProvider(ContextProvider):
    """Resolves invoice-level data: invoice.vlr_subsidiado, invoice.convenio_facturado, etc.

    Path format: "invoice.{field_name}" — looks up field_name in context.invoice_data.
    """

    prefix = "invoice"

    def resolve(self, path: str, context: "EvaluationContext") -> Any:
        if context.invoice_data is None:
            return None
        # Extract field name after the prefix: "invoice.vlr_subsidiado" → "vlr_subsidiado"
        field_name = path.split(".", 1)[-1] if "." in path else path
        return context.invoice_data.get(field_name)


# ── Registry ──────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, ContextProvider] = {}


def _register_builtins() -> None:
    """Register all built-in context providers."""
    builtins = [
        InvoiceProvider(),
    ]
    for p in builtins:
        PROVIDER_REGISTRY[p.prefix] = p


_register_builtins()


def get_provider(path: str) -> ContextProvider | None:
    """Look up a provider by matching path prefix against registry.

    "invoice.vlr_subsidiado" → lookup "invoice" → InvoiceProvider.
    """
    prefix = path.split(".", 1)[0] if "." in path else path
    return PROVIDER_REGISTRY.get(prefix)
