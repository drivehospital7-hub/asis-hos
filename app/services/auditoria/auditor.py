"""Auditoría de PDFs — orquestador principal.

Adapted from AUDITORA/procesador_pdfs.pyw with changes:
- No Tkinter dialog: auditar_carpeta(ruta: str) takes path parameter
- Uses logging instead of printing
- try/except per PDF so one bad file doesn't kill the batch
- Returns dict instead of saving to JSON
"""

import logging
import os

logger = logging.getLogger(__name__)

from app.services.auditoria.extractor import extraer_texto_pdf
from app.services.auditoria.pde_parser import (
    extraer_bloque_derechos,
    extraer_datos_derechos,
)
from app.services.auditoria.fev_parser import parsear_fev
from app.services.auditoria.normalizador import (
    normalizar_fev_emssanar,
    normalizar_pde_emssanar,
    normalizar_pde_adres,
    comparar_campos,
)


def validar_fev_vs_pde(lista_archivos):
    """Compare FEV data against PDE data for a single patient folder."""
    fev = None
    lista_pde = []

    for item in lista_archivos:
        if item["tipo"] == "FEV" and fev is None:
            fev = item
        elif item["tipo"] == "PDE":
            lista_pde.append(item)

    if not fev or not lista_pde:
        return None

    pde = None
    for item in lista_pde:
        data = item.get("data")
        if data is None:
            continue  # PDE con error de extracción, saltar
        eps = data.get("EPS", "").strip().upper()
        if eps and eps != "NO IDENTIFICADA":
            pde = item
            break

    if pde is None:
        # Usar el último PDE que sí tenga data, o el último a secas
        for item in reversed(lista_pde):
            if item.get("data") is not None:
                pde = item
                break
        if pde is None:
            pde = lista_pde[-1]

    fev_data = fev.get("data")
    pde_data = pde.get("data")

    if fev_data is None or pde_data is None:
        logger.warning("FEV o PDE sin data (error de extracción), no se puede validar")
        return {
            "fev_normalizado": None,
            "pde_normalizado": None,
            "diferencias": {
                "ERROR EXTRACCION": {
                    "mensaje": "No se pudo extraer datos del FEV o PDE para comparar"
                }
            }
        }

    fev_norm = normalizar_fev_emssanar(fev_data)

    if "EPS" in pde_data:
        pde_norm = normalizar_pde_emssanar(pde_data)
    elif "FUENTE DE CONSULTA" in pde_data:
        pde_norm = normalizar_pde_adres(pde_data)
    else:
        logger.warning("Tipo PDE no reconocido: %s", pde_data)
        return None

    diferencias = comparar_campos(fev_norm, pde_norm)

    return {
        "fev_normalizado": fev_norm,
        "pde_normalizado": pde_norm,
        "diferencias": diferencias
    }


