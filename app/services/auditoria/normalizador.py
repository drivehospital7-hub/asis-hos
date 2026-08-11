"""FEV↔PDE normalization and comparison utilities.

Copied from AUDITORA/normalizador.py.
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)


def normalizar_nombre_adres(nombres, apellidos):
    nombre_completo = f"{nombres} {apellidos}"
    return normalizar_nombre(nombre_completo)


def limpiar_eps_desde_responsable(responsable):
    responsable = responsable.upper()
    if "EMSSANAR" in responsable:
        return "EMSSANAR"
    if "900156264-2" in responsable:
        return "NUEVA EPS"
    if "MALLAMAS" in responsable:
        return "MALLAMAS"
    if "CAPITAL SALUD" in responsable:
        return "CAPITAL SALUD"
    if "ASMET SALUD" in responsable:
        return "ASMET SALUD"
    if "900226715-3" in responsable:
        return "COOSALUD EPS"
    if "800251440-6" in responsable:
        return "SANITAS EPS"
    if "817001773-3" in responsable:
        return "AIC EPS"
    if "800130907-4" in responsable:
        return "SALUD TOTAL EPS"
    if "800088702-2" in responsable:
        return "EPS SURAMERICANA"
    if "900604350-0" in responsable:
        return "SAVIA SALUD EPS"
    if "860066942-7" in responsable:
        return "COMPENSAR EPS"
    if "830053105-3" in responsable:
        return "FOMAG"
    return responsable.strip()


def limpiar_eps_adres(eps):
    eps = eps.upper()
    if "CAPITAL SALUD" in eps:
        return "CAPITAL SALUD"
    if "ASMET SALUD" in eps:
        return "ASMET SALUD"
    if "COOSALUD" in eps:
        return "COOSALUD EPS"
    if "SANITAS" in eps:
        return "SANITAS EPS"
    if "SALUD TOTAL" in eps:
        return "SALUD TOTAL EPS"
    if "EPS SURAMERICANA" in eps:
        return "EPS SURAMERICANA"
    if "SAVIA SALUD" in eps:
        return "SAVIA SALUD EPS"
    if "COMPENSAR" in eps:
        return "COMPENSAR EPS"
    return eps.strip()


def limpiar_tipo_afiliado(texto):
    t = texto.upper()
    if "COTIZANTE" in t:
        return "COTIZANTE"
    if "BENEFICIARIO" in t:
        return "BENEFICIARIO"
    return t.strip()


def normalizar_pde_adres(data):
    return {
        "eps": limpiar_eps_adres(data.get("EPS AFILIACION", "")),
        "tipo_documento": data.get("TIPO DE DOCUMENTO", "").upper(),
        "numero_documento": data.get("N° DE DOCUMENTO", ""),
        "nombre": normalizar_nombre_adres(
            data.get("NOMBRES", ""),
            data.get("APELLIDOS", "")
        ),
        "regimen": homologar_regimen(data.get("REGIMEN", "")),
        "tipo_afiliado": limpiar_tipo_afiliado(data.get("TIPO AFILIADO", "")),
        "estado": data.get("ESTADO", "").upper(),
        "origen": "PDE"
    }


def limpiar_texto(t):
    t = t.upper()
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def normalizar_nombre(nombre):
    nombre = limpiar_texto(nombre)
    palabras = nombre.split()
    palabras.sort()
    return " ".join(palabras)


def homologar_regimen(regimen):
    r = regimen.upper().strip()
    if "CONTRIBUTIVO" in r:
        return "CONTRIBUTIVO"
    if "SUBSIDIADO" in r:
        return "SUBSIDIADO"
    if (
        "OTRA/EXCEPCION" in r or "OTRA/EXCEPCIÓN" in r
        or "EXCEPCION" in r or "EXCEPCIÓN" in r
        or "REGIMEN ESPECIAL" in r or "ESPECIAL" in r
    ):
        return "REGIMEN ESPECIAL"
    if r in ["NO DETECTADO", "NO CLASIFICADO", ""]:
        return "NO IDENTIFICADO"
    return r


def normalizar_fev_emssanar(data):
    enc = data["encabezado"]
    return {
        "eps": limpiar_eps_desde_responsable(enc.get("RESPONSABLE", "")),
        "tipo_documento": enc.get("TIPO DE DOCUMENTO", "").upper(),
        "numero_documento": enc.get("NUMERO DE DOCUMENTO", ""),
        "nombre": normalizar_nombre(enc.get("NOMBRE COMPLETO", "")).upper(),
        "regimen": homologar_regimen(enc.get("REGIMEN", "")),
        "tipo_paciente": enc.get("TIPO PACIENTE", "").upper(),
        "estado": enc.get("ESTADO", "").upper(),
        "numero_factura": enc.get("NUMERO FACTURA", "").upper().strip(),
        "cufe": enc.get("CUFE", "").strip(),
        "origen": "FEV"
    }


def normalizar_pde_emssanar(data):
    regimen_original = data.get("REGIMEN", "").upper()
    tipo_afiliado = data.get("TIPO DE AFILIADO", "").upper().strip()

    if tipo_afiliado == "":
        if "COTIZANTE" in regimen_original:
            tipo_afiliado = "COTIZANTE"
        elif "BENEFICIARIO" in regimen_original:
            tipo_afiliado = "BENEFICIARIO"

    return {
        "eps": data.get("EPS", "").upper(),
        "tipo_documento": data.get("TIPO DE DOCUMENTO", "").upper(),
        "numero_documento": data.get("N° DE DOCUMENTO", ""),
        "nombre": normalizar_nombre(data.get("NOMBRE", "")),
        "regimen": homologar_regimen(regimen_original),
        "tipo_afiliado": tipo_afiliado,
        "estado": data.get("ESTADO", "").upper(),
        "departamento_afiliacion": data.get("DEPARTAMENTO DE AFILIACION", ""),
        "municipio_afiliacion": data.get("MUNICIPIO DE AFILIACION", ""),
        "departamento_portabilidad": data.get("DEPARTAMENTO DE PORTABILIDAD", ""),
        "municipio_portabilidad": data.get("MUNICIPIO DE PORTABILIDAD", ""),
        "origen": "PDE"
    }


def normalizar_pde_aic(data):
    return {
        "eps": "AIC",
        "tipo_documento": data.get("TIPO DE DOCUMENTO", "").upper(),
        "numero_documento": data.get("N° DE DOCUMENTO", ""),
        "nombre": normalizar_nombre(data.get("NOMBRE", "")),
        "regimen": homologar_regimen(data.get("REGIMEN", "")),
        "tipo_afiliado": data.get("TIPO DE AFILIADO", "").upper(),
        "estado": data.get("ESTADO", "").upper(),
        "origen": "PDE"
    }


def comparar_campos(fev, pde):
    diferencias = {}

    for campo in ["eps", "tipo_documento", "numero_documento", "nombre", "regimen"]:
        val_fev = fev.get(campo)
        val_pde = pde.get(campo)
        if val_fev != val_pde:
            diferencias[campo] = {"FEV": val_fev, "PDE": val_pde}

    estado_pde = pde.get("estado", "").upper()
    if estado_pde != "ACTIVO":
        diferencias["ALERTA ESTADO PDE"] = {
            "mensaje": "AFILIACIÓN NO ACTIVA - POSIBLE GLOSA O DEVOLUCION",
            "estado_pde": estado_pde
        }

    eps_fev = fev.get("eps", "")
    eps_pde = pde.get("eps", "")
    reg_fev = fev.get("regimen", "")
    reg_pde = pde.get("regimen", "")
    tipo_paciente = fev.get("tipo_paciente", "").upper()

    if eps_fev == eps_pde and reg_fev == reg_pde:
        if reg_fev == "SUBSIDIADO":
            if "SUBSIDIADO" not in tipo_paciente:
                diferencias["ALERTA TIPO PACIENTE"] = {
                    "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON REGIMEN SUBSIDIADO",
                    "tipo_paciente_fev": tipo_paciente
                }
        elif reg_fev == "CONTRIBUTIVO":
            if eps_fev == "EMSSANAR":
                if (
                    "CONTRIBUTIVO - COTIZANTE" not in tipo_paciente
                    and "CONTRIBUTIVO - BENEFICIARIO" not in tipo_paciente
                    and "CONTRIBUTIVO - ADICIONAL" not in tipo_paciente
                ):
                    diferencias["ALERTA TIPO PACIENTE"] = {
                        "mensaje": "TIPO PACIENTE FEV NO VALIDO PARA CONTRIBUTIVO EMSSANAR",
                        "tipo_paciente_fev": tipo_paciente
                    }
            elif eps_fev == "NUEVA EPS":
                afiliado = pde.get("tipo_afiliado", "").upper()
                esperado = f"CONTRIBUTIVO - {afiliado}"
                if esperado != tipo_paciente:
                    diferencias["ALERTA TIPO PACIENTE"] = {
                        "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON PDE",
                        "esperado": esperado, "fev": tipo_paciente
                    }
            elif eps_fev == "MALLAMAS":
                afiliado = pde.get("tipo_afiliado", "").upper()
                esperado = f"CONTRIBUTIVO - {afiliado}"
                if esperado != tipo_paciente:
                    diferencias["ALERTA TIPO PACIENTE"] = {
                        "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON PDE MALLAMAS",
                        "esperado": esperado, "fev": tipo_paciente
                    }
            elif eps_fev == "AIC":
                if reg_fev == "SUBSIDIADO":
                    if "SUBSIDIADO" not in tipo_paciente:
                        diferencias["ALERTA TIPO PACIENTE"] = {
                            "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON AIC SUBSIDIADO",
                            "fev": tipo_paciente
                        }
                elif reg_fev == "CONTRIBUTIVO":
                    if "CONTRIBUTIVO" not in tipo_paciente:
                        diferencias["ALERTA TIPO PACIENTE"] = {
                            "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON AIC CONTRIBUTIVO",
                            "fev": tipo_paciente
                        }
            else:
                afiliado = pde.get("tipo_afiliado", "").upper()
                if afiliado:
                    esperado = f"CONTRIBUTIVO - {afiliado}"
                    if esperado != tipo_paciente:
                        diferencias["ALERTA TIPO PACIENTE"] = {
                            "mensaje": "TIPO PACIENTE FEV NO COINCIDE CON PDE",
                            "esperado": esperado, "fev": tipo_paciente
                        }

    # Validación portabilidad
    eps_fev = fev.get("eps", "").upper()
    eps_pde = pde.get("eps", "").upper()
    doc_fev = fev.get("numero_documento", "")
    doc_pde = pde.get("numero_documento", "")
    if eps_fev == eps_pde and doc_fev == doc_pde and eps_fev == "EMSSANAR":
        numero_factura = fev.get("numero_factura", "").upper()
        dep_afiliacion = limpiar_texto(pde.get("departamento_afiliacion", ""))
        muni_afiliacion = limpiar_texto(pde.get("municipio_afiliacion", ""))
        dep_port = limpiar_texto(pde.get("departamento_portabilidad", ""))
        muni_port = limpiar_texto(pde.get("municipio_portabilidad", ""))

        afiliacion_orito = dep_afiliacion == "PUTUMAYO" and muni_afiliacion == "ORITO"
        tiene_portabilidad = (
            dep_port != "NO" and muni_port != "NO"
            and dep_port != "" and muni_port != ""
        )

        if not afiliacion_orito and numero_factura.startswith("CAP"):
            diferencias["ALERTA FACTURACION"] = {
                "mensaje": "PACIENTE ES PERTENECIENTE A OTROS MUNICIPIOS, FACTURADO COMO CAPITA, CORREGIR."
            }
        elif afiliacion_orito and tiene_portabilidad and numero_factura.startswith("CAP"):
            diferencias["ALERTA FACTURACION"] = {
                "mensaje": "PACIENTE CON PORTABILIDAD ACTIVA FACTURADO COMO CAPITA, CORREGIR."
            }

    numero_factura = fev.get("numero_factura", "").upper()
    cufe = fev.get("cufe", "").strip()
    if numero_factura.startswith("FEV") and cufe == "":
        diferencias["ALERTA CUFE"] = {"mensaje": "FACTURA SIN CUFE"}

    return diferencias
