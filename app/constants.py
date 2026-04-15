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
    3: "Cups Equivalentes",
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
CODIGO_IDE_CONTRATO_861801_EPSI05 = "861801"
ENTIDAD_IDE_CONTRATO_861801_EPSI05 = "EPSI05"
IDE_CONTRATO_REQUERIDO_861801_EPSI05 = "977"

# ----- Nueva Regla: Código=890405 + Entidad=EPSI05
# Si identificación tiene código 861801 -> IDE Contrato = 976
# Si identificación NO tiene código 861801 -> IDE Contrato = 977
CODIGO_IDE_CONTRATO_890405_EPSI05 = "890405"
ENTIDAD_IDE_CONTRATO_890405_EPSI05 = "EPSI05"
IDE_CONTRATO_CON_INSERCION_890405_EPSI05 = "976"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPSI05 = "977"  # no tiene código 861801
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
CODIGO_IDE_CONTRATO_906340_ESS118 = "906340"
ENTIDAD_IDE_CONTRATO_906340_ESS118 = "ESS118"
IDE_CONTRATO_REQUERIDO_906340_ESS118 = "839"

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=861801 -> IDE Contrato debe ser 974
# Urgencias y Contratos
CODIGO_IDE_CONTRATO_861801_ESS118 = "861801"
ENTIDAD_IDE_CONTRATO_861801_ESS118 = "ESS118"
IDE_CONTRATO_REQUERIDO_861801_ESS118 = "974"

# ----- Nueva Regla: Cód Entidad Cobrar=ESS118 + Código=890405 -> IDE Contrato debe ser 977 o 973 según inserción
# Urgencias y Contratos - con lógica de inserción
CODIGO_IDE_CONTRATO_890405_ESS118 = "890405"
ENTIDAD_IDE_CONTRATO_890405_ESS118 = "ESS118"
IDE_CONTRATO_SIN_INSERCION_890405_ESS118 = "974"  # Si NO tiene código 861801
IDE_CONTRATO_CON_INSERCION_890405_ESS118 = "973"   # Si SÍ tiene código 861801

# ----- Nueva Regla: Cód Entidad Cobrar=ESSC18 + Código=906340 -> IDE Contrato debe ser 842
CODIGO_IDE_CONTRATO_906340_ESSC18 = "906340"
ENTIDAD_IDE_CONTRATO_ESSC18 = "ESSC18"
IDE_CONTRATO_REQUERIDO_906340_ESSC18 = "842"

# ----- Nueva Regla: Cód Entidad Cobrar=ESSC18 + Código=861801 -> IDE Contrato debe ser 975
CODIGO_IDE_CONTRATO_861801_ESSC18 = "861801"
IDE_CONTRATO_REQUERIDO_861801_ESSC18 = "975"

# ----- Nueva Regla: Cód Entidad Cobrar=ESSC18 + Código=890405 -> IDE Contrato según inserción
CODIGO_IDE_CONTRATO_890405_ESSC18 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_ESSC18 = "968"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_ESSC18 = "975"  # Si NO tiene código 861801

# ----- Nueva Regla: Cód Entidad Cobrar=EPS037 + Código=906340 -> IDE Contrato debe ser 962
CODIGO_IDE_CONTRATO_906340_EPS037 = "906340"
ENTIDAD_IDE_CONTRATO_EPS037 = "EPS037"
IDE_CONTRATO_REQUERIDO_906340_EPS037 = "962"

# ----- Nueva Regla: Cód Entidad Cobrar=EPS037 + Código=861801 -> IDE Contrato debe ser 961
CODIGO_IDE_CONTRATO_861801_EPS037 = "861801"
IDE_CONTRATO_REQUERIDO_861801_EPS037 = "961"

# ----- Nueva Regla: Cód Entidad Cobrar=EPS037 + Código=890405 -> IDE Contrato según inserción
CODIGO_IDE_CONTRATO_890405_EPS037 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_EPS037 = "962"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPS037 = "961"  # Si NO tiene código 861801

# ----- Nueva Regla: Código 906340 + Cód Entidad Cobrar=EPSS41 -> IDE 959
CODIGO_IDE_CONTRATO_906340_EPSS41 = "906340"
IDE_CONTRATO_REQUERIDO_906340_EPSS41 = "959"

