"""FEV layout parser — pdfplumber-based extraction of FEV PDF structure.

Copied from AUDITORA/diagnostico_fev_layout.py.
"""

import pdfplumber
from collections import defaultdict
import re
import unicodedata
import logging

logger = logging.getLogger(__name__)

COLUMNAS = {
    "item": (20, 35),
    "id": (35, 55),
    "codigo": (55, 100),
    "concepto": (110, 250),
    "profesional": (250, 320),
    "fecha": (320, 380),
    "cantidad": (380, 415),
    "cant_pen": (415, 455),
    "valor_unitario": (470, 520),
    "subtotal": (540, 600)
}

CATEGORIAS = [
    "CONSULTAS",
    "DERECHOS DE SALA",
    "ESTANCIAS",
    "HONORARIOS",
    "MATERIALES E INSUMOS",
    "MEDICAMENTOS PBS",
    "PROCEDIMIENTOS DE PROMOCIÓN Y PREVENCIÓN",
    "PROCEDIMIENTOS TERAPÉUTICOS QUIRÚRGICOS",
    "PROCEDIMIENTOS TERAPÉUTICOS NO QUIRÚRGICOS",
    "PROCEDIMIENTOS DE DIAGNÓSTICOS",
]


def detectar_categoria(texto):
    texto_norm = normalizar_texto(texto)
    for cat in CATEGORIAS:
        cat_norm = normalizar_texto(cat)
        if texto_norm.startswith(cat_norm):
            return cat
    return None


CODIGOS_ESPECIALES = {
    "890303REMIS": {
        "codigo_real": "890303REMISION",
        "concepto_real": "CONSULTA DE ODONTOLOGIA"
    },
}

PATRONES_CORTE = [
    "SUBTOTAL POR SERVICIOS PRESTADOS",
    "TOTAL VALOR A PAGAR",
    "PAGA ENTIDAD ADMINISTRADORA",
    "TOTAL DETALLES DE LA FACTURA",
    "TOTAL EN LETRAS",
    "FIRMA PACIENTE",
    "RESPONSABLE ENTIDAD",
    "VERSION:",
    "RESOLUCION DIAN"
]

TOLERANCIA_VERTICAL = 8


def es_linea_corte(linea):
    texto = normalizar_texto(linea)
    for patron in PATRONES_CORTE:
        if patron in texto:
            return True
    return False


def normalizar_texto(texto):
    if not texto:
        return ""
    texto = texto.upper().strip()
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    texto = re.sub(r"\s+", " ", texto)
    return texto


def clasificar_columna(x0):
    for nombre, (xmin, xmax) in COLUMNAS.items():
        if xmin <= x0 <= xmax:
            return nombre
    return None


def agrupar_por_fila(words, numero_pagina=1):
    filas = []
    fila_actual = []
    top_referencia = None

    for w in sorted(words, key=lambda x: (round(x["top"]), x["x0"])):
        if numero_pagina == 1 and w["top"] < 260:
            continue
        if top_referencia is None:
            top_referencia = w["top"]
        if abs(w["top"] - top_referencia) <= TOLERANCIA_VERTICAL:
            fila_actual.append(w)
        else:
            filas.append(fila_actual)
            fila_actual = [w]
            top_referencia = w["top"]

    if fila_actual:
        filas.append(fila_actual)

    return filas


