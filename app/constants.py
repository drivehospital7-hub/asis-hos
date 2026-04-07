"""Constantes compartidas del proyecto Control System.

Este es el ÚNICO lugar para definir valores que se usan en múltiples módulos.
NO definir constantes en servicios individuales.
"""

from __future__ import annotations

# =============================================================================
# EXCEL - Formatos soportados
# =============================================================================

ALLOWED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})
MAX_UPLOAD_SIZE_MB = 10

# =============================================================================
# SHEETS - Nombres de hojas
# =============================================================================

CRUCE_FACTURAS_SHEET = "CruceFacturas"
REVISION_SHEET = "Revision"

# =============================================================================
# COLUMNS - Columnas a mostrar (las demás se ocultan)
# =============================================================================

COLUMNS_TO_KEEP = frozenset({
    "Entidad Cobrar",
    "Profesional Atiende",
    "Fec. Factura",
    "Número Factura",
    "Tipo Entidad Cobrar",
    "Convenio Facturado",
    "Procedimiento",
    "Tipo Identificación",
    "Edad Completa",
    "Nº Identificación",
    "Primer Apellido",
    "Responsable Cierra Facturar",
    "Vlr. Procedimiento",
    "Vlr. Subsidiado",
    "Cantidad",
    "Segundo Apellido",
    "Primer Nombre",
    "Segundo Nombre",
    "Sexo",
    "Fec. Nacimiento",
    "Cita",
    "Tipo Cita",
    "Centro Costo",
})

# =============================================================================
# PROCEDURES - Procedimientos PyP (Promoción y Prevención)
# =============================================================================

TARGET_PROCEDURES = frozenset({
    "Control de Placa Bacteriana",
    "Aplicación de Sellantes",
    "Detartraje Supragingival",
    "Topicacion de Fluor en Barniz",
    "Consulta de Primera vez por Odontologia General",
})

# =============================================================================
# COLORS - Colores para formato condicional (RGB hex - colores claros)
# =============================================================================

# Verdes claros para Facturas Ok
COLOR_GREEN_LIGHT = "C6EFCE"  # Verde suave (fondo)
COLOR_GREEN_DARK = "63BE7B"   # Verde más intenso (texto/bordes)

# Amarillos claros para Facturas Pendientes
COLOR_YELLOW_LIGHT = "FFEB9C"  # Amarillo suave (fondo)
COLOR_YELLOW_DARK = "FFC000"  # Amarillo más intenso (texto/bordes)

# Rojos claros para PDFs / Errores
COLOR_RED_LIGHT = "FFC7CE"    # Rojo suave (fondo)
COLOR_RED_DARK = "FF6B6B"     # Rojo más intenso (texto/bordes)

# Colores para formato condicional (compatibilidad hacia atrás)
COLOR_GREEN = "C6EFCE"
COLOR_YELLOW = "FFEB9C"
COLOR_RED = "FFC7CE"

# =============================================================================
# CONVENIOS - Valores de convenio
# =============================================================================

CONVENIO_ASISTENCIAL = "Asistencial"
CONVENIO_PYP = "Promoción y Prevención"

# =============================================================================
# ENTIDADES
# =============================================================================

ENTIDAD_MALLAMAS = "MALLAMAS EPS INDIGENA"
CENTRO_COSTO_ODONTOLOGIA = "ODONTOLOGIA"

# =============================================================================
# VALIDATION THRESHOLDS - Umbrales para validaciones
# =============================================================================

# Ruta duplicada: paciente con >= N facturas en PyP
RUTA_DUPLICADA_THRESHOLD = 3

# Cantidades anómalas
CANTIDAD_CONSULTAS_MIN = 2      # Consultas >= 2 es anómalo
CANTIDAD_MAX = 10               # Cantidad > 10 es anómalo
CANTIDAD_PYP_MIN = 3            # PyP >= 3 es anómalo

# =============================================================================
# HEADERS - Headers de hojas especiales
# =============================================================================

# Color azulado claro para encabezados
HEADER_BACKGROUND_COLOR = "DCE6F1"
# Color de borde para encabezados
HEADER_BORDER_COLOR = "4472C4"

# Color de fondo para filas de datos (azulado muy claro)
DATA_ROW_BACKGROUND_COLOR = "F2F6FA"
CRUCE_HEADERS: dict[str, str] = {
    "B2": "Facturas Ok",
    "D2": "Facturas Pendientes",
    "F2": "PDFs de Facturas",
}

# Headers para hoja Revision (columna -> valor)
REVISION_HEADERS: dict[int, str] = {
    1: "Decimales",
    2: "Doble tipo procedimiento",
    3: "Ruta Duplicada",
    4: "Convenio de procedimiento",
    5: "Cantidades",
}
