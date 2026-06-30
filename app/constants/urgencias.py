"""Constantes específicas de Urgencias.

Incluye: IDE Contrato, centros de costo, CUPS equivalentes,
reglas SOAT, hospitalización, CAPITA, y reglas de cantidades.
"""

from __future__ import annotations

# =============================================================================
# URGENCIAS - Reglas específicas de Urgencias (bases)
# =============================================================================

CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO = "02"
CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS = "14"
LABORATORIO_NO = "No"
CENTRO_COSTO_APOYO_DIAGNOSTICO = "APOYO DIAGNOSTICO-IMAGENOLOGIA"
CENTRO_COSTO_TRASLADOS = "TRASLADOS"

# Códigos permitidos por tipo de profesional en Urgencias
CODIGOS_TRABAJADORA_SOCIAL = frozenset({"890409", "37701"})
CODIGOS_PSICOLOGA = frozenset({"890408", "35102"})
CODIGOS_NUTRICIONISTA = frozenset({"890406", "37602"})
CODIGOS_FISIOTERAPEUTA = frozenset({"890412", "890411", "29117"})
CODIGOS_JEFE_ENFERMERIA = frozenset({"861801", "890205", "890405", "990211", "29116", "39360"})
CODIGOS_ODONTOLOGO = frozenset({"890403", "36102"})
CODIGOS_EXCLUIDOS_MEDICO = frozenset({
    "890409",  # TRABAJADORA SOCIAL
    "37701",   # TRABAJADORA SOCIAL
    "890408",  # PSICOLOGA
    "35102",   # PSICOLOGA
    "890406",  # NUTRICIONISTA
    "37602",   # NUTRICIONISTA
    "890412",  # FISIOTERAPEUTA
    "890411",  # FISIOTERAPEUTA
    "29117",   # FISIOTERAPEUTA
    "861801",  # JEFE ENFERMERIA
    "890205",  # JEFE ENFERMERIA
    "890405",  # JEFE ENFERMERIA
    "990211",  # JEFE ENFERMERIA
    "29116",   # JEFE ENFERMERIA
    "39360",   # JEFE ENFERMERIA
    "890403",  # ODONTOLOGO — Interconsulta por Odontologia General
    "36102",   # ODONTOLOGO
})

# Excepciones para Bacterióloga (no requiere Tipo=02/05 ni Laboratorio=Si)
EXCEPCIONES_BACTERIOLOGA = frozenset({"904903", "903883"})
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
    "39360",
    "29116",
})

CENTRO_COSTO_PYP_URGENCIAS = "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"

# Códigos que deben tener centro de costo "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"
CODIGOS_QUIROFANO_URGENCIAS = frozenset({
    "735301",
    "90DS02",
    "512002",
    "39220",
})

CENTRO_COSTO_QUIROFANO_URGENCIAS = "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"

# Códigos que deben tener centro de costo "APOYO DIAGNOSTICO-LABORATOR CLINICO"
CODIGOS_LABORATORIO_URGENCIAS = frozenset({
    "903437",
    "903866",
    "903867",
    "9062082",
    "903833",
    "903828",
    "902209",
    "906340",
    "904903",
    "902206",
    "906129",
    "906127",
    "907009",
})

CODIGOS_LABORATORIO_URGENCIAS_REVERSE = frozenset({
    "904902",
})

CENTRO_COSTO_LABORATORIO_URGENCIAS = "APOYO DIAGNOSTICO-LABORATOR CLINICO"

# Tarifario="Suminstros, Medicamentos" -> Centro de costo "APOYO TERAPEUTICO-FARMACIA E INSUMOS."
VALOR_TARIFARIO_FARMACIA = "Suminstros, Medicamentos"
CENTRO_COSTO_FARMACIA = "APOYO TERAPEUTICO-FARMACIA E INSUMOS."

# =============================================================================
# URGENCIAS - IDE Contrato (reglas por código + entidad)
# =============================================================================

