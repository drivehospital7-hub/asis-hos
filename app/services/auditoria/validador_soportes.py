"""Support document validation against FEV services and rules JSON.

Copied from AUDITORA/validador_soportes.py with changes:
- File path resolution via Path(__file__).parent (not CWD)
- assert replaced with conditionals + logging
- Uses logging instead of printing
"""

import json
import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve reglas_soportes.json via __file__ to avoid CWD dependency
_reglas_path = Path(__file__).parent / "reglas_soportes.json"
with open(_reglas_path, "r", encoding="utf-8") as f:
    REGLAS = json.load(f)
    REGLAS_PLANAS = {}
    for area, reglas_area in REGLAS.items():
        for codigo, regla in reglas_area.items():
            REGLAS_PLANAS[codigo] = regla


def limpiar_texto(texto):
    texto = texto.upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def comparar_conceptos(concepto_fev, concepto_regla):
    if not concepto_fev or not concepto_regla:
        return False
    fev = limpiar_texto(concepto_fev)
    regla = limpiar_texto(concepto_regla)

    if regla in fev or fev in regla:
        return True

    palabras_fev = set(fev.split())
    palabras_regla = set(regla.split())
    if not palabras_regla:
        return False
    interseccion = palabras_fev.intersection(palabras_regla)
    porcentaje = len(interseccion) / len(palabras_regla)
    return porcentaje >= 0.6


def resolver_variables(texto, fev, item):
    encabezado = fev.get("data", {}).get("encabezado", {})
    variables = {
        "{NUMERO_DOCUMENTO}": encabezado.get("NUMERO DE DOCUMENTO", ""),
        "{NOMBRE_PACIENTE}": encabezado.get("NOMBRE COMPLETO", ""),
        "{NUMERO_FACTURA}": encabezado.get("NUMERO FACTURA", ""),
        "{CUFE}": encabezado.get("CUFE", ""),
        "{EPS}": encabezado.get("RESPONSABLE", ""),
        "{CODIGO_SERVICIO}": item.get("codigo", ""),
        "{CONCEPTO_FEV}": item.get("concepto", "")
    }
    for var, valor in variables.items():
        texto = texto.replace(var, str(valor))
    return texto


