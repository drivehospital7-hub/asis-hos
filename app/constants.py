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
# PROCEDURES - Códigos CUPS PyP (Promoción y Prevención)
# =============================================================================

# =============================================================================
# PROCEDIMIENTOS PYP - Equipos Básicos
# =============================================================================

# Códigos CUPS para procedimientos de Promoción y Prevención
# Estos códigos DEBEN estar en el convenio "Promoción y Prevención"
# NOTA: No se verifica por nombre de procedimiento, solo por código CUPS
PYP_CUPS_CODES = frozenset({
    "890203",  # Consulta de Primera vez por Odontologia General
    "997002",  # Control de Placa Bacteriana
    "997106",  # Topización de Fluor en Barniz
    "997107",  # Aplicación de Sellantes
    "997301",  # Detartraje Supragingival
})

# Códigos PYP que SOLO pueden usar ODONTOLOGOS (890203 sí puede hygienista)
PYP_CODES_ONLY_ODONTOLOGO = frozenset({
    "890203",  # Consulta de Primera vez por Odontologia General
})

# Códigos PYP que pueden usar HIGIENISTAS (excepto 890203)
PYP_CODES_HIGIENISTA = frozenset({
    "997002",  # Control de Placa Bacteriana
    "997106",  # Topización de Fluor en Barniz
    "997107",  # Aplicación de Sellantes
    "997301",  # Detartraje Supragingival
})

# =============================================================================
# IDE CONTRATO - ESS118 con códigos PyP
# =============================================================================

ENTIDAD_IDE_CONTRATO_ESS118_PYP = "ESS118"
IDE_CONTRATO_MULTIPLE_ESS118_PYP = frozenset({"970", "974"})
IDE_CONTRATO_MULTIPLE_ESS118_NO_PYP = frozenset({"969", "973"})

# ESSC18 + Procedimientos PyP -> IDE Contrato 975
ENTIDAD_IDE_CONTRATO_ESSC18_PYP = "ESSC18"
IDE_CONTRATO_MULTIPLE_ESSC18_PYP = frozenset({"975"})
# ESSC18 + Procedimientos NO PyP -> IDE Contrato 968
IDE_CONTRATO_MULTIPLE_ESSC18_NO_PYP = frozenset({"968"})

# EPSS41 + Procedimientos PyP -> IDE Contrato 955 o 958
ENTIDAD_IDE_CONTRATO_EPSS41_PYP = "EPSS41"
IDE_CONTRATO_MULTIPLE_EPSS41_PYP = frozenset({"955", "958"})
# EPSS41 + Procedimientos NO PyP -> IDE Contrato 956 o 959
IDE_CONTRATO_MULTIPLE_EPSS41_NO_PYP = frozenset({"956", "959"})

# EPS037 + Procedimientos PyP -> IDE Contrato 961
ENTIDAD_IDE_CONTRATO_EPS037_PYP = "EPS037"
IDE_CONTRATO_MULTIPLE_EPS037_PYP = frozenset({"961"})
# EPS037 + Procedimientos NO PyP -> IDE Contrato 962
IDE_CONTRATO_MULTIPLE_EPS037_NO_PYP = frozenset({"962"})

# EPSI05 + Procedimientos PyP -> IDE Contrato 977
ENTIDAD_IDE_CONTRATO_EPSI05_PYP = "EPSI05"
IDE_CONTRATO_MULTIPLE_EPSI05_PYP = frozenset({"977"})
# EPSI05 + Procedimientos NO PyP -> IDE Contrato 976 o 978
IDE_CONTRATO_MULTIPLE_EPSI05_NO_PYP = frozenset({"976", "978"})

# EPSIC5 + Procedimientos PyP -> IDE Contrato 979
ENTIDAD_IDE_CONTRATO_EPSIC5_PYP = "EPSIC5"
IDE_CONTRATO_MULTIPLE_EPSIC5_PYP = frozenset({"979"})
# EPSIC5 + Procedimientos NO PyP -> IDE Contrato 967
IDE_CONTRATO_MULTIPLE_EPSIC5_NO_PYP = frozenset({"967"})

# RES001 + Procedimientos PyP -> IDE Contrato 954
ENTIDAD_IDE_CONTRATO_RES001_PYP = "RES001"
IDE_CONTRATO_MULTIPLE_RES001_PYP = frozenset({"954"})
# RES001 + Procedimientos NO PyP -> IDE Contrato 953
IDE_CONTRATO_MULTIPLE_RES001_NO_PYP = frozenset({"953"})