# ----- Nueva Regla: Código 861801 + Cód Entidad Cobrar=EPSS41 -> IDE 958
CODIGO_IDE_CONTRATO_861801_EPSS41 = "861801"
IDE_CONTRATO_REQUERIDO_861801_EPSS41 = "958"

# ----- Nueva Regla: ESS062 + Código 861801 -> IDE Contrato debe ser 922
CODIGO_IDE_CONTRATO_861801_ESS062 = "861801"
ENTIDAD_IDE_CONTRATO_ESS062 = "ESS062"
IDE_CONTRATO_REQUERIDO_861801_ESS062 = "922"

# ----- Nueva Regla: ESS062 + Código 890405 -> IDE Contrato según inserción
# Si identificación tiene código 861801 -> IDE Contrato = 921
# Si identificación NO tiene código 861801 -> IDE Contrato = 922
CODIGO_IDE_CONTRATO_890405_ESS062 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_ESS062 = "921"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_ESS062 = "922"  # NO tiene código 861801

# ----- Nueva Regla: ESSC62 + Código 861801 -> IDE Contrato debe ser 863
CODIGO_IDE_CONTRATO_861801_ESSC62 = "861801"
ENTIDAD_IDE_CONTRATO_ESSC62 = "ESSC62"
IDE_CONTRATO_REQUERIDO_861801_ESSC62 = "863"

# ----- Nueva Regla: ESSC62 + Código 890405 -> IDE Contrato según si tiene 890405
# Si identificación tiene código 890405 en otro procedimiento -> IDE Contrato = 862
# Si identificación NO tiene código 890405 -> IDE Contrato = 863
CODIGO_IDE_CONTRATO_890405_ESSC62 = "890405"
CODIGO_A_BUSCAR_890405_ESSC62 = "890405"  # código a buscar para determinar IDE
IDE_CONTRATO_CON_INSERCION_890405_ESSC62 = "862"  # tiene código 890405
IDE_CONTRATO_SIN_INSERCION_890405_ESSC62 = "863"  # NO tiene código 890405

# ----- Nueva Regla: Código 890405 + Cód Entidad Cobrar=EPSS41 -> IDE según inserción
CODIGO_IDE_CONTRATO_890405_EPSS41 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_EPSS41 = "959"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPSS41 = "958"  # Si NO tiene código 861801

# =============================================================================
# URGENCIAS - Entidad -> IDE Contrato (reglas nuevas)
# =============================================================================
# Mapeo de Código Entidad Cobrar -> IDE Contrato requerido
# Cada entidad debe tener exactamente ese contrato (no depende del código)

URGENCIA_ENTIDAD_CONTRATO: dict[str, str] = {
    "86000": "919",
    "86": "911",
    "5177": "917",
    "RES004": "909",
    "RES001": "953",
    "983": "0001",
    "984": "0001",
    "AT1306": "867",
    "1327": "882",
    "AT1317": "887",
    "1318": "912",
    "AT1324": "915",
    "AT1329": "916",
    "MIN001": "918",   # primera opción
    "000124": "874",
    "1423": "966",
    "1429": "884",
    "1425": "880",
    "144": "885",
    "EPSS005": "934",
    "EPSC005": "931",
}

# Entidades con múltiples contratos válidos (especial)
URGENCIA_ENTIDAD_MULTIPLE_CONTRATO: dict[str, set] = {
    "MIN001": {"910", "918"},
}

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

# ----- Nueva Regla: Código CUPS 890601 + Tipo Factura=Hospitalización -> Centro de costo "HOSPITALIZACIÓN - ESTANCIA GENERAL"
CODIGO_CUPS_HOSPITALIZACION = "890601"
CENTRO_COSTO_HOSPITALIZACION_ESTANCIA = "HOSPITALIZACIÓN - ESTANCIA GENERAL"

# ----- Nueva Regla: Servicios CUPS reemplazable - Código 890201 o 12333 debe ser 890701
CODIGO_CUPS_REEMPLAZABLE = "890201"
CODIGO_CUPS_SUSTITUTO = "890701"