# IDE Contrato para Código=906340 + Entidad=EPSI05
CODIGO_IDE_CONTRATO_URGENCIAS = "906340"
ENTIDAD_IDE_CONTRATO_URGENCIAS = "EPSI05"
IDE_CONTRATO_REQUERIDO_URGENCIAS = "986"

# IDE Contrato para Código=861801 -> IDE Contrato debe ser 977 + Entidad=EPSI05
CODIGO_IDE_CONTRATO_861801_EPSI05 = "861801"
ENTIDAD_IDE_CONTRATO_861801_EPSI05 = "EPSI05"
IDE_CONTRATO_REQUERIDO_861801_EPSI05 = "977"

# Código=890405 + Entidad=EPSI05
CODIGO_IDE_CONTRATO_890405_EPSI05 = "890405"
ENTIDAD_IDE_CONTRATO_890405_EPSI05 = "EPSI05"
IDE_CONTRATO_CON_INSERCION_890405_EPSI05 = "976"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPSI05 = "977"  # no tiene código 861801
CODIGO_INSERCION_BUSCAR = "861801"  # código a buscar para determinar IDE Contrato

# Código=861801 + Entidad=EPSIC5 -> IDE Contrato siempre 979
CODIGO_IDE_CONTRATO_EPSIC5 = "861801"
ENTIDAD_IDE_CONTRATO_EPSIC5 = "EPSIC5"
IDE_CONTRATO_REQUERIDO_EPSIC5 = "979"

# Código=890405 + Entidad=EPSIC5
CODIGO_IDE_CONTRATO_890405_EPSIC5 = "890405"
ENTIDAD_IDE_CONTRATO_890405_EPSIC5 = "EPSIC5"
IDE_CONTRATO_CON_INSERCION_890405_EPSIC5 = "967"
IDE_CONTRATO_SIN_INSERCION_890405_EPSIC5 = "979"

# Cód Entidad Cobrar=ESS118 + Código=906340 -> IDE Contrato debe ser 839
CODIGO_IDE_CONTRATO_906340_ESS118 = "906340"
ENTIDAD_IDE_CONTRATO_906340_ESS118 = "ESS118"
IDE_CONTRATO_REQUERIDO_906340_ESS118 = "839"

# ESS118 + Código=735301 o 861801 -> IDE Contrato puede ser 970 o 974
CODIGO_IDE_CONTRATO_735301_ESS118 = "735301"
CODIGO_IDE_CONTRATO_861801_ESS118 = "861801"
ENTIDAD_IDE_CONTRATO_ESS118_NUEVOS = "ESS118"
IDE_CONTRATO_MULTIPLE_ESS118_NUEVOS = frozenset({"970", "974"})

# ESS118 + Código=890405 -> IDE Contrato debe ser 974
CODIGO_IDE_CONTRATO_890405_ESS118 = "890405"
ENTIDAD_IDE_CONTRATO_890405_ESS118 = "ESS118"
IDE_CONTRATO_REQUERIDO_890405_ESS118 = "974"

# ESS118 + Código=890205 -> IDE Contrato debe ser 970
CODIGO_IDE_CONTRATO_890205_ESS118 = "890205"
ENTIDAD_IDE_CONTRATO_890205_ESS118 = "ESS118"
IDE_CONTRATO_REQUERIDO_890205_ESS118 = "970"

# Cód Entidad Cobrar=ESSC18 + Código=906340 -> IDE Contrato debe ser 842
CODIGO_IDE_CONTRATO_906340_ESSC18 = "906340"
ENTIDAD_IDE_CONTRATO_ESSC18 = "ESSC18"
IDE_CONTRATO_REQUERIDO_906340_ESSC18 = "842"

# Cód Entidad Cobrar=ESSC18 + Código=861801 -> IDE Contrato debe ser 975
CODIGO_IDE_CONTRATO_861801_ESSC18 = "861801"
IDE_CONTRATO_REQUERIDO_861801_ESSC18 = "975"