# ESS062 + Procedimientos PyP -> IDE Contrato 922
ENTIDAD_IDE_CONTRATO_ESS062_PYP = "ESS062"
IDE_CONTRATO_MULTIPLE_ESS062_PYP = frozenset({"922"})
# ESS062 + Procedimientos NO PyP -> IDE Contrato 921
IDE_CONTRATO_MULTIPLE_ESS062_NO_PYP = frozenset({"921"})

# ESSC62 + Procedimientos PyP -> IDE Contrato 863
ENTIDAD_IDE_CONTRATO_ESSC62_PYP = "ESSC62"
IDE_CONTRATO_MULTIPLE_ESSC62_PYP = frozenset({"863"})
# ESSC62 + Procedimientos NO PyP -> IDE Contrato 862
IDE_CONTRATO_MULTIPLE_ESSC62_NO_PYP = frozenset({"862"})

# 0001 + Procedimientos PyP -> IDE Contrato 17
ENTIDAD_IDE_CONTRATO_0001_PYP = "0001"
IDE_CONTRATO_MULTIPLE_0001_PYP = frozenset({"17"})
# 0001 + Procedimientos NO PyP -> IDE Contrato 984
IDE_CONTRATO_MULTIPLE_0001_NO_PYP = frozenset({"984"})

# EPSS005 + Procedimientos PyP -> IDE Contrato 933
ENTIDAD_IDE_CONTRATO_EPSS005_PYP = "EPSS005"
IDE_CONTRATO_MULTIPLE_EPSS005_PYP = frozenset({"933"})
# EPSS005 + Procedimientos NO PyP -> IDE Contrato 934
IDE_CONTRATO_MULTIPLE_EPSS005_NO_PYP = frozenset({"934"})

# EPSC005 + Procedimientos PyP -> IDE Contrato 932
ENTIDAD_IDE_CONTRATO_EPSC005_PYP = "EPSC005"
IDE_CONTRATO_MULTIPLE_EPSC005_PYP = frozenset({"932"})
# EPSC005 + Procedimientos NO PyP -> IDE Contrato 931
IDE_CONTRATO_MULTIPLE_EPSC005_NO_PYP = frozenset({"931"})

# 86 + Procedimientos NO PyP -> IDE Contrato 911
ENTIDAD_IDE_CONTRATO_86_NO_PYP = "86"
IDE_CONTRATO_MULTIPLE_86_NO_PYP = frozenset({"911"})

# 86000 + Procedimientos PyP -> IDE Contrato 920
ENTIDAD_IDE_CONTRATO_86000_PYP = "86000"
IDE_CONTRATO_MULTIPLE_86000_PYP = frozenset({"920"})
# 86000 + Procedimientos NO PyP -> IDE Contrato 919
IDE_CONTRATO_MULTIPLE_86000_NO_PYP = frozenset({"919"})

# Mantenido por compatibilidad con tests existentes
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
    8: "IDE Contrato",
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
# PROFESIONALES - Listado de profesionales de Odontología (para frontend)
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
# PROFESIONALES - Listado de profesionales de Odontología (validación)
# =============================================================================

PROFESIONALES_ODONTOLOGIA_VALIDACION: dict[str, dict[str, str]] = {
    "03424": {
        "nombre": "ARIAS MOREANO LAURA MELISSA",
        "tipo": "ODONTOLOGO",
    },
    "03007": {
        "nombre": "OSPINA MARTINEZ LIZETH",
        "tipo": "ODONTOLOGO",
    },
    "01329": {
        "nombre": "CASTILLO DUQUE NOHORA ELENA",
        "tipo": "HIGIENISTA",
    },
    "01251": {
        "nombre": "MOSQUERA LOZANO YENIA YADIRIS",
        "tipo": "ODONTOLOGO",
    },
    "01330": {
        "nombre": "PANTOJA MONTIEL LEIDY PAOLA",
        "tipo": "HIGIENISTA",
    },
    "03698": {
        "nombre": "QUINTERO QUIROZ NOBEIRA DORANI",
        "tipo": "HIGIENISTA",
    },
}

# =============================================================================
# PROFESIONALES - Listado de profesionales de Equipos Básicos
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
}

# =============================================================================
# PROFESIONALES - Listado de profesionales de Urgencias
# =============================================================================