def validar_soportes(archivos):
    resultados = []
    codigos_sin_regla = set()

    soportes = [
        {
            "archivo": a["archivo"].upper(),
            "texto": limpiar_texto(a.get("texto", ""))
        }
        for a in archivos
        if a["tipo"] == "SOPORTE"
    ]

    fev = next((a for a in archivos if a["tipo"] == "FEV"), None)
    if not fev:
        return []

    servicios = fev["data"].get("servicios", {})

    for categoria, items in servicios.items():
        if categoria in ["MEDICAMENTOS PBS", "MATERIALES E INSUMOS"]:
            continue

        for item in items:
            codigo = item.get("codigo", "").strip()
            regla = REGLAS_PLANAS.get(codigo)

            if not regla:
                codigos_sin_regla.add(codigo)
                continue

            if regla.get("revision_manual"):
                resultados.append({
                    "codigo": codigo,
                    "concepto_regla": regla.get("concepto"),
                    "concepto_fev": item.get("concepto"),
                    "estado": "REVISION MANUAL",
                    "motivo": regla.get("motivo_revision_manual", "Requiere validacion manual")
                })
                continue

            if "palabras_obligatorias" not in regla and "palabras_opcionales" not in regla:
                regla["palabras_obligatorias"] = regla.get("palabras_clave", [])
                regla["palabras_opcionales"] = []

            concepto_regla = regla.get("concepto")
            concepto_fev = item.get("concepto")
            validacion_concepto = comparar_conceptos(concepto_fev, concepto_regla)

            tipos_soporte = [
                t.upper() for t in regla.get("tipos_soporte", [])
            ]

            if not tipos_soporte:
                resultados.append({
                    "codigo": codigo,
                    "concepto_regla": concepto_regla,
                    "concepto_fev": concepto_fev,
                    "estado": "REGLA SIN TIPO DE SOPORTE"
                })
                continue

            palabras_obligatorias = []
            palabras_opcionales = []

            for palabra in regla.get("palabras_obligatorias", []):
                palabra_resuelta = resolver_variables(palabra, fev, item)
                palabras_obligatorias.append(limpiar_texto(palabra_resuelta))

            for palabra in regla.get("palabras_opcionales", []):
                palabra_resuelta = resolver_variables(palabra, fev, item)
                palabras_opcionales.append(limpiar_texto(palabra_resuelta))

            min_coincidencias = regla.get("min_coincidencias", 1)

            servicio = limpiar_texto(
                fev.get("data", {}).get("encabezado", {}).get("SERVICIO", "")
            )
            numero_factura = str(
                fev.get("data", {}).get("encabezado", {}).get("NUMERO FACTURA", "")
            ).upper()

            es_pyp = "PYP" in servicio
            es_factura_evento = numero_factura.startswith("FEV")

            if es_pyp and es_factura_evento:
                palabras_pyp = []
                for palabra in regla.get("palabras_obligatorias_caso_servicio_pyp", []):
                    palabra_resuelta = resolver_variables(palabra, fev, item)
                    palabras_pyp.append(limpiar_texto(palabra_resuelta))
                palabras_obligatorias.extend(palabras_pyp)
                min_coincidencias += len(palabras_pyp)

            textos_unificados = []
            archivos_unificados = []

            for soporte in soportes:
                nombre_archivo = soporte["archivo"]
                if not any(nombre_archivo.startswith(t) for t in tipos_soporte):
                    continue
                textos_unificados.append(soporte["texto"])
                archivos_unificados.append(nombre_archivo)

            texto_unificado = "\n\n===== NUEVO SOPORTE =====\n\n".join(textos_unificados)

            encontrado = False
            archivo_ok = None
            mejor_coincidencia = []
            mejor_faltante = []

            if not textos_unificados:
                resultados.append({
                    "codigo": codigo,
                    "concepto_regla": concepto_regla,
                    "concepto_fev": concepto_fev,
                    "validacion_concepto": validacion_concepto,
                    "coincidencias_encontradas": [],
                    "faltantes": palabras_obligatorias + palabras_opcionales,
                    "estado": "NO SE ENCONTRARON SOPORTES"
                })
                continue

            texto = texto_unificado

            obligatorias_encontradas = [
                p for p in palabras_obligatorias if p in texto
            ]
            obligatorias_faltantes = [
                p for p in palabras_obligatorias if p not in texto
            ]
            opcionales_encontradas = [
                p for p in palabras_opcionales if p in texto
            ]
            opcionales_faltantes = [
                p for p in palabras_opcionales if p not in texto
            ]

            coincidencias = obligatorias_encontradas + opcionales_encontradas
            faltantes = obligatorias_faltantes + opcionales_faltantes

            mejor_coincidencia = coincidencias.copy()
            mejor_faltante = faltantes.copy()

            cumple_obligatorias = len(obligatorias_faltantes) == 0
            cumple_minimo = len(coincidencias) >= min_coincidencias

            if cumple_obligatorias and cumple_minimo:
                encontrado = True
                archivo_ok = archivos_unificados

            if not encontrado:
                resultados.append({
                    "codigo": codigo,
                    "concepto_regla": concepto_regla,
                    "concepto_fev": concepto_fev,
                    "validacion_concepto": validacion_concepto,
                    "coincidencias_encontradas": mejor_coincidencia,
                    "faltantes": mejor_faltante,
                    "estado": "SOPORTE FALTANTE"
                })
            elif not validacion_concepto:
                resultados.append({
                    "codigo": codigo,
                    "concepto_regla": concepto_regla,
                    "concepto_fev": concepto_fev,
                    "soporte": archivo_ok,
                    "estado": "REVISION CONCEPTO"
                })

    return {
        "validacion_soportes": resultados,
        "codigos_sin_regla": list(codigos_sin_regla)
    }
