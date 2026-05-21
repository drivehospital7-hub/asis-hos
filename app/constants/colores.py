"""Colores para formato condicional en hojas Excel."""

from __future__ import annotations

# =============================================================================
# COLORS - Colores para formato condicional (RGB hex - colores claros)
# =============================================================================

# Verdes claros para Cruce Facturas (coincidencias con Número Factura)
COLOR_GREEN_LIGHT = "C6EFCE"  # Verde suave (fondo)
COLOR_GREEN_DARK = "63BE7B"   # Verde más intenso (texto/bordes)

# Amarillos claros para Cruce Identificación
COLOR_YELLOW_LIGHT = "FFEB9C"  # Amarillo suave (fondo)
COLOR_YELLOW_DARK = "FFC000"  # Amarillo más intenso (texto/bordes)

# Rojos claros para errores generales
COLOR_RED_LIGHT = "FFC7CE"    # Rojo suave (fondo)
COLOR_RED_DARK = "FF6B6B"     # Rojo más intenso (texto/bordes)

# Colores para formato condicional (compatibilidad hacia atrás)
COLOR_GREEN = "C6EFCE"
COLOR_YELLOW = "FFEB9C"
COLOR_RED = "FFC7CE"

# =============================================================================
# HEADERS - Colores de encabezados
# =============================================================================

# Color azulado claro para encabezados
HEADER_BACKGROUND_COLOR = "DCE6F1"
# Color de borde para encabezados
HEADER_BORDER_COLOR = "4472C4"

# Color de fondo para filas de datos (azulado muy claro)
DATA_ROW_BACKGROUND_COLOR = "F2F6FA"

# Color rojo claro para headers y datos de Revision Urgencias
URGENCIA_HEADER_BACKGROUND_COLOR = "FFCCCC"  # Rojo muy claro
URGENCIA_HEADER_BORDER_COLOR = "FF6B6B"      # Rojo más intenso
URGENCIA_DATA_ROW_BACKGROUND_COLOR = "FFF0F0"  # Rojo muy claro para filas
