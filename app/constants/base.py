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
AREA_HOSPITALIZACION = "hospitalizacion"
AREA_INTRAMURAL = "intramural"
AREA_AMBULATORIA = "ambulatoria"
AREA_EXTRAMURAL = "extramural"
AREA_FARMACIA = "farmacia"
AREA_UNIFICADA = "unificada"

# =============================================================================
# PERMISOS - Valores de permiso válidos
# =============================================================================

ALLOWED_PERMISOS = frozenset({
    "*",
    "procesar",
    "procesar:write",
    "control_urgencias",
    "control_urgencias:write",
    "facturas_abiertas",
    "facturas_abiertas:write",
    "equipos_basicos",
    "cruce_facturas",
    "derechos",
    "cronograma_bacteriologas",
    "cronograma_urgencias",
})

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

# Pares de permisos que NO pueden convivir en el mismo usuario.
# Si se asigna uno, el otro debe estar ausente.
# Formato: {permiso: su_conflictivo}
PERMISO_MUTUAL_EXCLUSION: dict[str, str] = {
    "procesar": "procesar:write",
    "procesar:write": "procesar",
    "control_urgencias": "control_urgencias:write",
    "control_urgencias:write": "control_urgencias",
    "facturas_abiertas": "facturas_abiertas:write",
    "facturas_abiertas:write": "facturas_abiertas",
}

# =============================================================================
# DEFAULT_TEMPLATES - Plantillas de permisos predefinidas
# =============================================================================