# Cód Entidad Cobrar=ESSC18 + Código=890405 -> IDE Contrato según inserción
CODIGO_IDE_CONTRATO_890405_ESSC18 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_ESSC18 = "968"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_ESSC18 = "975"  # Si NO tiene código 861801

# Cód Entidad Cobrar=EPS037 + Código=906340 -> IDE Contrato debe ser 962
CODIGO_IDE_CONTRATO_906340_EPS037 = "906340"
ENTIDAD_IDE_CONTRATO_EPS037 = "EPS037"
IDE_CONTRATO_REQUERIDO_906340_EPS037 = "962"

# Cód Entidad Cobrar=EPS037 + Código=861801 -> IDE Contrato debe ser 961
CODIGO_IDE_CONTRATO_861801_EPS037 = "861801"
IDE_CONTRATO_REQUERIDO_861801_EPS037 = "961"

# Cód Entidad Cobrar=EPS037 + Código=890405 -> IDE Contrato según inserción
CODIGO_IDE_CONTRATO_890405_EPS037 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_EPS037 = "962"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPS037 = "961"  # Si NO tiene código 861801

# Código 906340 + Cód Entidad Cobrar=EPSS41 -> IDE 959
CODIGO_IDE_CONTRATO_906340_EPSS41 = "906340"
IDE_CONTRATO_REQUERIDO_906340_EPSS41 = "959"

# Código 861801 + Cód Entidad Cobrar=EPSS41 -> IDE 958
CODIGO_IDE_CONTRATO_861801_EPSS41 = "861801"
IDE_CONTRATO_REQUERIDO_861801_EPSS41 = "958"

# ESS062 + Código 861801 -> IDE Contrato debe ser 922
CODIGO_IDE_CONTRATO_861801_ESS062 = "861801"
ENTIDAD_IDE_CONTRATO_ESS062 = "ESS062"
IDE_CONTRATO_REQUERIDO_861801_ESS062 = "922"

# ESS062 + Código 890405 -> IDE Contrato según inserción
CODIGO_IDE_CONTRATO_890405_ESS062 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_ESS062 = "921"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_ESS062 = "922"  # NO tiene código 861801

# ESSC62 + Código 861801 -> IDE Contrato debe ser 863
CODIGO_IDE_CONTRATO_861801_ESSC62 = "861801"
ENTIDAD_IDE_CONTRATO_ESSC62 = "ESSC62"
IDE_CONTRATO_REQUERIDO_861801_ESSC62 = "863"

# ESSC62 + Código 890405 -> IDE Contrato según si tiene 890405
CODIGO_IDE_CONTRATO_890405_ESSC62 = "890405"
CODIGO_A_BUSCAR_890405_ESSC62 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_ESSC62 = "862"  # tiene código 890405
IDE_CONTRATO_SIN_INSERCION_890405_ESSC62 = "863"  # NO tiene código 890405

# Código 890405 + Cód Entidad Cobrar=EPSS41 -> IDE según inserción
CODIGO_IDE_CONTRATO_890405_EPSS41 = "890405"
IDE_CONTRATO_CON_INSERCION_890405_EPSS41 = "959"  # Si tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_EPSS41 = "958"  # Si NO tiene código 861801

# Código=890405 + Entidad=86000 -> IDE Contrato según si tiene 861801
CODIGO_IDE_CONTRATO_890405_86000 = "890405"
ENTIDAD_IDE_CONTRATO_890405_86000 = "86000"
IDE_CONTRATO_CON_INSERCION_890405_86000 = "919"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_86000 = "920"  # no tiene código 861801

# Código=861801 + Entidad=RES004 -> IDE Contrato = 908
CODIGO_IDE_CONTRATO_861801_RES004 = "861801"
ENTIDAD_IDE_CONTRATO_861801_RES004 = "RES004"
IDE_CONTRATO_REQUERIDO_861801_RES004 = "908"

