"""ContextProvider registry and built-in data resolvers.

Each provider resolves a data path (e.g., "invoice.vlr_subsidiado") against
the EvaluationContext. Matched by prefix ("invoice" → InvoiceProvider).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
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


class CatalogProvider(ContextProvider):
    """Resolves catalog lookups: catalog.profesionales[CODE] or catalog.profesionales[CODE].tipo.

    Uses session-level in-memory cache keyed by code. Data is loaded via
    load_profesionales(domain, dict) which populates the cache from Python
    constants (Phase 2). In Phase 3+, this will be replaced by DB queries.

    Path format:
        catalog.profesionales[CODE]        → returns full info dict (or None)
        catalog.profesionales[CODE].tipo   → returns tipo field value (or None)
    """

    prefix = "catalog"

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, str]] = {}
        """Flat cache: code → info dict. Key is professional code string."""

    def load_profesionales(
        self,
        domain: str,
        profesionales: dict[str, dict[str, str]],
    ) -> None:
        """Populate the cache with profesional data from a Python dict.

        Args:
            domain: Domain name (e.g., 'odontologia', 'urgencias').
            profesionales: Dict mapping codigo → {"nombre": ..., "tipo": ...}.
        """
        for codigo, info in profesionales.items():
            # Domain prefix for namespace isolation (future-proofing)
            self._cache[codigo] = info

    def resolve(self, path: str, context: "EvaluationContext") -> Any:
        """Resolve a catalog path against the in-memory cache.

        Parses: catalog.profesionales[CODE] or catalog.profesionales[CODE].field
        Returns the info dict, specific field value, or None if not found.
        """
        import re

        # Match: catalog.profesionales[CODE] or catalog.profesionales[CODE].field
        match = re.match(
            r"^catalog\.profesionales\[([^\]]+)\](?:\.(\w+))?$",
            path,
        )
        if not match:
            return None

        codigo = match.group(1)
        field = match.group(2)

        info = self._cache.get(codigo)
        if info is None:
            return None

        if field:
            return info.get(field)

        return info


class ContractProvider(ContextProvider):
    """Resolves contract-related data: contract.ide_contrato.expected, etc.

    Placeholder for Phase 3 — in-memory lookup, upgraded to DB queries
    in Phase 7 when Contract ORM is added.

    Path format:
        contract.ide_contrato.expected[entidad][codigo] → expected IDE set
        contract.nota_tecnica[entidad].tarifa → tariff value
    """

    prefix = "contract"

    def __init__(self) -> None:
        self._ide_rules: dict[str, dict[str, frozenset[str]]] = {}
        """entity → (pyp_status → expected_ide_set)"""

    def load_ide_rules(
        self,
        entity_to_expected: dict[str, dict[str, frozenset[str]]],
    ) -> None:
        """Populate IDE contract rules in-memory.

        Args:
            entity_to_expected: Mapping entity → {"pyp": ide_set, "no_pyp": ide_set}.
        """
        self._ide_rules = entity_to_expected

    def resolve(self, path: str, context: "EvaluationContext") -> Any:
        """Resolve a contract data path.

        Currently returns None for all paths — placeholder for future.
        Phase 3 rules use InvoiceProvider to access row data directly,
        encoding entity/PyP/IDE rules in the condition tree.
        """
        return None


class DateProvider(ContextProvider):
    """Computes derived date fields from invoice row data.

    Path format:
        date.edad  → compute age (years) from fec_nacimiento + fec_factura
        date.horas → compute hours difference from fec_factura + fecha_cierre

    Returns an int for age/hours or None if dates are missing/invalid.
    The computed value is then compared by normal evaluators (gt, gte, lt, lte).
    """

    prefix = "date"

    def resolve(self, path: str, context: "EvaluationContext") -> Any:
        if context.invoice_data is None:
            return None

        field = path.split(".", 1)[-1] if "." in path else path

        if field == "edad":
            return self._compute_edad(context)
        elif field == "horas":
            return self._compute_horas(context)
        else:
            return None

    def _compute_edad(self, context: "EvaluationContext") -> int | None:
        """Compute age in years from fec_nacimiento and fec_factura."""
        fec_nac = self._parse_date(context.invoice_data.get("fec_nacimiento"))
        fec_fact = self._parse_date(context.invoice_data.get("fec_factura"))
        if fec_nac is None or fec_fact is None:
            return None
        # Future birth date (data error) → return None
        if fec_nac > fec_fact:
            return None
        edad = fec_fact.year - fec_nac.year
        if (fec_fact.month, fec_fact.day) < (fec_nac.month, fec_nac.day):
            edad -= 1
        return edad

    def _compute_horas(self, context: "EvaluationContext") -> int | None:
        """Compute hours difference between fec_factura and fecha_cierre."""
        fec_fact = self._parse_date(context.invoice_data.get("fec_factura"))
        fecha_cierre = self._parse_date(context.invoice_data.get("fecha_cierre"))
        if fec_fact is None or fecha_cierre is None:
            return None
        diff = (fecha_cierre - fec_fact).total_seconds()
        return int(diff / 3600)

    @staticmethod
    def _parse_date(date_value: Any) -> datetime | None:
        """Parse a date value from various formats.

        Handles datetime objects, strings in %Y-%m-%d, %d/%m/%Y, etc.
        Returns None if parsing fails.
        """
        from datetime import datetime as dt

        if date_value is None:
            return None
        if isinstance(date_value, dt):
            return date_value

        date_str = str(date_value).strip()
        if not date_str:
            return None

        # Try ISO formats first
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                return dt.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        # Try day-first formats
        for fmt in ("%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y"):
            try:
                return dt.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue

        return None


# ── Registry ──────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, ContextProvider] = {}


def _register_builtins() -> None:
    """Register all built-in context providers."""
    builtins = [
        InvoiceProvider(),
        CatalogProvider(),
        ContractProvider(),
        DateProvider(),
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
