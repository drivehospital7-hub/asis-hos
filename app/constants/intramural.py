"""Constantes del dominio Intramural.

TODAS las reglas de intramural (contratos, centros de costo, cantidades,
CUPS equivalentes) SOLO se aplican cuando el encabezado del Excel
"Tipo Factura Descripción" tiene valor "Intramural".
"""

from __future__ import annotations

AREA_INTRAMURAL = "intramural"

# Las reglas intramural solo aplican cuando Tipo Factura Descripción = este valor
TIPO_FACTURA_INTRAMURAL = "Intramural"

# =============================================================================
# INTRAMURAL - EXAMENES PYM EVENTO
# =============================================================================

CODIGOS_EXAMENES_PYM_EVENTO: frozenset[str] = frozenset({
    "906127",  # Toxoplasma Gondii Anticuerpos IG G
    "906129",  # Toxoplasma Gondii Anticuerpos IG M
    "906205",  # Citomegalovirus Anticuerpos IGG
    "906206",  # Citomegalovirus Anticuerpos IGM
    "906241",  # Rubeola Anticuerpos IGG
    "906131",  # Trypanosoma Cruzi Anticuerpos IG G
})

# =============================================================================
# INTRAMURAL - CODIGOS PYM (Promoción y Prevención)
# =============================================================================

CODIGOS_PYM_INTRAMURAL: dict[str, str] = {
    "990211": "Consejeria VIH",
    "897011": "Monitoria Fetal Anteparto",
    "995201": "Otras Vacunaciones del Programa Ampliado de Inmunizaciones SOD",
    "993513": "Vacuna contra el Virus del Papiloma Humano VPH",
    "993520": "Vacunacion Combinada contra Sarampion y Rubeola (Sr) (Doble Viral)",
    "993106": "Vacunacion contra Neumococo",
    "993502": "Vacunacion contra Hepatitis a",
    "993503": "Vacunacion contra Hepatitis B",
    "993505": "Vacunación contra Rabia",
    "993512": "Vacunacion contra Rotavirus",
    "993102": "Vacunacion contra Tuberculosis (BCG)",
    "993509": "Vacunacion contra Varicela",
}

# =============================================================================
# INTRAMURAL - PYM RUTAS
# =============================================================================

CODIGOS_PYM_RUTAS: dict[str, str] = {
    "735301": "Asistencia del Parto con o sin Episiorrafia o Perineorrafia",
    "903815": "Colesterol de Alta Densidad [HDL]",
    "903818": "Colesterol Total",
    "901107": "Coloracion Gram y Lectura para Cualquier Muestra",
    "907002": "Coprologico",
    "903895": "Creatinina en Suero u otros Fluidos",
    "901304": "Examen Directo Fresco de Cualquier Muestra",
    "903841": "Glucosa en Suero. LCR u otro Fluido Diferente a Orina",
    "903843": "Glucosa Pre y Post Prandial",
    "903844": "Glucosa. Curva de Tolerancia [Cuatro Muestras]",
    "904508": "Gonadotropina Corionica. Subunidad Beta Cualitativa. [BHCG] Prueba de Embarazo en Orina o Suero",
    "902211": "Hematocrito",
    "911016": "Hemoclasificacion (Grupo Sanguineo y Factor Rh)",
    "902213": "Hemoglobina",
    "902207": 'Hemograma I [Hemoglobina. Hematocrito y Leucograma] Metodo Manual',
    "902210": "Hemograma IV [Hemoglobina. Hematocrito. Recuento de Eritrocitos. Indices Eritrocitarios",
    "902214": "Hemoparasitos Extendido de Gota Gruesa",
    "1906317": "Hepatitis B. Antigeno de Superficie( Rapida)",
    "904902": "Hormona Estimulante del Tiroides [TSH]",
    "903859": "Potasio en Suero u otros Fluidos",
    "906915": "Prueba no Treponémica Manual",
    "907008": "Sangre Oculta en Materia Fecal [Guayaco o Equivalente]",
    "906039": "Treponema Pallidum Anticuerpos (Prueba Treponemica) Manual o Semiautomatizada o Automatizada",
    "903868": "Trigliceridos",
    "907106": "Uroanálisis",
    "901235": "Urocultivo (Antibiograma de Disco)",
    "993122": "Vacunacion Combinada contra Difteria. Tetanos y Tos Ferina (DPT)",
    "993130": "Vacunacion Combinada contra Haemophilus Influenza Tipo B. Difteria. Tetanos. Tos Ferina y Hepatitis B (Pentavalente)",
    "993522": "Vacunacion Combinada contra Sarampion. Parotiditis y Rubeola (SRP) (Triple Viral)",
    "993120": "Vacunacion Combinada contra Tetanos y Difteria [TD]",
    "993104": "Vacunacion contra Haemophilus Influenza Tipo B",
    "993510": "Vacunacion contra Influenza",
    "993501": "Vacunacion contra Poliomielitis (VOP o IVP)",
    "906249PR": "VIH -Prueba Rapida",
}