# Código=890405 + Entidad=RES004 -> IDE Contrato según si tiene 861801
CODIGO_IDE_CONTRATO_890405_RES004 = "890405"
ENTIDAD_IDE_CONTRATO_890405_RES004 = "RES004"
IDE_CONTRATO_CON_INSERCION_890405_RES004 = "908"  # tiene código 861801
IDE_CONTRATO_SIN_INSERCION_890405_RES004 = "909"  # no tiene código 861801
CODIGO_INSERCION_BUSCAR_RES004 = "861801"

# Código=861801 + Entidad=86000 -> IDE Contrato = 920
CODIGO_IDE_CONTRATO_861801_86000 = "861801"
ENTIDAD_IDE_CONTRATO_861801_86000 = "86000"
IDE_CONTRATO_REQUERIDO_861801_86000 = "920"

# =============================================================================
# URGENCIAS - Entidad -> IDE Contrato (mapeo directo)
# =============================================================================

URGENCIA_ENTIDAD_CONTRATO: dict[str, str] = {
    "86000": "919",
    "86": "911",
    "5177": "917",
    "RES004": "909",
    "RES001": "992",
    "983": "0001",
    "984": "0001",
    "AT1306": "867",
    "1327": "882",
    "AT1317": "887",
    "1318": "912",
    "AT1324": "915",
    "AT1329": "916",
    "MIN001": "918",
    "000124": "995",
    "1423": "966",
    "1429": "884",
    "1425": "880",
    "144": "885",
    "EPSS005": "934",
    "EPSC005": "931",
}

URGENCIA_ENTIDAD_MULTIPLE_CONTRATO: dict[str, set] = {
    "MIN001": {"910", "918"},
}

# =============================================================================
# URGENCIAS - Cups Equivalentes
# =============================================================================

# Código CUPS 890205 -> 890405 es su equivalente
CODIGO_CUPS_EQUIVALENTE_890205 = "890205"
CODIGO_CUPS_EQUIVALENTE_SUSTITUTO_890405 = "890405"
ENTIDADES_PERMITIDAS_890205 = frozenset({"ESS118", "ESSC18"})

# =============================================================================
# URGENCIAS - Sala de Observación
# =============================================================================

ESTANCIA_SALA_OBSERVACION_THRESHOLD_SECONDS = 6 * 3600  # 21600

ENTIDADES_SALA_OBSERVACION_05DSB01 = frozenset({"ESS118", "ESSC18"})

CODIGO_SALA_OBSERVACION_CORTA = "5DSB01"  # ≤ 6 horas
CODIGO_SALA_OBSERVACION_LARGA_ESS = "05DSB01"  # > 6 horas (ESS118, ESSC18)
CODIGO_SALA_OBSERVACION_LARGA_OTRAS = "129B02"  # > 6 horas (otras entidades)

CODIGOS_SALA_OBSERVACION_ACTIVADORES = frozenset({
    "5DSB01",
    "05DSB01",
    "129B02",
    "38114",
    "38915",
})

CODIGOS_SALA_OBSERVACION_OBLIGATORIOS = frozenset({
    "890701",
    "890601",
})

# ESS118/ESSC18 + Urgencias NO pueden tener 129B02
ENTIDADES_ESS_PROHIBIDO_129B02 = frozenset({"ESS118", "ESSC18"})
CODIGO_SALA_PROHIBIDO_ESS = "129B02"

# Urgencias NO puede tener 890601H
CODIGO_URGENCIAS_PROHIBIDO = "890601H"

# Entidades distintas a ESS118/ESSC18 NO pueden tener 05DSB01 en Urgencias
ENTIDADES_ESS_PERMITIDO_05DSB01 = frozenset({"ESS118", "ESSC18"})
CODIGO_05DSB01_PROHIBIDO_OTRAS = "05DSB01"

# Tarifario SOAT excluido de reglas de estancia (>6h / ≤6h)
VALOR_TARIFARIO_SOAT = "SOAT"

