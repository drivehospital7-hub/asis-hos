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
# GENDERIZE - Valores canónicos de género
# =============================================================================

GENDER_FEMALE = "female"
GENDER_MALE = "male"
GENDER_LASTNAME = "lastname"
GENDER_UNDEFINED = "undefined"

GENDER_DISPLAY_MAP: dict[str, str] = {
    "F": "female",
    "M": "male",
    "L": "lastname",
    "U": "undefined",
}

GENDER_CACHE_MAP: dict[str, str] = {
    "female": "F",
    "male": "M",
    "lastname": "L",
    "undefined": "U",
}

GENDER_VALID_SHORT = frozenset({"F", "M", "L", "U"})
GENDER_VALID_LONG = frozenset({"female", "male", "lastname", "undefined"})

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
    "monitoreo_carpetas",
    "monitoreo_carpetas:write",
})

# Pares de permisos que NO pueden convivir en el mismo usuario.
# Si se asigna uno, el otro debe estar ausente.
# Formato: {permiso: su_conflictivo}
PERMISO_MUTUAL_EXCLUSION: dict[str, str] = {
    "control_urgencias": "control_urgencias:write",
    "control_urgencias:write": "control_urgencias",
    "facturas_abiertas": "facturas_abiertas:write",
    "facturas_abiertas:write": "facturas_abiertas",
    "monitoreo_carpetas": "monitoreo_carpetas:write",
    "monitoreo_carpetas:write": "monitoreo_carpetas",
}

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
    {
        "title": "Equipos Básicos",
        "slug": "odontologia_equipos_basicos",
        "permiso": "odontologia_equipos_basicos",
        "href": "/odontologia-equipos-basicos",
        "tone": "info",
        "pending_label": "pendientes",
        "description": "Procesamiento de facturas de odontología para equipos básicos.",
    },
    {
        "title": "Monitoreo de Carpetas",
        "slug": "monitoreo_carpetas",
        "permiso": "monitoreo_carpetas",
        "href": "/monitoreo-carpetas",
        "tone": "info",
        "pending_label": "",
        "description": "Escaneo y monitoreo de carpetas de red de facturadores.",
    },
    {
        "title": "Usuarios",
        "slug": "usuarios",
        "permiso": "*",
        "href": "/auth/usuarios",
        "tone": "neutral",
        "pending_label": "",
        "description": "Gestión de usuarios, roles y permisos del sistema.",
    },
    {
        "title": "Importar Facturas",
        "slug": "import_facturas",
        "permiso": "*",
        "href": "/import-facturas",
        "tone": "neutral",
        "pending_label": "",
        "description": "Carga masiva de facturas desde archivos Excel.",
    },
]


def _filter_areas(permisos: list[str] | None) -> list[dict]:
    """Filter DASHBOARD_AREAS by user permissions. Admin (*) sees all.

    Expande permisos con :write para que quien tiene
    'control_urgencias:write' también vea el área 'control_urgencias'.
    """
    if permisos is None or "*" in permisos:
        return [{**a, "pending": 0} for a in DASHBOARD_AREAS]
    # Expandir :write → base (ej: control_urgencias:write → control_urgencias)
    expanded = set(permisos)
    for p in permisos:
        if p.endswith(":write"):
            expanded.add(p.removesuffix(":write"))
    return [{**a, "pending": 0} for a in DASHBOARD_AREAS if a["permiso"] in expanded]