def obtener_texto_completo(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            contenido = page.extract_text()
            if contenido:
                texto += contenido + "\n"
    return texto


def parsear_fev(pdf_path):
    encabezado = extraer_encabezado_fev(pdf_path)
    servicios = extraer_tabla_servicios(pdf_path)

    if not servicios:
        servicios = extraer_servicios_textuales(pdf_path)

    servicios_agrupados = agrupar_por_categoria(servicios)

    return {
        "encabezado": encabezado,
        "servicios": servicios_agrupados
    }


def extraer_encabezado_fev(pdf_path):
    datos = {}

    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        encabezado_crop = page.crop((0, 0, page.width, 270))
        texto = encabezado_crop.extract_text()

    if not texto:
        return datos

    def buscar(patron):
        m = re.search(patron, texto)
        return m.group(1).strip() if m else ""

    match = re.search(r"Responsable NIT:\s*(.*?)\s*Régimen:", texto)
    responsable = match.group(1).strip() if match else ""

    match_pago = re.search(r"Pago Factura:\s*(.*?)\s*Código:", texto)
    pago_factura = match_pago.group(1).strip() if match_pago else ""

    if pago_factura:
        responsable = responsable + " " + pago_factura

    responsable = re.sub(r"\s+", " ", responsable)
    datos["RESPONSABLE"] = responsable
    datos["REGIMEN"] = buscar(r"Régimen\s*:\s*(.+)")

    match = re.search(r"N[º°o\.]*\s*Factura:\s*(\S+)", texto)
    if match:
        datos["NUMERO FACTURA"] = match.group(1).strip()

    datos["TIPO FACTURA"] = buscar(r"Tipo Factura\s*:\s*(.+?)\s+Estado:")
    datos["SERVICIO"] = buscar(r"Servicio\s*:\s*(.+)")
    datos["ESTADO"] = buscar(r"Estado\s*:\s*(\S+)")

    match = re.search(
        r"Paciente:\s*([A-Z]{1,3})\s*:\s*(\d+)\s*-\s*(.*?)\n",
        texto
    )
    if match:
        tipo_doc = match.group(1).strip()
        numero_doc = match.group(2).strip()
        nombre = match.group(3).strip()
        datos["TIPO DE DOCUMENTO"] = tipo_doc
        datos["NUMERO DE DOCUMENTO"] = numero_doc
        datos["NOMBRE COMPLETO"] = nombre

    datos["FECHA INGRESO"] = buscar(r"Fec\. Ingreso\s*:\s*([\d/:\s]+)")
    datos["FECHA EGRESO"] = buscar(r"Fec\. Egreso\s*:\s*([\d/:\s]+)")
    datos["ESTANCIA"] = buscar(r"Estancia\s*:\s*(.+?)\s+Edad:")
    datos["EDAD"] = buscar(r"Edad\s*:\s*(.+?)\s+Estrato:")
    datos["FECHA NACIMIENTO"] = buscar(r"Fec\. Nacimie.*?:\s*([\d/]+)")
    datos["SEXO"] = buscar(r"Sexo\s*:\s*(\S+)")

    match_tipo = re.search(
        r"Tipo Paciente\s*:\s*(.+?)(?:A[r]?juste\s*Monetario:)",
        texto, re.IGNORECASE | re.DOTALL
    )
    if match_tipo:
        tipo_paciente = match_tipo.group(1).strip()
        tipo_paciente = re.sub(
            r"(A[r]?juste\s*Monetario.*)$", "", tipo_paciente, flags=re.IGNORECASE
        ).strip()
        tipo_paciente = re.sub(r"\s+", " ", tipo_paciente)

        tipo_norm = normalizar_texto(tipo_paciente)
        if (
            "SUBSIDIADO - OTRO MIEMBRO DEL" in tipo_norm
            or "NUCLEO FAM" in tipo_norm
            or "FAMAILI" in tipo_norm
        ):
            tipo_paciente = "Subsidiado - Otro miembro del núcleo familiar"

        datos["TIPO PACIENTE"] = tipo_paciente
    else:
        texto_norm = normalizar_texto(texto)
        if (
            "TIPO PACIENTE: SUBSIDIADO - OTRO MIEMBRO DEL" in texto_norm
            or "NUCLEO FAM" in texto_norm
            or "FAMAILI" in texto_norm
        ):
            datos["TIPO PACIENTE"] = "Subsidiado - Otro miembro del núcleo familiar"
        else:
            datos["TIPO PACIENTE"] = ""

    datos["CONTRATO"] = buscar(r"#Contrato\s*:\s*(.+?)\s+Nº Laboratorio:")

    match_cufe = re.search(r"CUFE\s*:\s*([A-Z0-9a-z\-]{20,})", texto)
    datos["CUFE"] = match_cufe.group(1).strip() if match_cufe else ""

    return datos


def limpiar_concepto(texto):
    if not texto:
        return texto
    texto = texto.strip().upper()
    basura = [
        "FACTURA", "ELECTRONICA", "VENTA", "SERVICIO", "SALUD",
        "PAGINA",
    ]
    palabras = texto.split()
    while palabras and palabras[-1] in basura:
        palabras.pop()
    return " ".join(palabras)


def es_continuacion_valida(texto):
    if not texto:
        return False
    texto_norm = normalizar_texto(texto)
    if len(texto_norm) < 3:
        return False

    bloqueos = [
        "WWW.", "NIT:", "PAGINA", "FACTURA", "IMPRIME:", "RESPONSABLE",
        "PACIENTE", "FIRMA", "RESOLUCION", "HIGEA", "SOFTWARE",
        "TOTAL", "SUBTOTAL", "COPAGO", "CUOTA", "PAGA ENTIDAD", "DIAN",
        "FECHA ENVIO", "NUMERO RADICADO", "VERSION:", "DESCRIPCION GENERAL",
    ]
    for b in bloqueos:
        if b in texto_norm:
            return False
    if re.match(r"^\d+\s+\d+", texto_norm):
        return False
    for cat in CATEGORIAS:
        if normalizar_texto(cat) in texto_norm:
            return False
    if len(re.findall(r"\d", texto_norm)) > 15:
        return False
    if len(texto_norm) > 120:
        return False
    return True


def detectar_codigo_especial(texto):
    texto_norm = normalizar_texto(texto)
    for codigo_parcial, datos in CODIGOS_ESPECIALES.items():
        codigo_parcial_norm = normalizar_texto(codigo_parcial)
        if codigo_parcial_norm in texto_norm:
            return {"codigo": datos["codigo_real"], "concepto": datos["concepto_real"]}
    return None


def parsear_fila_textual(texto, categoria_actual=None):
    patron = re.compile(
        r"""
        ^\s*
        (\d+)                           # item
        \s+
        (\d+)                           # id
        \s+
        ([A-Z0-9]{4,15})                # codigo FLEXIBLE
        \s*
        (.*?)                           # concepto
        \s+
        ([A-Za-zÁÉÍÓÚáéíóúÑñ]+\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+)
        \s+
        (\d{2}/\d{2}/\d{4})
        \s+
        ([\d.,]+)
        \s+
        ([\d.,]+)
        \s+
        ([\d.,]+)
        \s+
        ([\d.,]+)
        """,
        re.VERBOSE
    )

    match = patron.search(texto)
    if not match:
        return None

    item = match.group(1).strip()
    id_servicio = match.group(2).strip()
    codigo_extraido = match.group(3).strip()
    concepto_extraido = limpiar_concepto(match.group(4))
    profesional = match.group(5).strip()
    fecha = match.group(6).strip()
    cantidad = match.group(7).strip()
    valor_unitario = match.group(9).strip()
    subtotal = match.group(10).strip()

    codigo_especial = detectar_codigo_especial(codigo_extraido + concepto_extraido)
    if codigo_especial:
        codigo_final = codigo_especial["codigo"]
        concepto_final = codigo_especial["concepto"]
    else:
        codigo_final = codigo_extraido
        concepto_final = concepto_extraido

    categoria_final = detectar_categoria(texto) or categoria_actual

    return {
        "item": item,
        "id": id_servicio,
        "codigo": codigo_final,
        "concepto": concepto_final,
        "profesional": profesional,
        "fecha": fecha,
        "cantidad": cantidad,
        "valor_unitario": valor_unitario,
        "subtotal": subtotal,
        "categoria": categoria_final
    }


def extraer_tabla_servicios(pdf_path):
    servicios = []
    corte_global = False
    ultimo_servicio = None
    categoria_actual = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if corte_global:
                break

            words = page.extract_words()
            filas = agrupar_por_fila(words, numero_pagina=page.page_number)

            for fila in filas:
                texto_fila = " ".join([w["text"] for w in fila])

                es_corte_real = (
                    "Subtotal por Servicios Prestados" in texto_fila
                    or "Total Valor a Pagar" in texto_fila
                )
                if es_corte_real:
                    corte_global = True
                    break

                categoria_detectada = detectar_categoria(texto_fila)
                if categoria_detectada:
                    categoria_actual = categoria_detectada
                    texto_sin_categoria = normalizar_texto(texto_fila)
                    if texto_sin_categoria == normalizar_texto(categoria_detectada):
                        continue

                fila_dict = defaultdict(str)
                for palabra in fila:
                    columna = clasificar_columna(palabra["x0"])
                    if columna:
                        fila_dict[columna] += palabra["text"] + " "

                fecha_valida = "/" in fila_dict["fecha"]
                subtotal_valido = bool(
                    re.search(r"\d{1,3}(?:\.\d{3})*,\d{2}", fila_dict["subtotal"])
                )
                item_valido = bool(re.fullmatch(r"\d{1,3}", fila_dict["item"].strip()))
                id_valido = bool(re.fullmatch(r"\d{2,6}", fila_dict["id"].strip()))
                codigo_valido = bool(
                    re.fullmatch(r"[A-Z0-9]{4,15}", fila_dict["codigo"].strip())
                )

                columnas_corruptas = (
                    fila_dict["item"].strip() == fila_dict["id"].strip()
                    or fila_dict["codigo"].strip() == ""
                )

                fila_valida = (
                    fecha_valida and subtotal_valido and item_valido
                    and id_valido and codigo_valido and not columnas_corruptas
                )

                if fila_valida:
                    servicio = {
                        "item": fila_dict["item"].strip(),
                        "id": fila_dict["id"].strip(),
                        "codigo": fila_dict["codigo"].strip(),
                        "concepto": limpiar_concepto(fila_dict["concepto"]),
                        "profesional": fila_dict["profesional"].strip(),
                        "fecha": fila_dict["fecha"].strip(),
                        "cantidad": fila_dict["cantidad"].strip(),
                        "valor_unitario": fila_dict["valor_unitario"].strip(),
                        "subtotal": fila_dict["subtotal"].strip(),
                        "categoria": categoria_actual
                    }
                    servicios.append(servicio)
                    ultimo_servicio = servicio
                else:
                    texto_completo_fila = " ".join(w["text"] for w in fila)
                    servicio_fallback = parsear_fila_textual(
                        texto_completo_fila, categoria_actual
                    )
                    if servicio_fallback:
                        servicios.append(servicio_fallback)
                        ultimo_servicio = servicio_fallback
                    else:
                        texto_fila = texto_fila.strip()
                        nuevo_texto = fila_dict["concepto"].strip()
                        if (
                            ultimo_servicio
                            and es_continuacion_valida(nuevo_texto)
                        ):
                            nuevo_texto = limpiar_concepto(fila_dict["concepto"])
                            if nuevo_texto:
                                ultimo_servicio["concepto"] += " " + nuevo_texto

    return servicios


def extraer_servicios_textuales(pdf_path):
    texto = obtener_texto_completo(pdf_path)
    servicios = []
    categoria_actual = None
    tabla_iniciada = False
    lineas = texto.splitlines()

    patron_servicio = re.compile(
        r"""
        ^
        (\d+)\s+                       # item
        (\d+)\s+                       # id
        ([A-Z0-9\-]+)\s+               # codigo
        (.*?)\s+                       # concepto
        ([A-Za-zÁÉÍÓÚáéíóúÑñ]+\s+[A-Za-zÁÉÍÓÚáéíóúÑñ]+)\s+
        (\d{2}/\d{2}/\d{4})\s+
        ([\d.,]+)\s+
        ([\d.,]+)\s+
        ([\d.,]+)\s+
        ([\d.,]+)
        $
        """,
        re.VERBOSE
    )

    ultimo_servicio = None

    for linea in lineas:
        linea_norm = normalizar_texto(linea)

        if "# ID" in linea_norm and "CODIGO" in linea_norm and "CONCEPTO" in linea_norm:
            tabla_iniciada = True
            continue

        if not tabla_iniciada:
            continue

        linea_limpia = normalizar_texto(linea)
        for cat in CATEGORIAS:
            cat_norm = normalizar_texto(cat)
            if linea_limpia.startswith(cat_norm):
                categoria_actual = cat
                break

        if es_linea_corte(linea):
            ultimo_servicio = None
            continue

        servicio = parsear_fila_textual(linea, categoria_actual)
        if servicio:
            servicios.append(servicio)
            ultimo_servicio = servicio
        else:
            texto_footer = normalizar_texto(linea)
            es_footer = (
                "WWW." in texto_footer or "NIT:" in texto_footer
                or "SOFTWARE" in texto_footer or "FACTURA" in texto_footer
                or "PAGINA" in texto_footer
            )
            if (
                ultimo_servicio
                and es_continuacion_valida(linea)
                and not es_footer
            ):
                ultimo_servicio["concepto"] += " " + limpiar_concepto(linea)

    return servicios


def agrupar_por_categoria(servicios):
    agrupado = defaultdict(list)
    for s in servicios:
        categoria = s.get("categoria") or "SIN CATEGORIA"
        agrupado[categoria].append(s)
    return dict(agrupado)