DEFAULT_TEMPLATES = [
    {
        "nombre": "procesar",
        "descripcion": "Solo módulo de procesamiento unificado",
        "permisos": ["procesar"],
    },
    {
        "nombre": "procesar_control",
        "descripcion": "Procesar + control + facturas abiertas (solo lectura)",
        "permisos": ["procesar", "control_urgencias", "facturas_abiertas"],
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
# ENGINE - Motor de Reglas de Auditoría
# =============================================================================

ENGINE_DOMAIN_TRANSVERSAL = "transversal"
RULE_STATES: frozenset[str] = frozenset({"draft", "active", "deprecated", "retired"})
DEFAULT_SEVERITY = "error"

import os as _os


def is_rule_engine_enabled() -> bool:
    """Check if the DB-backed rule engine is enabled via env var.

    Set USE_RULE_ENGINE=true to delegate migrated detectors to the engine.
    Default: false (legacy Python detectors are used).
    """
    from dotenv import load_dotenv
    load_dotenv()
    return _os.getenv("USE_RULE_ENGINE", "false").lower() == "true"

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
        "title": "Procesar",
        "slug": "procesar",
        "permiso": "procesar",
        "href": "/procesar",
        "tone": "danger",
        "pending_label": "errores",
        "description": "Procesamiento unificado de facturas. Detecta el tipo de factura automáticamente.",
    },
    {
        "title": "Cronograma Bacteriólogas",
        "slug": "cronograma_bacteriologas",
        "permiso": "cronograma_bacteriologas",
        "href": "/cronograma-bacteriologas",
        "tone": "info",
        "pending_label": "",
        "description": "Gestión de horarios y responsables del servicio de bacteriólogas.",
    },
    {
        "title": "Cronograma Urgencias",
        "slug": "cronograma_urgencias",
        "permiso": "cronograma_urgencias",
        "href": "/cronograma-urgencias",
        "tone": "info",
        "pending_label": "",
        "description": "Gestión de horarios del servicio de urgencias.",
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


# =============================================================================
# LABORATORIO DE ENVÍO - Códigos de laboratorio derivados a terceros
# (reutilizable, no ligado a ningún tipo de factura en particular)
# =============================================================================

CODIGOS_LABORATORIO_ENVIO: frozenset[str] = frozenset({
    "901010",  # Parcial De Orina [Uroanálisis]
    "901101",  # Coloración Ácido Alcohol Resistente [Ziehl-Neelsen] Y Lectura O Baciloscopia
    "901210",  # Cultivo Especial Para Otros Microorganismos En Cualquier Muestra
    "901220",  # Coproscópico [Coproparasitológico]
    "901230",  # Mycobacterium Tuberculosis Cultivo
    "901235",  # Urocultivo (Antibiograma De Disco)
    "902035",  # Grupo Sanguíneo ABO y Rh
    "902045",  # Tiempo De Protrombina [PT]
    "902049",  # Tiempo De Tromboplastina Parcial [PTT]
    "902210",  # Hemograma IV [Hemoglobina, Hematocrito, Recuento De Eritrocitos, Índices Eritrocitarios]
    "902215",  # Hemograma VI Completo con Diferencial
    "903016",  # Ferritina
    "903026",  # Microalbuminuria
    "903028",  # Microalbuminuria
    "903801",  # Ácido Úrico En Suero
    "903803",  # Albúmina En Suero U Otros Fluidos
    "903810",  # Calcio Semiautomatizado
    "903833",  # Fosfatasa Alcalina
    "903845",  # BUN [Nitrógeno Ureico]
    "903847",  # Lipasa
    "903849",  # Bilirrubina Total
    "903850",  # Bilirrubina Directa
    "903851",  # Colesterol Total En Suero
    "903852",  # Colesterol HDL En Suero
    "903853",  # Colesterol LDL En Suero
    "903854",  # Triglicéridos En Suero
    "903855",  # Glucosa En Suero U Otros Fluidos
    "903856",  # Glucosa En Orina
    "903859",  # Potasio En Suero U Otros Fluidos
    "903860",  # Creatinina En Suero
    "903862",  # Proteinuria En Orina De 24 H
    "903863",  # Proteínas Totales En Suero Y Otros Fluidos
    "903864",  # Sodio En Suero U Otros Fluidos
    "903865",  # Sodio En Orina De 24 Horas
    "903866",  # Transaminasa Glutámico-Pirúvica [Alanino Amino Transferasa - ALT]
    "903867",  # Transaminasa Glutámico Oxalacética [Aspartato Amino Transferasa - AST]
    "903876",  # Creatina En Orina
    "904902",  # TSH Hormona
    "904910",  # Hormona Luteinizante [LH]
    "904911",  # Hormona Folículo Estimulante [FSH]
    "904916",  # Prolactina
    "904920",  # TSH [Hormona Estimulante De La Tiroides]
    "904921",  # Tiroxina Libre
    "904925",  # Triyodotironina Total
    "906019",  # Chlamydia Trachomatis Anticuerpos Ig G Semiautomatizado O Automatizado
    "906131",  # Trypanosoma Cruzi Anticuerpos Ig G Semiautomatizado O Automatizado
    "906133",  # Trypanosoma Cruzi Anticuerpos Ig M Semiautomatizado O Automatizado
    "906205",  # Citomegalovirus Anticuerpos Ig G Semiautomatizado O Automatizado
    "906206",  # Citomegalovirus Anticuerpos Ig M Semiautomatizado O Automatizado
    "906210",  # VDRL [Sífilis] Semiautomatizado
    "906220",  # Hepatitis B Anticuerpos Central Ig M [Anti-Core HBc-M] Semiautomatizado O Automatizado
    "906221",  # Hepatitis B Anticuerpos Central Totales [Anti-Core HBc] Semiautomatizado O Automatizado
    "906230",  # Herpes II Anticuerpos Ig G Manual, Semiautomatizado O Automatizado
    "906231",  # Herpes II Anticuerpos Ig M Manual, Semiautomatizado O Automatizado
    "906241",  # Rubeola Anticuerpos Ig G Automatizado
    "906243",  # Rubeola Anticuerpos Ig M Automatizado
    "906250",  # VIH Anticuerpos Semiautomatizado O Automatizado
    "906463",  # Tiroideos Tiroglobulínicos Anticuerpos Automatizado
    "906610",  # Antígeno Específico Para Cáncer De Próstata
    "906910",  # Factor Reumatoideo Semiautomatizado
    "906920",  # Chlamydia Trachomatis Anticuerpos Ig M Semiautomatizado O Automatizado
})


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
