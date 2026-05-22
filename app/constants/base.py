"""Constantes de propósito general del proyecto Control System."""

from __future__ import annotations

# =============================================================================
# EXCEL - Formatos soportados
# =============================================================================

ALLOWED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})

# =============================================================================
# SHEETS - Nombres de hojas
# =============================================================================

REVISION_SHEET = "Revision"

# =============================================================================
# CONVENIOS - Valores de convenio
# =============================================================================

CONVENIO_ASISTENCIAL = "Asistencial"
CONVENIO_PYP = "Promoción y Prevención"

# =============================================================================
# TIPO USUARIO - Valores válidos (regla transversal)
# =============================================================================

TIPO_USUARIO_VALORES = frozenset({
    "SUBSIDIADO",
    "CONTRIBUTIVO",
    "OTROS (REGÍMENES ESPECIALES, EOC)",
    "VINCULADO",
    "PARTICULAR",
})

# =============================================================================
# ENTIDADES
# =============================================================================



# =============================================================================
# AREAS - Áreas del sistema de facturación
# =============================================================================

AREA_ODONTOLOGIA = "odontologia"
AREA_URGENCIAS = "urgencias"
AREA_EQUIPOS_BASICOS = "equipos_basicos"

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
# ARCHIVOS - Configuración de imágenes y archivos para errores
# =============================================================================

IMAGENES_DIR = "data/imagenes"
IMAGENES_MAX_PER_OBSERVACION = 3
IMAGENES_ALLOWED_TYPES = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"})
IMAGENES_MAX_SIZE_MB = 20

# =============================================================================
# HOSPITALIZACIÓN - Constantes generales
# =============================================================================

HORAS_POR_DIA = 24