PROFESIONALES_URGENCIAS: dict[str, dict[str, str]] = {
    "03568": {
        "nombre": "RIVADENEIRA CABEZAS RENY MARGARITA",
        "tipo": "TRABAJADORA SOCIAL",
    },
    "01235": {
        "nombre": "BURBANO NARVAEZ LISEDT FERNANDA",
        "tipo": "TRABAJADORA SOCIAL",
    },
    "01960": {
        "nombre": "CASTRO LINARES YESSICA PATRICIA",
        "tipo": "PSICOLOGA",
    },
    "03493": {
        "nombre": "MOMPOTES PANTOJA EMELIN BRISBANY",
        "tipo": "PSICOLOGA",
    },
    "03822": {
        "nombre": "APRAEZ RODRIGUEZ JENIFER PAOLA",
        "tipo": "NUTRICIONISTA",
    },
    "01293": {
        "nombre": "RODRIGUEZ MORALES JAMEZ ARLEY",
        "tipo": "MEDICO",
    },
    "02249": {
        "nombre": "PALACIOS PALACIOS FRANCISCO DARWIN",
        "tipo": "MEDICO",
    },
    "03799": {
        "nombre": "YANDAR PANTOJA LUIS FELIPE",
        "tipo": "MEDICO",
    },
    "03222": {
        "nombre": "CHILAMA HERNANDEZ SAMIR AMILCAR",
        "tipo": "MEDICO",
    },
    "03384": {
        "nombre": "ROSERO QUINTERO DARWIN DARIO",
        "tipo": "MEDICO",
    },
    "03154": {
        "nombre": "BASANTE RUANO VIVIANA JERALDINE",
        "tipo": "MEDICO",
    },
    "01289": {
        "nombre": "DELGADO CARVAJAL YASMANI",
        "tipo": "MEDICO",
    },
    "03628": {
        "nombre": "LUNA DIAZ RICHARD ALEXANDER",
        "tipo": "MEDICO",
    },
    "03710": {
        "nombre": "MORA JACANAMEJOY YENNY NATALIA",
        "tipo": "JEFE ENFERMERIA",
    },
    "01868": {
        "nombre": "VALLEJOS TORO ELCY JACKELINE",
        "tipo": "JEFE ENFERMERIA",
    },
    "03742": {
        "nombre": "ROSERO LUNA JENIFER LIZBETH",
        "tipo": "JEFE ENFERMERIA",
    },
    "03365": {
        "nombre": "HUERTAS OCAMPO DIANA PATRICIA",
        "tipo": "FISIOTERAPEUTA",
    },
    "03730": {
        "nombre": "PABON GARCIA ALEJANDRA",
        "tipo": "BACTERIOLOGA",
    },
    "03375": {
        "nombre": "PEÑA PEÑA LISBETH PAOLA",
        "tipo": "BACTERIOLOGA",
    },
    "02217": {
        "nombre": "MADROÑERO BURBANO KAREN LIZETH",
        "tipo": "BACTERIOLOGA",
    },
    "03374": {
        "nombre": "MOLINA ALVAREZ KAROL DAYANNA",
        "tipo": "BACTERIOLOGA",
    },
    "03255": {
        "nombre": "MARIN ZULUAGA VALENTINA",
        "tipo": "BACTERIOLOGA",
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

# Códigos permitidos por tipo de profesional en Urgencias
CODIGO_TRABAJADORA_SOCIAL = "890409"
CODIGO_PSICOLOGA = "890408"
CODIGO_NUTRICIONISTA = "890406"
CODIGO_FISIOTERAPEUTA = "890412"
CODIGOS_JEFE_ENFERMERIA = frozenset({"861801", "890205", "890405", "990211"})
CODIGOS_EXCLUIDOS_MEDICO = frozenset({
    "890409",  # TRABAJADORA SOCIAL
    "890408",  # PSICOLOGA
    "890406",  # NUTRICIONISTA
    "890412",  # FISIOTERAPEUTA
})

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

# ----- Nueva Regla: Código CUPS 890408 -> Centro de costo "URGENCIAS"
CODIGO_CUPS_URGENCIAS = "890408"
CENTRO_COSTO_URGENCIAS = "URGENCIAS"

# ----- Nueva Regla: Código CUPS 861101 -> Centro de costo "URGENCIAS"
CODIGO_CUPS_URGENCIAS_861101 = "861101"

# ----- Nueva Regla: Servicios CUPS reemplazable - Código 890201 o 12333 debe ser 890701
CODIGO_CUPS_REEMPLAZABLE = "890201"
CODIGO_CUPS_SUSTITUTO = "890701"