# SOAT + Urgencias + Estancia >6h -> código 38114
CODIGO_SOAT_SALA_OBSERVACION_LARGA = "38114"
# SOAT + Urgencias + Estancia ≤6h -> código 38915
CODIGO_SOAT_SALA_OBSERVACION_CORTA = "38915"

# SOAT + Urgencias + tiene 38114 o 38915 -> debe tener 39145 y 39131
CODIGOS_SOAT_OBLIGATORIOS_SALA = frozenset({
    "39145",
    "39131",
})

# SOAT + Urgencias NO puede tener código 39133
CODIGO_SOAT_URGENCIAS_PROHIBIDO = "39133"

# SOAT + Hospitalización NO puede tener códigos 39145, 38915
CODIGOS_SOAT_HOSPITALIZACION_PROHIBIDOS = frozenset({
    "39145",
    "38915",
})

# SOAT + Urgencias + códigos 39145, 38114, 38915, 39131 -> cantidad debe ser = 1
CODIGOS_SOAT_CANTIDAD_OBLIGATORIA = frozenset({
    "39145",
    "38114",
    "38915",
    "39131",
})

# SOAT + Hospitalización códigos 38114 y 39131 con cantidades especiales
CODIGOS_SOAT_HOSPITALIZACION_CANTIDAD = frozenset({
    "38114",
    "39131",
})

# SOAT + Hospitalización debe tener códigos 39133, 38114 y 39131
CODIGOS_SOAT_HOSPITALIZACION_OBLIGATORIOS = frozenset({
    "39133",
    "38114",
    "39131",
})

# =============================================================================
# HOSPITALIZACIÓN - Reglas
# =============================================================================

# Hospitalización debe tener 129B02, 890601H y 890601
CODIGOS_HOSPITALIZACION_OBLIGATORIOS = frozenset({
    "129B02",
    "890601H",
    "890601",
})

# Hospitalización NO puede tener 05DSB01, 5DSB01 ni 890701
CODIGOS_HOSPITALIZACION_PROHIBIDOS = frozenset({
    "05DSB01",
    "5DSB01",
    "890701",
})

# Código CUPS 890601H -> Centro de costo "HOSPITALIZACIÓN - ESTANCIA GENERAL"
CODIGO_CUPS_HOSPITALIZACION = "890601H"
CENTRO_COSTO_HOSPITALIZACION_ESTANCIA = "HOSPITALIZACIÓN - ESTANCIA GENERAL"

# Códigos que deben tener centro de costo "HOSPITALIZACIÓN - ESTANCIA GENERAL"
CODIGOS_HOSPITALIZACION_ESTANCIA = frozenset({
    "890601H",
    "39133",
})

# Código CUPS 861101 -> Centro de costo "URGENCIAS"
CODIGO_CUPS_URGENCIAS_861101 = "861101"
CENTRO_COSTO_URGENCIAS = "URGENCIAS"

# Código CUPS 939402 + Tipo Factura=Hospitalización -> Error
CODIGO_CUPS_HOSPITALIZACION_PROHIBIDO = "939402"
ERROR_HOSPITALIZACION_NO_PERMITIDO = "No se debe facturar en Hospitalización, incluido en internación"

# Código CUPS 12333 + Tipo Factura=Hospitalización -> Error
CODIGO_12333_HOSPITALIZACION_PROHIBIDO = "12333"
ERROR_12333_HOSPITALIZACION_NO_PERMITIDO = "Código 12333 (Consulta Prioritaria) no permitido en Hospitalización"

# Servicios CUPS reemplazables
CODIGOS_CUPS_REEMPLAZABLES = frozenset({
    "890201",  # -> 890701
    "129B01",  # -> 129B02
})
CODIGO_CUPS_SUSTITUTO_890701 = "890701"
CODIGO_CUPS_SUSTITUTO_129B02 = "129B02"

# =============================================================================
# URGENCIAS - Control de Errores
# =============================================================================