# =============================================================================
# INTRAMURAL - PYM NECESITAN DIAGNOSTICOS
# Codigos Dx Principal (CIE-10) que requieren diagnóstico para PyM
# =============================================================================

CODIGOS_PYM_NECESITAN_DX: frozenset[str] = frozenset({
    "Z359",   # SUPERVISION DE EMBARAZO DE ALTO RIESGO
    "Z000",   # EXAMEN MEDICO GENERAL
    "Z108",   # OTROS CONTROLES GENERALES DE SALUD DE RUTINA
    "Z103",   # CONTROL GENERAL DE SALUD A INTEGRANTES DE EQUIPOS DEPORTIVOS
    "Z001",   # CONTROL DE SALUD DE RUTINA DEL NIÑO
    "Z002",   # EXAMEN DURANTE PERIODO DE CRECIMIENTO RAPIDO
    "Z238",   # NECESIDAD DE INMUNIZACION SOLO CONTRA OTRA ENFERMEDAD BACTERIANA
    "Z316",   # CONSEJO Y ASESORAMIENTO GENERAL SOBRE LA PROCREACION
    "Z321",   # EMBARAZO CONFIRMADO
    "Z358",   # SUPERVISION DE OTROS EMBARAZOS DE ALTO RIESGO
    "Z300",   # CONSEJO Y ASESORAMIENTO GENERAL SOBRE LA ANTICONCEPCION
    "Z717",   # CONSULTA PARA ASESORIA SOBRE EL VIH
    "Z349",   # SUPERVISION DE EMBARAZO NORMAL NO ESPECIFICADO
    "Z356",   # SUPERVISION DE PRIMIGESTA MUY JOVEN
    "Z320",   # EMBARAZO (AUN) NO CONFIRMADO
    "Z003",   # EXAMEN DEL ESTADO DE DESARROLLO DEL ADOLESCENTE
    "Z350",   # SUPERVISION DE EMBARAZO CON HISTORIA DE ESTERILIDAD
    "Z133",   # EXAMEN DE PESQUISA ESPECIAL PARA TRASTORNOS MENTALES
    "Z352",   # SUPERVISION DE EMBARAZO CON OTRO RIESGO OBSTETRICO
    "Z113",   # EXAMEN DE PESQUISA ESPECIAL PARA INFECCIONES DE TRANSMISION SEXUAL
})

# =============================================================================
# INTRAMURAL - TABLA COMPLETA DX (código → descripción)
# =============================================================================

DX_PRINCIPAL_INTRAMURAL: dict[str, str] = {
    "Z359": "SUPERVISION DE EMBARAZO DE ALTO RIESGO, SIN OTRA ESPECIFICACION",
    "Z000": "EXAMEN MEDICO GENERAL",
    "Z108": "OTROS CONTROLES GENERALES DE SALUD DE RUTINA DE OTRAS SUBPOBLACIONES DEFINIDAS",
    "Z103": "CONTROL GENERAL DE SALUD DE RUTINA A INTEGRANTES DE EQUIPOS DEPORTIVOS",
    "Z001": "CONTROL DE SALUD DE RUTINA DEL NIÑO",
    "Z002": "EXAMEN DURANTE EL PERIODO DE CRECIMIENTO RAPIDO EN LA INFANCIA",
    "Z238": "NECESIDAD DE INMUNIZACION SOLO CONTRA OTRA ENFERMEDAD BACTERIANA",
    "Z316": "CONSEJO Y ASESORAMIENTO GENERAL SOBRE LA PROCREACION",
    "Z321": "EMBARAZO CONFIRMADO",
    "Z358": "SUPERVISION DE OTROS EMBARAZOS DE ALTO RIESGO",
    "Z300": "CONSEJO Y ASESORAMIENTO GENERAL SOBRE LA ANTICONCEPCION",
    "Z717": "CONSULTA PARA ASESORIA SOBRE EL VIRUS DE LA INMUNODEFICIENCIA HUMANA [VIH]",
    "Z349": "SUPERVISION DE EMBARAZO NORMAL NO ESPECIFICADO",
    "Z356": "SUPERVISION DE PRIMIGESTA MUY JOVEN",
    "Z320": "EMBARAZO (AUN) NO CONFIRMADO",
    "Z003": "EXAMEN DEL ESTADO DE DESARROLLO DEL ADOLESCENTE",
    "Z350": "SUPERVISION DE EMBARAZO CON HISTORIA DE ESTERILIDAD",
    "Z133": "EXAMEN DE PESQUISA ESPECIAL PARA TRASTORNOS MENTALES Y DEL COMPORTAMIENTO",
    "Z352": "SUPERVISION DE EMBARAZO CON OTRO RIESGO EN LA HISTORIA OBSTETRICA O REPRODUCTIVA",
    "Z113": "EXAMEN DE PESQUISA ESPECIAL PARA INFECCIONES DE TRANSMISION PREDOMINANTEMENTE SEXUAL",
}
