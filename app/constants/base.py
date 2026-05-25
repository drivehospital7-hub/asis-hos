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
# PERMISOS - Valores de permiso válidos
# =============================================================================

ALLOWED_PERMISOS = frozenset({
    "*",
    "odontologia",
    "urgencias",
    "control_urgencias",
    "control_urgencias:write",
    "facturas_abiertas",
    "facturas_abiertas:write",
    "equipos_basicos",
    "odontologia_equipos_basicos",
    "cruce_facturas",
    "derechos",
})

# =============================================================================
# DEFAULT_TEMPLATES - Plantillas de permisos predefinidas
# =============================================================================

DEFAULT_TEMPLATES = [
    {
        "nombre": "odontologia",
        "descripcion": "Solo módulo de odontología",
        "permisos": ["odontologia"],
    },
    {
        "nombre": "urgencias",
        "descripcion": "Urgencias + control + facturas abiertas (solo lectura)",
        "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
    },
    {
        "nombre": "auditor",
        "descripcion": "Control urgencias + facturas abiertas + equipos básicos (con modificación)",
        "permisos": [
            "control_urgencias",
            "control_urgencias:write",
            "facturas_abiertas",
            "facturas_abiertas:write",
            "equipos_basicos",
        ],
    },
]

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
# FILE SIZE - Límite de tamaño para archivos Excel subidos
# =============================================================================

MAX_EXCEL_UPLOAD_SIZE_MB = 100

# =============================================================================
# HOSPITALIZACIÓN - Constantes generales
# =============================================================================

HORAS_POR_DIA = 24

# =============================================================================
# DASHBOARD - Áreas del dashboard con sus permisos asociados
# =============================================================================

DASHBOARD_AREAS = [
    {
        "title": "Urgencias",
        "slug": "urgencias",
        "permiso": "urgencias",
        "href": "/urgencias",
        "tone": "danger",
        "pending_label": "errores",
        "description": "Procesamiento y validación de facturas del servicio de urgencias.",
    },
    {
        "title": "Odontología",
        "slug": "odontologia",
        "permiso": "odontologia",
        "href": "/odontologia",
        "tone": "info",
        "pending_label": "errores",
        "description": "Procesamiento y validación de facturas del servicio de odontología.",
    },
    {
        "title": "Control de Novedades",
        "slug": "control_errores",
        "permiso": "control_urgencias",
        "href": "/control-errores",
        "tone": "warning",
        "pending_label": "pendientes",
        "description": "Registro y seguimiento de novedades en facturación.",
    },
    {
        "title": "Facturas Abiertas",
        "slug": "abiertas_urgencias",
        "permiso": "facturas_abiertas",
        "href": "/abiertas-urgencias",
        "tone": "info",
        "pending_label": "sin horario",
        "description": "Gestión de horarios y responsables del servicio de urgencias.",
    },
    {
        "title": "Ordenado y Facturado",
        "slug": "ordenado_facturado",
        "permiso": "equipos_basicos",
        "href": "/ordenado-facturado",
        "tone": "info",
        "pending_label": "pendientes",
        "description": "Verificación de facturación ordenada por profesional y servicio.",
    },
    {
        "title": "Derechos",
        "slug": "derechos",
        "permiso": "derechos",
        "href": "/derechos",
        "tone": "info",
        "pending_label": "pendientes",
        "description": "Gestión de derechos de petición y trámites administrativos.",
    },
]


def _filter_areas(permisos: list[str] | None) -> list[dict]:
    """Filter DASHBOARD_AREAS by user permissions. Admin (*) sees all."""
    if permisos is None or "*" in permisos:
        return [{**a, "pending": 0} for a in DASHBOARD_AREAS]
    return [{**a, "pending": 0} for a in DASHBOARD_AREAS if a["permiso"] in permisos]