ERROR_TIPO_URGENCIAS = [
    "Otros",
    "Soportes de Carpeta",
    "Factura Abierta",
]

ERROR_ESTADO_URGENCIAS = [
    "S",
    "N",
]

ERROR_RESPONSABLE_URGENCIAS = [
    "ALEJANDRA ESPAÑA",
    "CARLOS OMAR",
    "DANIELA PAEZ",
    "ANGIE ARIAS",
]

RESPONSABLE_NOMBRES_COMPLETOS: dict[str, str] = {
    "ALEJANDRA ESPAÑA": "ESPAÑA DIAZ LORENY ALEJANDRA",
    "CARLOS OMAR": "MEZA FERNANDEZ CARLOS OMAR",
    "DANIELA PAEZ": "PAEZ YULIETH DANIELA",
    "ANGIE ARIAS": "ARIAS CULCHA ANGIE CAROLINA",
}

CRONOGRAMA_NOMBRE_MAP: dict[str, str] = {
    "CARLOS": "CARLOS OMAR",
    "ALEJANDRA": "ALEJANDRA ESPAÑA",
    "YULIETH": "DANIELA PAEZ",
    "CAROLINA": "ANGIE ARIAS",
}

# Centros de costo válidos para Urgencias
CENTROS_COSTO_VALIDOS_URGENCIAS = frozenset({
    "URGENCIAS",
    "APOYO TERAPEUTICO-FARMACIA E INSUMOS.",
    "APOYO DIAGNOSTICO-LABORATOR CLINICO",
    "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN",
    "HOSPITALIZACIÓN - ESTANCIA GENERAL",
    "APOYO DIAGNOSTICO-IMAGENOLOGIA",
    "TRASLADOS",
    "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO",
})

# =============================================================================
# URGENCIAS - Códigos CUPS Capita (ESS118)
# =============================================================================

