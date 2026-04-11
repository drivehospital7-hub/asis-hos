"""Constantes compartidas del proyecto Control System.

Este es el ÚNICO lugar para definir valores que se usan en múltiples módulos.
NO definir constantes en servicios individuales.
"""

from __future__ import annotations

# =============================================================================
# EXCEL - Formatos soportados
# =============================================================================

ALLOWED_EXCEL_SUFFIXES = frozenset({".xlsx", ".xls", ".xlsm", ".xlsb"})

# =============================================================================
# SHEETS - Nombres de hojas
# =============================================================================

CRUCE_FACTURAS_SHEET = "CruceFacturas"
REVISION_SHEET = "Revision"

# =============================================================================
# COLUMNS - Columnas a mostrar (las demás se ocultan)
# =============================================================================

# Columnas para ODONTOLOGÍA
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

# Columnas para URGENCIAS (incluye las necesarias para reglas)
URGENCIA_COLUMNS_TO_KEEP = frozenset({
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
    "Código Tipo Procedimiento",
    "Laboratorio",
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
# CONVENIOS - Valores de convenio
# =============================================================================

CONVENIO_ASISTENCIAL = "Asistencial"
CONVENIO_PYP = "Promoción y Prevención"

# =============================================================================
# ENTIDADES
# =============================================================================

ENTIDAD_MALLAMAS = "MALLAMAS EPS INDIGENA"
CENTRO_COSTO_ODONTOLOGIA = "ODONTOLOGIA"
CENTRO_COSTO_EXTRAMURAL = "SERVICIOS ODONTOLOGIA -EXTRAMURALES"
CENTRO_COSTO_EQUIPOS_BASICOS = "EQUIPOS BASICOS ODONTOLOGIA"

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
    "B2": "Cruce Facturas",
    "D2": "Cruce Identificación",
}

# Headers para hoja Revision ODONTOLOGIA (columna -> valor)
REVISION_HEADERS: dict[int, str] = {
    1: "Decimales",
    2: "Doble tipo procedimiento",
    3: "Ruta Duplicada",
    4: "Convenio de procedimiento",
    5: "Cantidades",
    6: "Tipo Identificación",
    7: "Centro Costo",
}

# Headers para hoja Revision URGENCIAS (columna -> valor)
URGENCIA_REVISION_HEADERS: dict[int, str] = {
    1: "Centros de Costos",
    2: "IDE Contrato",
}

# =============================================================================
# AREAS - Áreas del sistema de facturación
# =============================================================================

AREA_ODONTOLOGIA = "odontologia"
AREA_URGENCIAS = "urgencias"
AREA_EQUIPOS_BASICOS = "equipos_basicos"

# =============================================================================
# PROFESIONALES - Listado de profesionales de Odontología
# =============================================================================

PROFESIONALES_ODONTOLOGIA: dict[str, dict[str, str]] = {
    "001": {
        "nombre": "ARIAS MOREANO LAURA MELISSA",
        "identificacion": "1004730653",
    },
    "002": {
        "nombre": "CASTILLO DUQUE NOHORA ELENA",
        "identificacion": "38461725",
    },
    "003": {
        "nombre": "MOSQUERA LOZANO YENIA YADIRIS",
        "identificacion": "35852158",
    },
    "004": {
        "nombre": "OSPINA MARTINEZ LIZETH",
        "identificacion": "1110594106",
    },
    "005": {
        "nombre": "PANTOJA MONTIEL LEIDY PAOLA",
        "identificacion": "1123322483",
    },
    "006": {
        "nombre": "QUINTERO QUIROZ NOBEIRA DORANI",
        "identificacion": "1006848745",
    },
}

# =============================================================================
# URGENCIAS - Reglas específicas de Urgencias
# =============================================================================

CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO = "02"
CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS = "14"
LABORATORIO_NO = "No"
CENTRO_COSTO_APOYO_DIAGNOSTICO = "APOYO DIAGNOSTICO-IMAGENOLOGIA"
CENTRO_COSTO_TRASLADOS = "TRASLADOS"

# Códigos exceptuados (no listar aunque tenga Código=02 y Lab=No)
CODIGOS_EXCEPTUADOS = frozenset({
    "194901",
    "23105",
    "23116",
    "232200",
    "232201",
    "25142AFINA",
    "90123501",
    "90385901",
    "90386401",
    "903883",
    "9038831",
    "904903",
})

# Códigos que deben tener centro de costo "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"
CODIGOS_PYP_URGENCIAS = frozenset({
    "990211",
    "890205",
    "890405",
    "861801",
})

# Centro de costo para procedimientos PYP en urgencias
CENTRO_COSTO_PYP_URGENCIAS = "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"

# Códigos que deben tener centro de costo "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"
CODIGOS_QUIROFANO_URGENCIAS = frozenset({
    "735301",
    "90DS02",
})

# Centro de costo para procedimientos de quirófano en urgencias
CENTRO_COSTO_QUIROFANO_URGENCIAS = "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"

# Códigos que deben tener centro de costo "APOYO DIAGNOSTICO-LABORATOR CLINICO"
CODIGOS_LABORATORIO_URGENCIAS = frozenset({
    "903866",
    "903867",
    "903856",
    "9062082",
    "903833",
    "903828",
    "902209",
    "906340",
})

# Centro de costo para procedimientos de laboratorio en urgencias
CENTRO_COSTO_LABORATORIO_URGENCIAS = "APOYO DIAGNOSTICO-LABORATOR CLINICO"

# ----- Nueva Regla: IDE Contrato para Código=906340 + Entidad=EPSI05
CODIGO_IDE_CONTRATO_URGENCIAS = "906340"
ENTIDAD_IDE_CONTRATO_URGENCIAS = "EPSI05"
IDE_CONTRATO_REQUERIDO_URGENCIAS = "986"

# ----- Nueva Regla: IDE Contrato para Código=861801 -> IDE Contrato debe ser 977 + Entidad=EPSI05
CODIGO_IDE_CONTRATO_861801 = "861801"
ENTIDAD_IDE_CONTRATO_861801 = "EPSI05"
IDE_CONTRATO_REQUERIDO_861801 = "977"

# ----- Nueva Regla: Código=890405 + Entidad=EPSI05
# Si identificación tiene código 861801 -> IDE Contrato = 976
# Si identificación NO tiene código 861801 -> IDE Contrato = 977
CODIGO_IDE_CONTRATO_890405 = "890405"
ENTIDAD_IDE_CONTRATO_890405 = "EPSI05"
IDE_CONTRATO_CON_INSERCION_890405 = "976"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405 = "977"  # no tiene código 861801
CODIGO_INSERCION_BUSCAR = "861801"  # código a buscar para determinar IDE Contrato

# ----- Nueva Regla: Código=861801 + Entidad=EPSIC5 (OTHER entity, not EPSI05)
# Código 861801 + Entidad EPSIC5 -> IDE Contrato siempre 979
CODIGO_IDE_CONTRATO_EPSIC5 = "861801"
ENTIDAD_IDE_CONTRATO_EPSIC5 = "EPSIC5"
IDE_CONTRATO_REQUERIDO_EPSIC5 = "979"

# ----- Nueva Regla: Código=890405 + Entidad=EPSIC5 (OTHER entity, not EPSI05)
# Si identificación tiene código 861801 -> IDE Contrato = 967
# Si identificación NO tiene código 861801 -> IDE Contrato = 979
CODIGO_IDE_CONTRATO_890405_EPSIC5 = "890405"
ENTIDAD_IDE_CONTRATO_890405_EPSIC5 = "EPSIC5"
IDE_CONTRATO_CON_INSERCION_890405_EPSIC5 = "967"
IDE_CONTRATO_SIN_INSERCION_890405_EPSIC5 = "979"

# ----- Nueva Regla: Entidad=ESS118 + Códigos específicos -> IDE Contrato no puede ser 969
# IDE Contrato 969 NO permitido para estos códigos
ENTIDAD_IDE_CONTRATO_ESS118 = "ESS118"
CODIGOS_IDE_CONTRATO_NO_969 = [
    "110001",
    "110001AUX",
    "861101",
    "890403",
    "890406",
    "890408",
    "890409",
    "890412",
    "939403",
]
IDE_CONTRATO_PROHIBIDO_ESS118 = "969"

# Color rojo claro para headers y datos de Revision Urgencias
URGENCIA_HEADER_BACKGROUND_COLOR = "FFCCCC"  # Rojo muy claro
URGENCIA_HEADER_BORDER_COLOR = "FF6B6B"      # Rojo más intenso
URGENCIA_DATA_ROW_BACKGROUND_COLOR = "FFF0F0"  # Rojo muy claro para filas

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=735301 -> IDE Contrato debe ser 970
# Urgencias y Contratos
CODIGO_IDE_CONTRATO_735301 = "735301"
ENTIDAD_IDE_CONTRATO_735301 = "ESS118"
IDE_CONTRATO_REQUERIDO_735301 = "970"

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=906340 -> IDE Contrato debe ser 839
# Urgencias y Contratos
CODIGO_IDE_CONTRATO_906340 = "906340"
ENTIDAD_IDE_CONTRATO_906340 = "ESS118"
IDE_CONTRATO_REQUERIDO_906340 = "839"

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=861801 -> IDE Contrato debe ser 974
# Urgencias y Contratos
CODIGO_IDE_CONTRATO_861801 = "861801"
ENTIDAD_IDE_CONTRATO_861801 = "ESS118"
IDE_CONTRATO_REQUERIDO_861801 = "974"

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=890405 -> IDE Contrato debe ser 977 o 973 según inserción
# Urgencias y Contratos - con lógica de inserción
CODIGO_IDE_CONTRATO_890405 = "890405"
ENTIDAD_IDE_CONTRATO_890405 = "ESS118"
IDE_CONTRATO_SIN_INSERCION_890405 = "977"  # Si NO tiene código 861801
IDE_CONTRATO_CON_INSERCION_890405 = "973"   # Si SÍ tiene código 861801

# =============================================================================
# EQUIPOS BÁSICOS - Reglas independientes de Odontología estándar
# =============================================================================

# Columnas para Equipos Básicos (mismas que odontología por ahora)
EQUIPOS_BASICOS_COLUMNS_TO_KEEP = COLUMNS_TO_KEEP

# Headers para hoja Revision EQUIPOS BÁSICOS (pueden ser diferentes)
EQUIPOS_BASICOS_REVISION_HEADERS: dict[int, str] = {
    1: "Decimales",
    2: "Doble tipo procedimiento",
    3: "Ruta Duplicada",
    4: "Convenio de procedimiento",
    5: "Cantidades",
    6: "Tipo Identificación",
    7: "Centro Costo",
}

# --- REGLAS CONFIGURABLES PARA EQUIPOS BÁSICOS ---
# Estas你可以 modificar después sin afectar las reglas de Odontología estándar

# Procedimientos objetivo para Equipos Básicos (PYá por defecto, configurable)
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
