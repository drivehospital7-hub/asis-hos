"""Constantes específicas de Equipos Básicos.

Extraídas de app/constants/odontologia.py y app/constants/columnas.py
para que Equipos Básicos funcione como módulo independiente.
"""

from __future__ import annotations

# =============================================================================
# PROFESIONALES - Equipos Básicos
# =============================================================================

PROFESIONALES_EQUIPOS_BASICOS: dict[str, dict[str, str]] = {
    "03764": {
        "nombre": "JARAMILLO HERNANDEZ YAMILE LORENA",
        "tipo": "ODONTOLOGO",
    },
    "03762": {
        "nombre": "CHAVES GONZALEZ NURY ADRIANA",
        "tipo": "HIGIENISTA",
    },
    "03808": {
        "nombre": "PANTOJA VARGAS MERLY ORFELINA",
        "tipo": "HIGIENISTA",
    },
    "02981": {
        "nombre": "MARTINEZ MUÑOZ MARIA FERNANDA",
        "tipo": "HIGIENISTA",
    },
    "03761": {
        "nombre": "NEQUIRUCAMA NEQUIRUCAMA DARWIN HERNEY",
        "tipo": "HIGIENISTA",
    },
    "03766": {
        "nombre": "NARVAEZ DELGADO ADRIAN ALONSO",
        "tipo": "ODONTOLOGO",
    },
    "03739": {
        "nombre": "ESCOBAR PALACIOS CARLOS ANDRES",
        "tipo": "ODONTOLOGO",
    },
    "03763": {
        "nombre": "MESTRE RUIZ DAYRON",
        "tipo": "ODONTOLOGO",
    },
    "02084": {
        "nombre": "RUALES ALVARADO LUZ MERY",
        "tipo": "HIGIENISTA",
    },
    "03825": {
        "nombre": "GARCIA MONTENEGRO MARGARITA",
        "tipo": "HIGIENISTA",
    },
    "03831": {
        "nombre": "CHICO ACOSTA JUAN ANDRES",
        "tipo": "ODONTOLOGO",
    },
    "03851": {
        "nombre": "HERRERA CANO ALEXANDER",
        "tipo": "ODONTOLOGO",
    },
    "03848": {
        "nombre": "BURBANO SALAZAR ANAYIBE LORENA",
        "tipo": "HIGIENISTA",
    },
}

# =============================================================================
# EQUIPOS BÁSICOS - Reglas independientes
# =============================================================================

# Procedimientos objetivo para Equipos Básicos (PyP por defecto, configurable)
EQUIPOS_BASICOS_TARGET_PROCEDURES = frozenset({
    "Control de Placa Bacteriana",
    "Aplicación de Sellantes",
    "Detartraje Supragingival",
    "Topicacion de Fluor en Barniz",
    "Consulta de Primera vez por Odontologia General",
})

# Umbral ruta duplicada para Equipos Básicos (configurable)
EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD = 3

# Cantidades anómalas para Equipos Básicos (configurable)
EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN = 2
EQUIPOS_BASICOS_CANTIDAD_MAX = 10
EQUIPOS_BASICOS_CANTIDAD_PYP_MIN = 3

# =============================================================================
# CENTROS DE COSTO
# =============================================================================

CENTRO_COSTO_EQUIPOS_BASICOS = "EQUIPOS BASICOS ODONTOLOGIA"

# =============================================================================
# HEADERS - Headers de hojas especiales
# =============================================================================

# Headers para hoja Revision EQUIPOS BÁSICOS (formato normalizado - 6 columnas fijas)
EQUIPOS_BASICOS_REVISION_HEADERS: dict[int, str] = {
    1: "Tipo de error",
    2: "Número Factura",
    3: "Responsable Cierra",
    4: "Descripción",
    5: "Procedimiento",
    6: "Detalle",
}

# =============================================================================
# COLUMNS - Columnas a mostrar (las demás se ocultan)
# =============================================================================

EQUIPOS_BASICOS_COLUMNS_TO_KEEP = frozenset({
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