URGENCIAS_CAPITA_CUPS_CODES = frozenset({
    "05DSB01",
    "12333",
    "129B02",
    "180201",
    "184101",
    "1906317",
    "230101",
    "230102",
    "230103",
    "230201",
    "230202",
    "230203",
    "231101",
    "232101",
    "232102",
    "232103",
    "232201",
    "232401",
    "232402",
    "234401",
    "234402",
    "237102",
    "237103",
    "237301",
    "237302",
    "237304",
    "240301",
    "243201",
    "274901",
    "275101",
    "275102",
    "275104",
    "275203",
    "389301",
    "579401",
    "579501",
    "5DS002",
    "5DS003",
    "5DS004",
    "5DSB01",
    "601T01",
    "697101",
    "735301",
    "735980",
    "750303",
    "754101",
    "786902",
    "829910",
    "858101",
    "860207",
    "861201",
    "861202",
    "861203",
    "861801",
    "862701",
    "865101",
    "865102",
    "865201",
    "865202",
    "865203",
    "865204",
    "865205",
    "865206",
    "865207",
    "865208",
    "865210",
    "869401",
    "869501",
    "870001",
    "870003",
    "870005",
    "870101",
    "870102",
    "870107",
    "870108",
    "871010",
    "871020",
    "871030",
    "871040",
    "871050",
    "871091",
    "871111",
    "871112",
    "871121",
    "871129",
    "872002",
    "873111",
    "873112",
    "873121",
    "873122",
    "873202",
    "873204",
    "873205",
    "873206",
    "873210",
    "873312",
    "873313",
    "873314",
    "873333",
    "873335",
    "873340",
    "873411",
    "873420",
    "873431",
    "88001",
    "88201",
    "88202",
    "890101",
    "890105",
    "890108",
    "890114",
    "890201",
    "890203",
    "890205",
    "890206",
    "890208",
    "890301",
    "890303",
    "890305",
    "890306",
    "890308",
    "890601",
    "890601H",
    "890701",
    "890703",
    "892901",
    "892904",
    "893812",
    "895004",
    "895101",
    "897011",
    "897012",
    "901001",
    "901101",
    "901102",
    "901104",
    "901106",
    "901107",
    "901111",
    "901210",
    "901230",
    "901235",
    "901304",
    "901305",
    "901325",
    "901326",
    "902045",
    "902049",
    "902204",
    "902207",
    "902210",
    "902211",
    "902213",
    "902214",
    "902215",
    "902216",
    "902217",
    "902221",
    "902223",
    "903026",
    "903426",
    "903803",
    "903805",
    "903809",
    "903815",
    "903816",
    "903818",
    "903823",
    "903826",
    "903840",
    "903841",
    "903842",
    "903843",
    "903844",
    "903845",
    "903856",
    "903859",
    "903863",
    "903864",
    "903868",
    "903876",
    "903883",
    "903895",
    "904508",
    "904902",
    "906039",
    "906208",
    "9062081",
    "906249",
    "906249PR",
    "906317",
    "906914",
    "906915",
    "907002",
    "907003",
    "907004",
    "907005",
    "907008",
    "907106",
    "907202",
    "90DS02",
    "911015",
    "911016",
    "911017",
    "911018",
    "911019",
    "911020",
    "933701",
    "935001",
    "935101",
    "935301",
    "935302",
    "935303",
    "935304",
    "935305",
    "935306",
    "935401",
    "935701",
    "935901",
    "936801",
    "939402",
    "943102",
    "944002",
    "944102",
    "944202",
    "950601",
    "960701",
    "961401",
    "961601",
    "963301",
    "963801",
    "963901",
    "965101",
    "965201",
    "965301",
    "965901",
    "971101",
    "971201",
    "971401",
    "971601",
    "972101",
    "972201",
    "973201",
    "973801",
    "974301",
    "977101",
    "977501",
    "978301",
    "981101",
    "981201",
    "981701",
    "982101",
    "982201",
    "982501",
    "982601",
    "982701",
    "982801",
    "982901",
    "990201",
    "990203",
    "990204",
    "990205",
    "990206",
    "990211",
    "991402",
    "991403",
    "991601",
    "991800",
    "991801",
    "992102",
    "992201",
    "992901",
    "992990",
    "993102",
    "993104",
    "993105",
    "993106",
    "993107",
    "993120",
    "993122",
    "993130",
    "993501",
    "993502",
    "993503",
    "993504",
    "993505",
    "993506",
    "993507",
    "993508",
    "993509",
    "993510",
    "993512",
    "993513",
    "993520",
    "993522",
    "994101",
    "994301",
    "995201",
    "995202",
    "997002",
    "997103",
    "997106",
    "997107",
    "997301",
    "P0000002",
    "P0000003",
    "P0000008",
    "P0000009",
    "P0000010",
    "P0000011",
    "P0000012",
    "P0000013",
    "P0000014",
    "P0000081",
    "P0000221",
    "P0000288",
    "P0000775",
    "P0000776",
    "P0000777",
    "P0000778",
    "P0000779",
    "P0001244",
    "P0001245",
    "P0001246",
    "P0001619",
    "P0001620",
    "P0001852",
    "P0001853",
    "T0001630",
    "T0001634",
})

# =============================================================================
# REVISIÓN - Códigos exentos de reglas de cantidad
# =============================================================================

CODIGOS_REVISION_CANTIDAD_EXENTOS = frozenset({
    "890601",
    "129B02",
    "890701",
    "05DSB01",
    "5DSB01",
    "890601H",
    "39145",
    "38114",
    "38915",
    "39131",
    "39133",
})

# Código Tipo Procedimiento que necesita Laboratorio = "No" como excepción
CODIGO_TIPO_PROCEDIMIENTO_REVISION_LAB = "02"
LABORATORIO_REVISION_EXENTO = "No"

# Códigos Tipo Procedimiento con regla de cantidad máxima 20
CODIGOS_TIPO_PROC_09_12 = frozenset({
    "09",
    "12",
    "13",
})
CODIGO_EXENTO_V03AN0101 = "V03AN0101"
CANTIDAD_MAX_09_12 = 20