def procesar_archivo(ruta_pdf):
    """Process a single PDF file and classify it as FEV, PDE, or SOPORTE."""
    nombre = os.path.basename(ruta_pdf).upper()

    if nombre.startswith("FEV"):
        logger.info("Procesando FEV: %s", nombre)
        try:
            resultado = parsear_fev(ruta_pdf)
        except Exception as e:
            logger.exception("Error parseando FEV %s: %s", nombre, e)
            return {
                "tipo": "FEV",
                "archivo": nombre,
                "error": f"Error parseando FEV: {e}",
                "data": None,
            }
        return {
            "tipo": "FEV",
            "archivo": nombre,
            "data": resultado,
        }

    elif nombre.startswith("PDE"):
        logger.info("Procesando PDE: %s", nombre)
        try:
            texto = extraer_texto_pdf(ruta_pdf, "PDE")
            if not texto:
                logger.warning("PDE %s: no se pudo extraer texto (OCR intentado, página sin texto legible)", nombre)
                return {
                    "tipo": "PDE",
                    "archivo": nombre,
                    "error": "No se pudo extraer texto del PDF. Puede ser un PDF escaneado ilegible o estar corrupto.",
                    "data": None,
                }
            bloque = extraer_bloque_derechos(texto)
            if not bloque:
                logger.warning("No se encontró bloque en %s, usando texto completo", nombre)
                bloque = texto
            datos = extraer_datos_derechos(bloque)
        except Exception as e:
            logger.exception("Error parseando PDE %s: %s", nombre, e)
            return {
                "tipo": "PDE",
                "archivo": nombre,
                "error": f"Error parseando PDE: {e}",
                "data": None,
            }
        return {
            "tipo": "PDE",
            "archivo": nombre,
            "data": datos,
        }

    elif nombre.startswith(("EPI", "HAU", "HAO", "HEV", "OPF", "HAM", "PDX")):
        logger.info("Procesando SOPORTE: %s", nombre)
        try:
            texto = extraer_texto_pdf(ruta_pdf, "SOPORTE")
            if not texto:
                logger.warning("SOPORTE %s: no se pudo extraer texto (OCR intentado, página sin texto legible)", nombre)
                return {
                    "tipo": "SOPORTE",
                    "archivo": nombre,
                    "error": "No se pudo extraer texto del PDF. Puede ser un PDF escaneado ilegible o estar corrupto.",
                    "texto": "",
                }
        except Exception as e:
            logger.exception("Error extrayendo texto de soporte %s: %s", nombre, e)
            return {
                "tipo": "SOPORTE",
                "archivo": nombre,
                "error": f"Error extrayendo texto: {e}",
                "texto": "",
            }
        return {
            "tipo": "SOPORTE",
            "archivo": nombre,
            "texto": texto,
        }

    else:
        logger.debug("Archivo ignorado: %s", nombre)
        return None


