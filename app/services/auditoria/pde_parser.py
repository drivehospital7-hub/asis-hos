"""PDE text parsing — EPS-specific parsers for derecho de peticion PDFs.

Copied from AUDITORA/extractor.py (lines 1-1607), excluding:
- extraer_texto_pdf() (went to extractor.py)
- pytesseract/pdf2image/PIL imports
- hardcoded Tesseract/poppler paths

Includes all EPS parsers, text normalization utilities, and
extraer_datos_derechos() dispatcher.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# ================== FILTROS ==================

PALABRAS_MEDICAS = [
    "DIAGNOSTICO", "DX", "TRIAGE", "ENFERMERIA", "EVOLUCION",
    "MEDICO", "MEDICINA", "PACIENTE INGRESA", "SIGNOS VITALES",
    "TRATAMIENTO", "HOSPITALIZACION", "FORMULA MEDICA"
]


def limpiar_texto(t):
    return " ".join(t.split())


# ================== EXTRAER BLOQUE DE DERECHOS ==================

def extraer_bloque_derechos(texto):
    texto = texto.upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = texto.replace("\n", " ")
    texto = " ".join(texto.split())

    patrones_inicio = [
        "VALIDACION DE DERECHOS",
        "VERIFICACION DE DERECHOS",
        "CONSULTA DE AFILIADOS",
        "FECHA/HORA CONSULTA",
        "ADMINISTRADORA DE LOS RECURSOS",
        "CONSULTA BDUA",
        "AFILIADO EN BDUA",
        "ADRES",
        "CERTIFICADO DE AFILIACION AL PBS",
        "EPS ASOCIACION INDIGENA DEL CAUCA",
    ]

    inicio = -1
    for p in patrones_inicio:
        pos = texto.find(p)
        if pos != -1:
            inicio = pos
            break

    if inicio == -1:
        return ""

    patrones_fin = [
        "DIAGNOSTICO",
        "TRIAGE",
        "EVOLUCION",
        "NOTAS DE ENFERMERIA",
        "ORDEN DE SALIDA",
        "ANEXO TECNICO"
    ]

    fin = len(texto)
    for p in patrones_fin:
        pos = texto.find(p, inicio)
        if pos != -1:
            fin = min(fin, pos)

    return texto[inicio:fin]


# ================== MAPA TIPO DOCUMENTO ==================

MAPA_TIPO_DOC = {
    r"CEDULA\s+DE\s+CIUD": "CC",
    r"\bCC\b": "CC",
    r"TARJETA\s+DE\s+IDEN": "TI",
    r"\bT\.I\b": "TI",
    r"REGISTRO\s+CIVIL": "RC",
    r"\bR\.C\b": "RC",
    r"CEDULA\s+DE\s+EX": "CE",
    r"\bCE\b": "CE",
    r"\bPASAPORTE\b": "PA",
    r"ADULTO\s+SIN\s+IDEN": "AS",
    r"MENOR\s+SIN\s+IDEN": "MS",
    r"CARNE\s+DIPLOM": "CD",
    r"CERTIFICADO\s+NACI": "CN",
    r"NACIDO\s+VIVO": "CN",
    r"PERMISO\s+ESPECIAL\s+DE\s+PERMAN": "PEP",
    r"SALVOCONDUCTO": "SC",
    r"NUMERO\s+UNICO\s+IDENT": "NUIP",
    r"PASAPORTE\s+DE\s+LA\s+ONU": "PONU",
    r"PERMISO\s+POR\s+P": "PT",
}


def normalizar_tipo_doc(texto):
    texto_norm = normalizar_texto(texto)
    for patron, sigla in MAPA_TIPO_DOC.items():
        if re.search(patron, texto_norm):
            return sigla
    return "NO DETECTADO"


def normalizar_texto(t):
    t = t.upper()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def clasificar_estado(estado_raw):
    estado_raw = normalizar_texto(estado_raw)

    estados_activos = ["ACTIVO", "VIGENTE"]
    estados_no_activos = [
        "RETIRADO", "INACTIVO", "SUSPENDIDO", "NO VIGENTE",
        "CANCELADO", "BLOQUEADO", "TRASLADADO", "FALLECIDO"
    ]

    for e in estados_activos:
        if e in estado_raw:
            return "ACTIVO"
    for e in estados_no_activos:
        if e in estado_raw:
            return "NO ACTIVO"
    return "NO CLASIFICADO"


# ================== EXTRACCION DE CAMPOS ==================

def extraer_eps(texto):
    texto = normalizar_texto(texto)
    encabezado = texto[:500]

    if (
        ("VALIDACION DE DERECHOS" in encabezado and "AFILIADOS" in encabezado)
        or
        ("CERTIFICADO DE AFILIACION AL PBS" in encabezado and "EMSSANAR" in encabezado)
    ):
        return "EMSSANAR"

    if "EPS ASOCIACION INDIGENA DEL CAUCA" in encabezado or \
       "EPS ASOCIACIÓN INDIGENA DEL CAUCA" in encabezado:
        return "AIC"

    if "CONSULTA DE AFILIADOS" in encabezado and "LINEA" in encabezado:
        return "MALLAMAS"

    if "FECHA/HORA CONSULTA" in encabezado or "FECHA HORA CONSULTA" in encabezado:
        return "NUEVA EPS"

    if "ADMINISTRADORA DE LOS RECURSOS" in encabezado or "BDUA" in encabezado:
        return "ADRES"

    if (
        "FONDO NACIONAL DE PRESTACIONES SOCIALES DEL MAGISTERIO" in encabezado
        or "FOMAG" in encabezado
        or "FIDUPREVISORA" in encabezado
    ):
        return "FOMAG"

    return "NO IDENTIFICADA"


def extraer_numero_documento(texto):
    patron = (
        r"N[ÚU]MERO\s+DE\s+IDENTIFICACI[ÓO]N\s*\*\s*"
        r"([A-Z0-9]{5,25})"
        r"\s+POR\s+FAVOR\s+DIGITAR"
    )
    match = re.search(patron, texto)
    if match:
        return match.group(1)
    return "NO"


def extraer_doc_emssanar(texto):
    texto = normalizar_texto(texto)

    patron_principal = re.search(
        r"TIPO\s+IDENTIFICACION\s*\*?\s*"
        r"([A-Z\s]+?)\s+"
        r"NUMERO\s+DE\s+IDENTIFICACION\s*\*?\s*"
        r"(\d{5,20})",
        texto,
        re.DOTALL
    )

    if patron_principal:
        tipo_raw = patron_principal.group(1).strip()
        numero = patron_principal.group(2).strip()
        tipo = normalizar_tipo_doc(tipo_raw)
        if tipo != "NO DETECTADO":
            return tipo, numero

    patron_directo = re.search(
        r"\b(RC|TI|CC|CE|PA|AS|MS)\s+(\d{5,20})\b",
        texto
    )
    if patron_directo:
        return patron_directo.group(1), patron_directo.group(2)

    numero = extraer_numero_documento(texto)
    if numero != "NO":
        return "NO DETECTADO", numero

    return "NO", "NO"


def extraer_documento_mallamas(texto):
    patron = r"DOCUMENTO\s+([A-Z]{2,5})\s*-\s*(\d{5,20})"
    match = re.search(patron, texto)
    if match:
        return match.group(1), match.group(2)
    return "NO", "NO"


def extraer_nombre_mallamas(texto):
    patron = r"NOMBRE\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+DOCUMENTO"
    match = re.search(patron, texto)
    return match.group(1).strip() if match else "NO"


def extraer_ubicacion_mallamas(texto):
    texto = normalizar_texto(texto)
    dep = re.search(r"DEPARTAMENTO\s+([A-ZÑ ]+?)\s+CIUDAD", texto)
    ciudad = re.search(r"CIUDAD\s+([A-ZÑ ]+?)\s+IPS", texto)
    return (
        dep.group(1).strip() if dep else "NO",
        ciudad.group(1).strip() if ciudad else "NO"
    )


def extraer_ips_mallamas(texto):
    texto = normalizar_texto(texto)
    patron = (
        r"IPS\s+PRIMARIA\s*:?\s*(.+?)\s+ESTADO\s+"
        r"(?:ACTIVO|INACTIVO|SUSPENDIDO|RETIRADO|VIGENTE)"
    )
    match = re.search(patron, texto, re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return "NO"


def extraer_estado_regimen_mallamas(texto):
    texto = normalizar_texto(texto)
    estado = re.search(
        r"ESTADO\s+(ACTIVO|INACTIVO|SUSPENDIDO|RETIRADO|VIGENTE)",
        texto
    )
    regimen = re.search(
        r"REGIMEN\s+(SUBSIDIADO|CONTRIBUTIVO)",
        texto
    )
    return (
        estado.group(1) if estado else "NO",
        regimen.group(1) if regimen else "NO"
    )


def extraer_tipo_afiliado_mallamas(texto):
    patron = r"TIPO\s+AFILIADO\s+([A-Z]+)"
    match = re.search(patron, texto)
    return match.group(1) if match else "NO"


def extraer_nivel_mallamas(texto):
    patron = r"NIVEL\s+([A-C])"
    match = re.search(patron, texto)
    return match.group(1) if match else "NO"


def extraer_portabilidad_mallamas(texto):
    texto = normalizar_texto(texto)

    if "NO SE ENCONTRARON SOLICITUDES VIGENTES" in texto:
        return {
            "PORTABILIDAD VIGENTE": "NO",
            "PERIODO DESDE": "NO",
            "PERIODO HASTA": "NO",
            "TIPO MIGRACION": "NO",
            "RESIDENCIA TEMPORAL": "NO",
            "CELULAR": "NO",
            "ESTADO DE PORTABILIDAD": "NO"
        }

    if "SOLICITUDES DE PORTABILIDAD VIGENTES" not in texto:
        return {"PORTABILIDAD VIGENTE": "NO"}

    datos_port = {"PORTABILIDAD VIGENTE": "SI"}

    periodo = re.search(
        r"PERIODO DESDE:\s*([0-9A-Z\.-]+)\s*HASTA:\s*([0-9A-Z\.-]+)",
        texto
    )
    datos_port["PERIODO DESDE"] = periodo.group(1) if periodo else "NO"
    datos_port["PERIODO HASTA"] = periodo.group(2) if periodo else "NO"

    tipo_mig = re.search(
        r"TIPO MIGRACION\s+([A-Z\s\(\)0-9]+?)\s+FECHA SOLICITUD",
        texto
    )
    datos_port["TIPO MIGRACION"] = tipo_mig.group(1).strip() if tipo_mig else "NO"

    res_temp = re.search(
        r"RES\.?\s*TEMPORAL\s+([A-Z\s\-]+?)\s+MOTIVO",
        texto
    )
    datos_port["RESIDENCIA TEMPORAL"] = res_temp.group(1).strip() if res_temp else "NO"

    cel = re.search(r"CELULAR\s+(\d{10})", texto)
    datos_port["CELULAR"] = cel.group(1) if cel else "NO"

    estados = re.search(
        r"ESTADO\(S\)\s+(.*?)\s+IMPRIMIR",
        texto,
        re.DOTALL
    )
    if not estados:
        estados = re.search(r"ESTADO\(S\)\s+(.*)", texto, re.DOTALL)
    if estados:
        valor = estados.group(1).strip()
        valor = re.sub(r"\s+", " ", valor)
        datos_port["ESTADO DE PORTABILIDAD"] = valor
    else:
        datos_port["ESTADO DE PORTABILIDAD"] = "NO"

    return datos_port


# ================== PARSERS POR EPS ==================

def parser_emssanar(texto):
    texto_norm = normalizar_texto(texto)

    if (
        "CERTIFICADO DE AFILIACION AL PBS" in texto_norm
        and "ESTADO DE SERVICIO" in texto_norm
    ):
        return parser_emssanar_certificado(texto)

    datos = {"EPS": "EMSSANAR"}
    texto_original = texto
    texto_norm = normalizar_texto(texto_original)

    DEPARTAMENTOS = [
        "ARCHIPIELAGO DE SAN ANDRES PROVIDENCIA Y SANTA CATALINA",
        "NORTE DE SANTANDER", "VALLE DEL CAUCA",
        "SAN ANDRES Y PROVIDENCIA", "BOGOTA D C", "BOGOTA",
        "ANTIOQUIA", "ARAUCA", "ATLANTICO", "BOLIVAR", "BOYACA",
        "CALDAS", "CAQUETA", "CASANARE", "CAUCA", "CESAR", "CHOCO",
        "CORDOBA", "CUNDINAMARCA", "GUAINIA", "GUAVIARE", "HUILA",
        "LA GUAJIRA", "MAGDALENA", "META", "NARIÑO", "NARINO",
        "PUTUMAYO", "QUINDIO", "RISARALDA", "SANTANDER", "SUCRE",
        "TOLIMA", "VAUPES", "VAUPÉS", "VICHADA", "AMAZONAS"
    ]

    tipo_doc, numero_doc = extraer_doc_emssanar(texto_original)
    datos["TIPO DE DOCUMENTO"] = tipo_doc
    datos["N° DE DOCUMENTO"] = numero_doc

    reg = re.search(r"REGIMEN\s+(SUBSIDIADO|CONTRIBUTIVO)", texto_norm)
    datos["REGIMEN"] = reg.group(1) if reg else "NO"

    bloque = re.search(
        r"REGIMEN\s+(?:SUBSIDIADO|CONTRIBUTIVO)\s+(.+?)IPS DE ATENCION",
        texto_original, re.DOTALL
    )
    bloque_texto = bloque.group(1) if bloque else texto_original
    bloque_norm = normalizar_texto(bloque_texto)

    datos["NOMBRE"] = "NO"
    datos["DEPARTAMENTO DE AFILIACION"] = "NO"
    datos["MUNICIPIO DE AFILIACION"] = "NO"

    estado_match = re.search(
        r"\b(VIGENTE|ACTIVO|NO VIGENTE|INACTIVO|SUSPENDIDO)\b", bloque_texto
    )
    if estado_match:
        antes_estado = bloque_texto[:estado_match.start()].strip()
        coma = antes_estado.rfind(",")
        if coma != -1:
            izquierda = antes_estado[:coma].strip()
            municipio = antes_estado[coma + 1:].strip()
            izquierda_norm = normalizar_texto(izquierda)
            for dep in sorted(DEPARTAMENTOS, key=len, reverse=True):
                dep_norm = normalizar_texto(dep)
                if izquierda_norm.endswith(dep_norm):
                    pos = len(izquierda) - len(dep)
                    nombre = izquierda[:pos].strip()
                    datos["NOMBRE"] = re.sub(r"\s+", " ", nombre)
                    datos["DEPARTAMENTO DE AFILIACION"] = dep
                    datos["MUNICIPIO DE AFILIACION"] = re.sub(r"\s+", " ", municipio)
                    break

    estado = re.search(
        r"[A-ZÁÉÍÓÚÑ\s]+,\s+[A-ZÁÉÍÓÚÑ\s]+?\s+"
        r"(VIGENTE|ACTIVO|NO VIGENTE|INACTIVO|SUSPENDIDO)\s+",
        bloque_texto, re.DOTALL
    )
    if estado:
        estado_texto = re.sub(r"\s+", " ", estado.group(1)).strip()
        estado_norm = normalizar_texto(estado_texto)
        if "NO VIGENTE" in estado_norm:
            datos["ESTADO"] = "INACTIVO"
        elif "VIGENTE" in estado_norm:
            datos["ESTADO"] = "ACTIVO"
        else:
            datos["ESTADO"] = estado_texto
    else:
        datos["ESTADO"] = "NO"

    ips = re.search(
        r"((?:ESE\s+)?HOSPITAL\s+.+?\(\s*[A-ZÁÉÍÓÚÑ\s]+\s*\))",
        bloque_texto, re.DOTALL
    )
    if not ips:
        ips = re.search(
            r"(?:VIGENTE|ACTIVO|NO VIGENTE|INACTIVO|SUSPENDIDO)\s+"
            r"(.+?)\s+(?:I{1,3}|IV|V|N)\s*-",
            bloque_texto, re.DOTALL
        )
    if ips:
        ips_limpia = re.sub(r"\s+", " ", ips.group(1)).strip()
        datos["IPS PRIMARIA"] = ips_limpia
    else:
        datos["IPS PRIMARIA"] = "NO"

    if datos["IPS PRIMARIA"] != "NO":
        limitante = re.search(r"\b(I{1,3}|IV|V|N)\s*-", bloque_texto)
        segmento_datos = bloque_texto[:limitante.start()] if limitante else bloque_texto

        ubicaciones = re.findall(
            r"([A-ZÁÉÍÓÚÑ]{3,}),\s+([A-ZÁÉÍÓÚÑ]{3,})", segmento_datos
        )
        ips_encontradas = re.findall(
            r"([A-ZÁÉÍÓÚÑ0-9\s\-\.\,]+?\(\s*[A-ZÁÉÍÓÚÑ\s]+\s*\))",
            segmento_datos, re.DOTALL
        )
        ips_encontradas = [re.sub(r"\s+", " ", ips).strip() for ips in ips_encontradas]

        if len(ubicaciones) >= 2:
            datos["DEPARTAMENTO DE PORTABILIDAD"] = ubicaciones[1][0]
            datos["MUNICIPIO DE PORTABILIDAD"] = ubicaciones[1][1]
        else:
            datos["DEPARTAMENTO DE PORTABILIDAD"] = "NO"
            datos["MUNICIPIO DE PORTABILIDAD"] = "NO"

        if len(ips_encontradas) >= 2:
            datos["IPS DE PORTABILIDAD"] = ips_encontradas[1]
        else:
            datos["IPS DE PORTABILIDAD"] = "NO"
    else:
        datos["DEPARTAMENTO DE PORTABILIDAD"] = "NO"
        datos["MUNICIPIO DE PORTABILIDAD"] = "NO"
        datos["IPS DE PORTABILIDAD"] = "NO"

    return datos


def parser_emssanar_certificado(texto):
    datos = {"EPS": "EMSSANAR"}
    texto_original = texto
    texto = normalizar_texto(texto)

    def extraer(patron):
        match = re.search(patron, texto)
        return match.group(1).strip() if match else "NO"

    doc = re.search(
        r"TIPO Y NUMERO DE IDENTIFICACION:\s*([A-Z]{2,3})\s*(\d+)", texto
    )
    if doc:
        datos["TIPO DE DOCUMENTO"] = doc.group(1)
        datos["N° DE DOCUMENTO"] = doc.group(2)
    else:
        datos["TIPO DE DOCUMENTO"] = "NO"
        datos["N° DE DOCUMENTO"] = "NO"

    apellidos = extraer(r"APELLIDOS:\s*(.*?)\s*NOMBRES:")
    nombres = "NO"
    patrones_nombres = [
        r"NOMBRES:\s*(.*?)\s*FICHA SISBEN",
        r"NOMBRES:\s*(.*?)\s*TIPO DE DISCAPACIDAD",
        r"NOMBRES:\s*(.*?)\s*PLAN DE SALUD",
    ]
    for patron in patrones_nombres:
        match = re.search(patron, texto)
        if match:
            nombres = re.sub(r"\s+", " ", match.group(1)).strip()
            break
    datos["NOMBRE"] = f"{nombres} {apellidos}".strip()

    plan = extraer(r"PLAN DE SALUD:\s*(.*?)\s*ESTADO DE SERVICIO")
    if "SUBSIDIADO" in plan:
        datos["REGIMEN"] = "SUBSIDIADO"
    elif "CONTRIBUTIVO" in plan:
        datos["REGIMEN"] = "CONTRIBUTIVO"
    else:
        datos["REGIMEN"] = "NO"

    estado = extraer(r"ESTADO DE SERVICIO:\s*(.*?)\s*FECHA DE AFILIACION")
    datos["ESTADO"] = clasificar_estado(estado)

    datos["DEPARTAMENTO DE AFILIACION"] = extraer(
        r"DEPARTAMENTO DE AFILIACION:\s*(.*?)\s*MUNICIPIO DE AFILIACION:"
    )
    datos["MUNICIPIO DE AFILIACION"] = extraer(
        r"MUNICIPIO DE AFILIACION:\s*(.*?)\s*ZONA:"
    )

    ips = re.search(
        r"IPS DIRECCION SERVICIO\s*(.*?)\s*"
        r"(?:CL|CR|DG|TV|TRANS|CALLE|CARRERA|"
        r"MEDICINA GENERAL|ODONTOLOGIA|PROMOCION Y PREVENCION|"
        r"TIENE DERECHO)",
        texto, re.DOTALL
    )
    if ips:
        ips_limpia = re.sub(r"\s+", " ", ips.group(1)).strip()
        ips_limpia = re.sub(
            r"\b(VIA|CL|CR|DG|TV|CALLE|CARRERA|VEREDA|KM|BARRIO|MZ|MANZANA|LOTE)\b.*",
            "", ips_limpia
        ).strip()
        datos["IPS PRIMARIA"] = ips_limpia
    else:
        ips_fallback = re.search(
            r"((?:ESE\s+)?HOSPITAL\s+.+?\(\s*[A-ZÁÉÍÓÚÑ\s]+\s*\))",
            texto_original, re.DOTALL
        )
        if ips_fallback:
            datos["IPS PRIMARIA"] = re.sub(r"\s+", " ", ips_fallback.group(1)).strip()
        else:
            datos["IPS PRIMARIA"] = "NO"

    datos["DEPARTAMENTO DE PORTABILIDAD"] = "NO"
    datos["MUNICIPIO DE PORTABILIDAD"] = "NO"
    datos["IPS DE PORTABILIDAD"] = "NO"

    return datos


def parser_mallamas(texto):
    datos = {"EPS": "MALLAMAS"}

    tipo_doc, numero_doc = extraer_documento_mallamas(texto)
    datos["TIPO DE DOCUMENTO"] = tipo_doc
    datos["N° DE DOCUMENTO"] = numero_doc

    datos["NOMBRE"] = extraer_nombre_mallamas(texto)

    dep, ciudad = extraer_ubicacion_mallamas(texto)
    datos["DEPARTAMENTO DE AFILIACION"] = dep
    datos["MUNICIPIO DE AFILIACION"] = ciudad

    datos["IPS PRIMARIA"] = extraer_ips_mallamas(texto)

    estado, regimen = extraer_estado_regimen_mallamas(texto)
    datos["ESTADO"] = estado
    datos["REGIMEN"] = regimen

    datos["TIPO DE AFILIADO"] = extraer_tipo_afiliado_mallamas(texto)
    datos["NIVEL"] = extraer_nivel_mallamas(texto)

    texto_norm = normalizar_texto(texto)
    portabilidad = extraer_portabilidad_mallamas(texto_norm)
    datos.update(portabilidad)

    return datos


def parser_aic(texto):
    datos = {"EPS": "AIC EPS"}
    texto = normalizar_texto(texto)

    def extraer(patron):
        match = re.search(patron, texto)
        return match.group(1).strip() if match else "NO"

    doc = re.search(
        r"TIPO Y NUMERO DE IDENTIFICACION:\s*([A-Z]{2,3})\s*(\d+)", texto
    )
    if doc:
        datos["TIPO DE DOCUMENTO"] = doc.group(1)
        datos["N° DE DOCUMENTO"] = doc.group(2)
    else:
        datos["TIPO DE DOCUMENTO"] = "NO"
        datos["N° DE DOCUMENTO"] = "NO"

    apellidos = extraer(r"APELLIDOS:\s*(.*?)\s*NOMBRES:")
    nombres = extraer(r"NOMBRES:\s*(.*?)\s*TIPO DE DISCAPACIDAD:")
    datos["NOMBRE"] = f"{nombres} {apellidos}".strip()

    plan = extraer(r"PLAN DE SALUD:\s*(.*?)\s*ESTADO DE SERVICIO:")
    if "SUBSIDIADO" in plan:
        datos["REGIMEN"] = "SUBSIDIADO"
    elif "CONTRIBUTIVO" in plan:
        datos["REGIMEN"] = "CONTRIBUTIVO"
    else:
        datos["REGIMEN"] = "NO"

    estado = extraer(r"ESTADO DE SERVICIO:\s*(.*?)\s*FECHA DE AFILIACION")
    if "VIGENTE" in estado:
        datos["ESTADO"] = "ACTIVO"
    elif "INACTIVO" in estado:
        datos["ESTADO"] = "NO ACTIVO"
    elif "SUSPENDIDO" in estado:
        datos["ESTADO"] = "NO ACTIVO"
    else:
        datos["ESTADO"] = "NO"

    datos["DEPARTAMENTO DE AFILIACION"] = extraer(
        r"DEPARTAMENTO DE AFILIACION:\s*(.*?)\s*MUNICIPIO DE AFILIACION:"
    )
    datos["MUNICIPIO DE AFILIACION"] = extraer(
        r"MUNICIPIO DE AFILIACION:\s*(.*?)\s*DEPARTAMENTO DE PORTABILIDAD:"
    )
    datos["DEPARTAMENTO DE PORTABILIDAD"] = extraer(
        r"DEPARTAMENTO DE PORTABILIDAD:\s*(.*?)\s*ZONA:"
    )
    datos["MUNICIPIO DE PORTABILIDAD"] = extraer(
        r"MUNICIPIO DE PORTABILIDAD:\s*(.*?)\s*N -"
    )

    ips = re.search(r"IPS DIRECCION SERVICIO\s*(.*?)\s*CALLE", texto)
    datos["IPS PRIMARIA"] = ips.group(1).strip() if ips else "NO"

    return datos


def parser_nueva_eps_fallback(texto):
    datos = {}
    texto = normalizar_texto(texto)

    doc = re.search(r"\b(CC|TI|RC|CE|PA)\s+(\d{5,15})\b", texto)
    if doc:
        datos["TIPO DE DOCUMENTO"] = doc.group(1)
        datos["N° DE DOCUMENTO"] = doc.group(2)
    else:
        datos["TIPO DE DOCUMENTO"] = "NO"
        datos["N° DE DOCUMENTO"] = "NO"

    nombre = re.search(r"\d{5,15}\s+([A-ZÑ ]+?)\s+(ACTIVO|INACTIVO)", texto)
    datos["NOMBRE"] = nombre.group(1).strip() if nombre else "NO"

    estado = re.search(r"\b(ACTIVO|INACTIVO)\b", texto)
    datos["ESTADO"] = estado.group(1) if estado else "NO"

    ubi = re.search(
        r"\b(PUTUMAYO|NARIÑO|CAUCA|HUILA|VALLE|CAQUETA)\s+([A-ZÑ]+)\s+\d{7,10}",
        texto
    )
    if ubi:
        datos["DEPARTAMENTO DE AFILIACION"] = ubi.group(1)
        datos["MUNICIPIO DE AFILIACION"] = ubi.group(2)
    else:
        datos["DEPARTAMENTO DE AFILIACION"] = "NO"
        datos["MUNICIPIO DE AFILIACION"] = "NO"

    cat = re.search(r"\b(SISBEN-\d+|A|B|C)\b", texto)
    datos["CATEGORIA"] = cat.group(1) if cat else "NO"

    ips = re.search(r"(E\.?S\.?E\.?\s+HOSPITAL\s+[A-ZÑ ]+)", texto)
    datos["IPS PRIMARIA"] = ips.group(1).strip() if ips else "NO"

    if "SUBSIDIADO" in texto:
        datos["REGIMEN"] = "SUBSIDIADO"
    elif "CONTRIBUTIVO" in texto:
        if "BENEFICIARIO" in texto:
            datos["REGIMEN"] = "CONTRIBUTIVO BENEFICIARIO"
        else:
            datos["REGIMEN"] = "CONTRIBUTIVO"
    else:
        datos["REGIMEN"] = "NO DETECTADO"

    datos["EPS"] = "NUEVA EPS"
    return datos


def parser_nueva_eps(texto):
    texto_original = texto
    datos = {}
    texto = normalizar_texto(texto)

    def extraer(patron):
        match = re.search(patron, texto)
        return match.group(1).strip() if match else "NO"

    datos["N° DE DOCUMENTO"] = extraer(r"IDENTIFICACION:\s*(\d+)")
    datos["TIPO DE DOCUMENTO"] = extraer(r"TIPO IDENTIFICACION:\s*([A-Z]+)")
    datos["NOMBRE"] = extraer(
        r"NOMBRE USUARIO:\s*(.*?)\s*(?=ESTADO AFILIACION USUARIO)"
    )

    estado_raw = extraer(
        r"ESTADO AFILIACION USUARIO:\s*(.*?)\s*(?=FECHA NACIMIENTO|DEPARTAMENTO)"
    )
    datos["ESTADO"] = clasificar_estado(estado_raw)

    dep = extraer(r"DEPARTAMENTO:\s*(.*?)\s*(?=MUNICIPIO)")
    mun = extraer(r"MUNICIPIO:\s*(.*?)\s*(?=TELEFONO|TIPO AFILIADO)")

    if dep == "NO" or dep == "" or "VEREDA" in dep:
        fallback_ubi = re.search(
            r"\b(PUTUMAYO|NARIÑO|CAUCA|HUILA|VALLE|CAQUETA)\s+([A-ZÑ]+)\s+\d{7,10}",
            texto
        )
        if fallback_ubi:
            dep = fallback_ubi.group(1)
            mun = fallback_ubi.group(2)

    datos["DEPARTAMENTO DE AFILIACION"] = dep
    datos["MUNICIPIO DE AFILIACION"] = mun

    tipo_afiliado = extraer(
        r"TIPO AFILIADO:\s*(.*?)\s*(?=CATEGORIA AFILIADO)"
    )
    categoria_afiliado = extraer(
        r"CATEGORIA AFILIADO:\s*(.*?)\s*(?=SEMANAS COTIZADAS|IPS PRIMARIA)"
    )

    if categoria_afiliado in ["NO", ""]:
        cat_fallback = re.search(r"\b(SISBEN-\d+|A|B|C)\b", texto)
        if cat_fallback:
            categoria_afiliado = cat_fallback.group(1)

    datos["CATEGORIA"] = categoria_afiliado

    ips = extraer(r"IPS PRIMARIA:\s*(.*?)\s*(?=AUTORIZACIONES|$)")
    if ips == "NO":
        ips_fallback = re.search(r"(E\.?S\.?E\.?\s+HOSPITAL\s+[A-ZÑ ]+)", texto)
        if ips_fallback:
            ips = ips_fallback.group(1)
    datos["IPS PRIMARIA"] = ips

    if any(x in tipo_afiliado for x in ["SEGUNDOS COTIZANTES", "CABEZA DE FAMILIA"]):
        datos["REGIMEN"] = "CONTRIBUTIVO COTIZANTE"
    elif "BENEFICIARIO" in tipo_afiliado:
        if "SISBEN" in categoria_afiliado:
            datos["REGIMEN"] = "SUBSIDIADO"
        elif categoria_afiliado.strip() in {"A", "B", "C"}:
            datos["REGIMEN"] = "CONTRIBUTIVO BENEFICIARIO"
        else:
            datos["REGIMEN"] = "NO CLASIFICADO"
    else:
        datos["REGIMEN"] = "NO DETECTADO"

    datos["EPS"] = "NUEVA EPS"

    estructura_valida = (
        datos["N° DE DOCUMENTO"] != "NO"
        and len(datos["NOMBRE"]) > 5
        and datos["ESTADO"] != "NO CLASIFICADO"
        and datos["IPS PRIMARIA"] != "NO"
        and datos["REGIMEN"] != "NO CLASIFICADO"
        and "VEREDA" not in datos["DEPARTAMENTO DE AFILIACION"]
    )

    ocr_compactado = (
        "IPS PRIMARIA: RETORNAR" in texto
        or "SUBSIDIADO-E.S.E." in texto
        or (datos["IPS PRIMARIA"] == "NO" and "E.S.E." in texto)
    )

    if (
        "IDENTIFICACION:" not in texto
        or not estructura_valida
        or ocr_compactado
    ):
        datos_fallback = parser_nueva_eps_fallback(texto_original)
        if datos_fallback and datos_fallback["N° DE DOCUMENTO"] != "NO":
            return datos_fallback

    return datos


def parser_adres(texto):
    datos = {"FUENTE DE CONSULTA": "ADRES"}
    texto_original = texto
    texto_norm = normalizar_texto(texto)

    bloque_base = re.search(
        r"INFORMACION BASICA DEL AFILIADO\s*:?\s*(.*?)DATOS DE AFILIACION",
        texto_norm, re.DOTALL
    )
    if bloque_base:
        base = bloque_base.group(1)
        tipo = re.search(r"TIPO DE IDENTIFICACION\s+([A-Z]+)", base)
        datos["TIPO DE DOCUMENTO"] = tipo.group(1) if tipo else "NO"
        doc = re.search(r"NUMERO DE IDENTIFICACION\s+(\d{6,24})", base)
        datos["N° DE DOCUMENTO"] = doc.group(1) if doc else "NO"
        nom = re.search(r"NOMBRES\s+(.+?)\s+APELLIDOS", base, re.DOTALL)
        datos["NOMBRES"] = nom.group(1).strip() if nom else "NO"
        ap = re.search(r"APELLIDOS\s+(.+?)\s+FECHA DE NACIMIENTO", texto_original, re.DOTALL)
        datos["APELLIDOS"] = ap.group(1).strip() if ap else "NO"
        dep = re.search(r"DEPARTAMENTO\s+([A-ZÑ\.\s]+?)\s+MUNICIPIO", base)
        datos["DEPARTAMENTO DE AFILIACION"] = dep.group(1).strip() if dep else "NO"
        mun = re.search(r"MUNICIPIO\s+([A-ZÑ\.\s]+)", base)
        datos["MUNICIPIO DE AFILIACION"] = mun.group(1).strip() if mun else "NO"

    bloque_afiliacion = re.search(
        r"DATOS DE AFILIACION\s*:?\s*(.*?)FECHA DE IMPRESION",
        texto_norm, re.DOTALL
    )
    if bloque_afiliacion:
        linea = bloque_afiliacion.group(1)

        estado = re.search(
            r"\b(ACTIVO|INACTIVO|SUSPENDIDO|PROTECCION LABORAL [A-Z])\b", linea
        )
        if estado:
            estado_raw = estado.group(1).strip()
            if "PROTECCION LABORAL" in estado_raw:
                datos["ESTADO"] = "ACTIVO"
            else:
                datos["ESTADO"] = estado_raw
        else:
            datos["ESTADO"] = "NO"

        reg = re.search(r"\b(SUBSIDIADO|CONTRIBUTIVO)\b", linea)
        datos["REGIMEN"] = reg.group(1) if reg else "NO"

        tipo_af = re.search(r"\b(BENEFICIARIO|COTIZANTE)\b", linea)
        datos["TIPO AFILIADO"] = tipo_af.group(1) if tipo_af else "NO"

        eps_legal = re.search(r'"([^"]+EPS[^"]+)"', texto_original)
        if eps_legal:
            datos["EPS AFILIACION"] = eps_legal.group(1).strip()
        else:
            eps_fallback = re.search(
                r"(ACTIVO|INACTIVO|SUSPENDIDO|PROTECCION LABORAL [A-Z])\s+"
                r"(.*?)\s+(SUBSIDIADO|CONTRIBUTIVO)", linea
            )
            datos["EPS AFILIACION"] = (
                eps_fallback.group(2).strip() if eps_fallback else "NO DETECTADA"
            )

    for k, v in datos.items():
        if isinstance(v, str):
            datos[k] = re.sub(r"\s+", " ", v).strip()

    campos_clave = ["TIPO DE DOCUMENTO", "N° DE DOCUMENTO", "NOMBRES", "APELLIDOS"]
    for campo in campos_clave:
        if campo not in datos or datos[campo] == "NO":
            datos["PARSER ALERTA"] = "REVISION_MANUAL"

    return datos


def parser_fomag(texto):
    datos = {"EPS": "FOMAG"}
    texto_original = texto
    texto = normalizar_texto(texto)

    corte = re.split(r"INFORMACION DEL COTIZANTE", texto, maxsplit=1)
    bloque = corte[0]

    nombre = re.search(r"SENOR.*?\)\s+(.+?)\s+IDENTIFICADO.*?\s+CON", bloque)
    datos["NOMBRE"] = re.sub(r"\s+", " ", nombre.group(1)).strip() if nombre else "NO"

    doc = re.search(
        r"(CEDULA CIUDADANIA|TARJETA DE IDENTIDAD|REGISTRO CIVIL DE NACIMIENTO|CEDULA EXTRANJERIA)"
        r"\s+N[°º]?\s*(\d+)", bloque
    )
    if doc:
        tipo_raw = doc.group(1)
        if "CEDULA CIUDADANIA" in tipo_raw:
            tipo = "CC"
        elif "TARJETA DE IDENTIDAD" in tipo_raw:
            tipo = "TI"
        elif "REGISTRO CIVIL DE NACIMIENTO" in tipo_raw:
            tipo = "RC"
        elif "CEDULA EXTRANJERIA" in tipo_raw:
            tipo = "CE"
        else:
            tipo = "NO"
        datos["TIPO DE DOCUMENTO"] = tipo
        datos["N° DE DOCUMENTO"] = doc.group(2)
    else:
        datos["TIPO DE DOCUMENTO"] = "NO"
        datos["N° DE DOCUMENTO"] = "NO"

    fecha = re.search(r"FECHA DE AFILIACION ES DEL\s+([0-9\-\/]+)", bloque)
    datos["FECHA AFILIACION"] = fecha.group(1) if fecha else "NO"

    mun = re.search(r"AFILIADO AL MUNICIPIO DE\s+([A-ZÑ\s]+?)\s+Y REGISTRA", bloque)
    datos["MUNICIPIO DE AFILIACION"] = mun.group(1).strip() if mun else "NO"

    estado = re.search(r"EN ESTADO\s+(ACTIVO|INACTIVO|SUSPENDIDO)", bloque)
    if estado:
        datos["ESTADO"] = clasificar_estado(estado.group(1))
    else:
        datos["ESTADO"] = "NO"

    tipo_af = re.search(r"COMO\s+(BENEFICIARIO|COTIZANTE)", bloque)
    datos["TIPO AFILIADO"] = tipo_af.group(1) if tipo_af else "NO"

    ips = re.search(r"IPS PRIMARIA\s+(.+?)\s*$", bloque)
    if ips:
        ips_limpia = ips.group(1)
        ips_limpia = re.split(r"INFORMACION|INFORMACIÓN", ips_limpia)[0]
        datos["IPS PRIMARIA"] = re.sub(r"\s+", " ", ips_limpia).strip()
    else:
        datos["IPS PRIMARIA"] = "NO"

    datos["REGIMEN"] = "REGIMEN ESPECIAL"

    return datos


# ================== DISPATCHER ==================

def extraer_datos_derechos(texto):
    eps_detectada = extraer_eps(texto)

    if eps_detectada == "ADRES":
        return parser_adres(texto)
    if eps_detectada == "EMSSANAR":
        return parser_emssanar(texto)
    if eps_detectada == "NUEVA EPS":
        return parser_nueva_eps(texto)
    if eps_detectada == "AIC":
        return parser_aic(texto)
    if eps_detectada == "MALLAMAS":
        return parser_mallamas(texto)
    if eps_detectada == "FOMAG":
        return parser_fomag(texto)

    return {
        "EPS": "NO IDENTIFICADA",
        "PARSER ALERTA": "EPS_NO_RECONOCIDA"
    }