CODIGO_ESPECIAL_02_LAB = "903883"
CANTIDAD_MAX_02_LAB = 2
CANTIDAD_MAX_02_LAB_903883 = 5

# =============================================================================
# LÍMITES ESPECÍFICOS POR CÓDIGO
# =============================================================================

CODIGOS_LIMITE_ESPECIFICO: dict[str, int] = {
    "939403": 2,
    "939402": 8,
}

# =============================================================================
# URGENCIAS - Reglas de cantidades
# =============================================================================

URGENCIAS_CODIGOS_CANTIDAD_MAX_1 = frozenset({
    "05DSB01",
    "5DSB01",
    "890601",
    "890701",
    "129B02",
    "12333",
})

URGENCIAS_SOAT_CODIGOS_CANTIDAD_MAX_1 = frozenset({
    "39133",
})

URGENCIAS_NO_SOAT_CODIGOS_CANTIDAD_MAX_1 = frozenset({
    "890601H",
})

# =============================================================================
# HOSPITALIZACIÓN - Reglas de cantidades
# =============================================================================

CODIGO_HOSPITALIZACION_ESTANCIA = "129B02"
CODIGO_HOSPITALIZACION_CAMAS = "890601"

# =============================================================================
# URGENCIAS - Reglas REVERSE: IDE Contrato → Código CUPS esperado
# =============================================================================

IDE_CONTRATO_REVERSE = {
    "986": "906340",
}

IDE_CONTRATO_REVERSE_977 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "976",
    },
}

IDE_CONTRATO_REVERSE_979 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "967",
    },
}

IDE_CONTRATO_REVERSE_839 = "906340"

IDE_CONTRATO_REVERSE_842 = "906340"

IDE_CONTRATO_REVERSE_958 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "959",
    },
}

IDE_CONTRATO_REVERSE_961 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "962",
    },
}

IDE_CONTRATO_REVERSE_922 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "921",
    },
}

IDE_CONTRATO_REVERSE_863 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "862",
    },
}

IDE_CONTRATO_REVERSE_975 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "968",
    },
}

IDE_CONTRATO_REVERSE_920 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "919",
    },
}

IDE_CONTRATO_REVERSE_908 = {
    "codigos_permitidos": ["861801", "890405"],
    "codigo_error_890405": {
        "si_identificacion_tiene": "861801",
        "codigo_deberia_ser": "909",
    },
}

IDE_CONTRATO_REVERSE_ESS118 = {
    "codigos_permitidos": ["735301", "890205", "861801"],
}

# =============================================================================
# PROFESIONALES - Urgencias
# =============================================================================

PROFESIONALES_URGENCIAS: dict[str, dict[str, str]] = {
    "03007": {
        "nombre": "OSPINA MARTINEZ LIZETH",
        "tipo": "ODONTOLOGO",
    },
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
    "03857": {
        "nombre": "TAPIA MONCAYO ANGIE CATHERINE",
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
    "03893": {
        "nombre": "SAMBONI RAMIREZ MARLEN DANIELA",
        "tipo": "MEDICO",
    },
    "03911": {
        "nombre": "JOJOA TULCAN DAVID ALEJANDRO",
        "tipo": "MEDICO",
    },
    "01251": {
        "nombre": "MOSQUERA LOZANO YENIA YADIRIS",
        "tipo": "ODONTOLOGO",
    },
    "01952": {
        "nombre": "SANTACRUZ SALAS MONICA ALEXANDRA",
        "tipo": "PSICOLOGA",
    },
    "03379": {
        "nombre": "RENDON CHAMORRO JENNY FERNANDA",
        "tipo": "JEFE ENFERMERIA",
    },
    "01346": {
        "nombre": "BURBANO NARVAEZ MARITZA ELIANA",
        "tipo": "JEFE ENFERMERIA",
    },
}
