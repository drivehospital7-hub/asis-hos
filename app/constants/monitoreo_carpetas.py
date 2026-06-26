"""Constantes para el módulo Monitoreo de Carpetas.

Configuración de rutas de red, patrones regex para validación de nombres,
keywords de inferencia de estado y timeouts de escaneo.

Todas las rutas de red se configuran via MONITOREO_CARPETAS_ROOTS env var.
"""

from __future__ import annotations

# =============================================================================
# STATUS - Keywords de inferencia de estado
# =============================================================================

STATUS_VERIFICADA: str = "Verificada"
STATUS_POR_CORREGIR: str = "Por corregir"
STATUS_EN_REVISION: str = "En revisión"

STATUS_KEYWORDS: dict[str, list[str]] = {
    STATUS_VERIFICADA: ["FACTURAS CAPITA OK", "LISTAS PARA PASAR"],
    STATUS_POR_CORREGIR: ["CORREGIR", "CORRECCION"],
    STATUS_EN_REVISION: ["default"],
}

# =============================================================================
# REGEX - Patrones de validación de nombres de facturas
# =============================================================================

# FEV seguido de uno o más dígitos (case-insensitive)
FEV_REGEX: str = r"FEV\d+"

# CAP seguido de dígitos, guion bajo, letras mayúsculas y dígitos
CAP_REGEX: str = r"CAP\d+_[A-Z]+\d+"

# =============================================================================
# ENV VAR - Configuración de rutas de red
# =============================================================================

ENV_MONITOREO_ROOTS: str = "MONITOREO_CARPETAS_ROOTS"

# =============================================================================
# TIMEOUTS - Configuración de escaneo
# =============================================================================

SCAN_TIMEOUT_PER_FACTURADOR: int = 120
"""Tiempo máximo en segundos para escanear un solo facturador."""

MAX_CONCURRENT_SCANS: int = 3
"""Máximo de escaneos simultáneos (semáforo de concurrencia)."""

# =============================================================================
# EXCEL - Configuración del reporte
# =============================================================================

REPORT_SHEET_FACTURAS: str = "Facturas"
REPORT_SHEET_INDICADORES: str = "Indicadores"
REPORT_PREFIX: str = "monitoreo_"
REPORT_SUFFIX: str = ".xlsx"

# Columnas del reporte de detalle
REPORT_COLUMNS: list[str] = [
    "Código Factura",
    "Tipo",
    "Estado",
    "Ruta Completa",
    "Facturador",
    "Fecha Escaneo",
    "Duplicado",
    "Carpeta Vacía",
    "Nombre Inválido",
]
