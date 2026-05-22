"""Constantes específicas de Odontología y Equipos Básicos.

Incluye: CUPS odontología, profesionales odontología y equipos básicos,
reglas IDE Contrato PyP, mal capitado, y thresholds configurables.
"""

from __future__ import annotations

# =============================================================================
# PROCEDURES - Códigos CUPS PyP (Promoción y Prevención)
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
# TARGET PROCEDURES - Procedimientos objetivo (compatibilidad con tests)
# =============================================================================

TARGET_PROCEDURES = frozenset({
    "Control de Placa Bacteriana",
    "Aplicación de Sellantes",
    "Detartraje Supragingival",
    "Topicacion de Fluor en Barniz",
    "Consulta de Primera vez por Odontologia General",
})

# =============================================================================
# MAL CAPITADO - Códigos que requieren prefijo FEV en Número Factura
# =============================================================================

CODIGOS_MAL_CAPITADO = frozenset({"G03XB01", "A02BB01"})
PREFIJO_FACTURA_MAL_CAPITADO = "FEV"

# MAL CAPITADO - Si Número Factura tiene prefijo CAP -> Cód Entidad Cobrar debe ser ESS118
PREFIJO_FACTURA_CAP = "CAP"
ENTIDAD_REQUERIDA_CAP = "ESS118"

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

# =============================================================================
# PROFESIONALES - Odontología
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