def auditar_carpeta(ruta):
    """Audit all PDF files in a folder tree.

    Args:
        ruta: Path to the root folder to scan.

    Returns:
        dict with nested structure per patient folder, including
        validations, alerts, and error handling.
    """
    if not os.path.isdir(ruta):
        logger.error("Ruta no existe o no es una carpeta: %s", ruta)
        return {"error": f"La ruta no existe o no es una carpeta: {ruta}"}

    resultados = {}
    nombres_globales = {}
    metadatos = {
        "total_pdfs_encontrados": 0,
        "total_clasificados": 0,
        "total_ignorados": 0,
        "total_errores": 0,
        "archivos_ignorados": [],  # archivos que no coincidieron con ningún patrón
        "archivos_con_error": [],  # archivos que se clasificaron pero fallaron
    }

    logger.info("Iniciando auditoría en: %s", ruta)
    logger.info("=== ARCHIVOS ENCONTRADOS ===")

    for root, dirs, files in os.walk(ruta):
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        if not pdfs:
            continue

        ruta_relativa = os.path.relpath(root, ruta)
        if ruta_relativa == ".":
            partes = [os.path.basename(ruta)]
        else:
            partes = ruta_relativa.split(os.sep)

        carpeta_final = partes[-1]

        if carpeta_final not in nombres_globales:
            nombres_globales[carpeta_final] = []

        ubicacion = " / ".join(partes[:-1]) if len(partes) > 1 else partes[0]
        if ubicacion not in nombres_globales[carpeta_final]:
            nombres_globales[carpeta_final].append(ubicacion)

        nodo = resultados
        for parte in partes[:-1]:
            if parte not in nodo:
                nodo[parte] = {}
            nodo = nodo[parte]

        tiene_subcarpetas = len(dirs) > 0

        if carpeta_final not in nodo:
            if tiene_subcarpetas:
                nodo[carpeta_final] = {}
            else:
                nodo[carpeta_final] = {"archivos": []}

        for file in pdfs:
            metadatos["total_pdfs_encontrados"] += 1
            ruta_pdf = os.path.join(root, file)

            logger.info("  [%s] %s", carpeta_final, file)

            # try/except per PDF so one bad file doesn't kill the batch
            try:
                resultado = procesar_archivo(ruta_pdf)
            except Exception as e:
                logger.exception("Error inesperado procesando %s: %s", ruta_pdf, e)
                resultado = {
                    "tipo": "DESCONOCIDO",
                    "archivo": file.upper(),
                    "error": str(e),
                }

            if resultado is None:
                # Archivo que no coincide con ningún patrón
                metadatos["total_ignorados"] += 1
                PATRONES_VALIDOS = "FEV, PDE, EPI, HAU, HAO, HEV, OPF, HAM, PDX"
                metadatos["archivos_ignorados"].append({
                    "archivo": file,
                    "carpeta": carpeta_final,
                    "motivo": f"No coincide con patrones: {PATRONES_VALIDOS}",
                })
            elif resultado.get("error"):
                metadatos["total_errores"] += 1
                metadatos["archivos_con_error"].append({
                    "archivo": file,
                    "carpeta": carpeta_final,
                    "error": resultado["error"],
                })
                if "archivos" in nodo[carpeta_final]:
                    nodo[carpeta_final]["archivos"].append(resultado)
            elif "archivos" in nodo[carpeta_final]:
                metadatos["total_clasificados"] += 1
                nodo[carpeta_final]["archivos"].append(resultado)
            elif "archivos" not in nodo.get(carpeta_final, {}):
                logger.warning("Nodo sin archivos para %s, saltando resultado", carpeta_final)

    # Post-process: validations
    def recorrer_validaciones(diccionario):
        for clave, valor in diccionario.items():
            if isinstance(valor, dict):
                if "archivos" in valor:
                    archivos = valor["archivos"]
                    tipos = [a["tipo"] for a in archivos]

                    tiene_fev = "FEV" in tipos
                    tiene_pde = "PDE" in tipos

                    if tiene_fev:
                        alerta = None
                        if not tiene_pde:
                            alerta = {
                                "mensaje": "NO EXISTE PDF PDE O ESTÁ MAL NOMBRADO"
                            }

                        try:
                            valor["validacion"] = validar_fev_vs_pde(archivos)
                        except Exception as e:
                            logger.exception("Error validando FEV vs PDE para %s: %s", clave, e)
                            valor["validacion"] = None

                        try:
                            from app.services.auditoria.validador_soportes import validar_soportes
                            servicios_fev = None
                            for a in archivos:
                                if a["tipo"] == "FEV":
                                    servicios_fev = a["data"].get("servicios", {}) if a.get("data") else None
                                    break
                            if servicios_fev:
                                valor["validacion_soportes"] = validar_soportes(valor["archivos"])
                        except Exception as e:
                            logger.exception("Error validando soportes para %s: %s", clave, e)
                            valor["validacion_soportes"] = None

                        if alerta:
                            valor["alerta_archivos"] = alerta

                    elif tiene_pde:
                        valor["alerta_archivos"] = {
                            "mensaje": "PDE HUÉRFANO FALTA PDF FEV O MAL NOMBRADO"
                        }
                        valor["validacion"] = None

                    if len(nombres_globales.get(clave, [])) > 1:
                        valor["duplicado_global"] = {
                            "mensaje": "MISMA CARPETA EXISTENTE EN DIFERENTES UBICACIONES",
                            "ubicaciones": nombres_globales[clave],
                        }
                else:
                    recorrer_validaciones(valor)

    recorrer_validaciones(resultados)

    logger.info(
        "Auditoría completada: %d PDFs encontrados, %d clasificados, %d ignorados, %d errores",
        metadatos["total_pdfs_encontrados"],
        metadatos["total_clasificados"],
        metadatos["total_ignorados"],
        metadatos["total_errores"],
    )
    if metadatos["archivos_ignorados"]:
        logger.info("Archivos ignorados (%d):", len(metadatos["archivos_ignorados"]))
        for a in metadatos["archivos_ignorados"]:
            logger.info("  - %s", a["archivo"])

    return {
        "expedientes": resultados,
        "_metadata": metadatos,
    }
