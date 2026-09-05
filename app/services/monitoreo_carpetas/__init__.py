"""Módulo de Monitoreo de Carpetas.

Escanea directorios de red de facturadores, infiere estado de carpetas,
valida nombres de facturas, detecta duplicados y carpetas vacías,
y genera reportes Excel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvoiceRecord:
    """Representa una factura individual encontrada durante el escaneo."""

    filename: str
    facturador: str
    full_path: str
    status: str
    invoice_type: str
    invoice_code: str


@dataclass
class ScanResult:
    """Resultado completo del escaneo de carpetas."""

    facturas: list[InvoiceRecord] = field(default_factory=list)
    indicadores: dict[str, int | float] = field(default_factory=dict)
    duplicados: list[dict[str, Any]] = field(default_factory=list)
    vacias: list[dict[str, Any]] = field(default_factory=list)
    errores_scan: list[dict[str, Any]] = field(default_factory=list)
    excel_path: str | None = None


__all__: list[str] = [
    "InvoiceRecord",
    "ScanResult",
]
