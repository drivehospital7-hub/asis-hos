"""
Servicio de extracción de datos de PDFs del módulo Derechos.
Extrae texto y datos de PDFs según la entidad (EMSSANAR CAPITA, EMSSANAR URGENCIAS, etc.)
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ========================================
# Campos exactos para DERECHOS_EMSSANAR_BOXALUD
# ========================================
DERECHOS_EMSSANAR_BOXALUD = [
    "Tipo de identificacion",
    "Numero de identificacion",
    "Plan",
    "Nombre Afiliado",
    "Departamento - Municipio Afiliacion",
    "Estado Afiliado",
    "IPS Primaria",
    "Departamento - Municipio Portabilidad",
    "IPS Portabilidad",
    "Oferta",
    "IPS",
    "Sede",
    "Servicio",
]

# Intentar importar pypdf
try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    logger.warning("pypdf no está instalado: pip install pypdf")


def extraer_texto_pdf(ruta_pdf: str) -> Optional[str]:
    """
    Extrae el texto completo de un PDF.
    
    Args:
        ruta_pdf: Ruta al archivo PDF
        
    Returns:
        Texto extraído o None si hay error
    """
    if not PYPDF_AVAILABLE:
        logger.error("PyPDF2 no disponible")
        return None
    
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        
        for page in reader.pages:
            texto = page.extract_text()
            if texto:
                texto_completo += texto + "\n"
        
        logger.info("Extraído texto de %s (%d páginas)", ruta_pdf, len(reader.pages))
        return texto_completo
        
    except Exception as e:
        logger.error("Error extrayendo texto de %s: %s", ruta_pdf, e)
        return None


def extraer_datos_emssanar(texto: str | None, numero_carpeta: str) -> dict:
    """
    Extrae los datos de PDFs de EMSSANARBoxalud.
    
    Campos (hardcodeados):
    1. Tipo de identificacion
    2. Numero de identificacion
    3. Plan
    4. Nombre Afiliado
    5. Departamento - Municipio Afiliacion
    6. Estado Afiliado
    7. IPS Primaria
    8. Departamento - Municipio Portabilidad
    9. IPS Portabilidad
    10. Oferta (IPS + Sede + Servicio)
    11. IPS
    12. Sede
    13. Servicio
    """
    import re
    
    # Tipos válidos de identificación (para mapear)
    TIPOS_IDENTIFICACION = {
        "Cédula de ciudad": "Cédula de ciudadanía",
        "Tarjeta de identidad": "Tarjeta de identidad",
        "Registro civil": "Registro civil",
        "Cédula de extranjería": "Cédula de extranjería",
        "Pasaporte": "Pasaporte",
        "Adulto sin identificación": "Adulto sin identificación",
        "Menor sin identificación": "Menor sin identificación",
        "Carné diplomático": "Carné diplomático",
        "Certificado Nacido Vivo": "Certificado Nacido Vivo",
        "Permiso Especial de Permanencia": "Permiso Especial de Permanencia",
        "Salvoconducto de permanencia": "Salvoconducto de permanencia",
        "Número único identificación": "Número único identificación",
        "Pasaporte de la ONU": "Pasaporte de la ONU",
        "Permiso por Protección Temporal": "Permiso por Protección Temporal",
    }
    
    # Inicializar con campos exactos
    datos = {campo: None for campo in DERECHOS_EMSSANAR_BOXALUD}
    datos["servicios"] = []
    
    if not texto:
        datos["error"] = "Sin texto para extraer"
        return datos
    
    # Normalizar
    texto = texto.replace("\ufb01", "fi")
    texto = texto.replace("\xa0", " ")
    lineas = [l.strip() for l in texto.split("\n") if l.strip()]
    lineas = [re.sub(r'\s+', ' ', l) for l in lineas]
    
    found_subsidiado = False
    
    # Extraer cada campo
    for i, linea in enumerate(lineas):
        # Tipo de identificacion (está en la misma línea después del asterisco)
        # Ej: "Tipo identificación * Cédula de ciud"
        if "Tipo identificación" in linea or "Tipo identificaci" in linea:
            # Extraer todo después de "*"
            if "*" in linea:
                tipo_valor = linea.split("*")[-1].strip()
                if tipo_valor and tipo_valor != "-":
                    # Mapear con tipos válidos
                    for key, value in TIPOS_IDENTIFICACION.items():
                        if key.lower() in tipo_valor.lower() or tipo_valor.lower() in key.lower():
                            datos["Tipo de identificacion"] = value
                            break
                    # Si no encuentra match
                    if datos["Tipo de identificacion"] is None:
                        datos["Tipo de identificacion"] = tipo_valor
        
        # Numero de identificacion
        match = re.search(r'(?:Número|Numero)\s*de\s*Identificaci[oó]n\s*\*?\s*(\d+)', texto)
        if match and datos["Numero de identificacion"] is None:
            datos["Numero de identificacion"] = match.group(1)
        
        # Plan
        if "Plan" in linea and "Nombre" in (lineas[i + 1] if i + 1 < len(lineas) else ""):
            sig = lineas[i + 1] if i + 1 < len(lineas) else ""
            if sig and sig not in ["-", "Nombre"]:
                datos["Plan"] = sig
        
        # Nombre Afiliado (después de Subsidiado - líneas en MAYÚSCULAS)
        if "Subsidiado" in linea:
            found_subsidiado = True
            continue  # Skip esta línea, no es parte del nombre
        
        if found_subsidiado and datos["Nombre Afiliado"] is None:
            test = linea.replace(" ", "").replace(",", "")
            if test.isalpha() and len(test) > 3:
                if "PUTUMAYO" not in test.upper() and "ORITO" not in test.upper():
                    # Colectar siguientes líneas de nombre (máx 4)
                    nombre_partes = [linea.replace(",", "")]
                    for j in range(i + 1, min(i + 5, len(lineas))):
                        sig = lineas[j].strip()
                        test2 = sig.replace(" ", "").replace(",", "")
                        if test2.isalpha() and "PUTUMAYO" not in test2.upper() and "ORITO" not in test2.upper():
                            nombre_partes.append(sig.replace(",", ""))
                        else:
                            break
                    datos["Nombre Afiliado"] = " ".join(nombre_partes)
                    break
        
        # Estado Afiliado (después de "Estado")
        if linea == "Estado" and datos["Estado Afiliado"] is None:
            sig = lineas[i + 1] if i + 1 < len(lineas) else ""
            if sig and "-" not in sig:
                datos["Estado Afiliado"] = sig
        
        # IPS Primaria
        if "IPS" in linea and "Primaria" in linea and datos["IPS Primaria"] is None:
            # Buscar bloque ESE después
            for j in range(i, min(i + 10, len(lineas))):
                if lineas[j] == "ESE":
                    ips_partes = []
                    for k in range(j, min(j + 10, len(lineas))):
                        ips_partes.append(lineas[k])
                        if ")" in lineas[k]:
                            break
                    datos["IPS Primaria"] = " ".join(ips_partes)
                    break
        
        # IPS Portabilidad
        if linea == "IPS" and i > 0 and "Portabilidad" in lineas[i - 1] and datos["IPS Portabilidad"] is None:
            for j in range(i, min(i + 10, len(lineas))):
                if lineas[j] == "ESE":
                    ips_partes = []
                    for k in range(j, min(j + 10, len(lineas))):
                        ips_partes.append(lineas[k])
                        if ")" in lineas[k]:
                            break
                    datos["IPS Portabilidad"] = " ".join(ips_partes)
                    break
        
        # Oferta (buscar líneas con códigos como 8632000024)
        if re.match(r'^\d{10}\s*-', linea) and datos["Oferta"] is None:
            # Formato: CODIGO - IPS - SEDE - SERVICIO
            datos["Oferta"] = linea
            # Buscar IPS y Sede separados
            partes = linea.split(" - ")
            if len(partes) >= 3:
                datos["IPS"] = partes[1].strip()
                datos["Sede"] = partes[2].strip() if len(partes) > 2 else None
            # Buscar Servicio en siguientes líneas
            for j in range(i + 1, min(i + 3, len(lineas))):
                if "MEDICINA" in lineas[j].upper():
                    datos["Servicio"] = "MEDICINA GENERAL"
                    break
                elif "ODONTOLOG" in lineas[j].upper():
                    datos["Servicio"] = "ODONTOLOGÍA"
                    break
                elif "PROMOCIÓN" in lineas[j].upper():
                    datos["Servicio"] = "PROMOCIÓN Y PREVENCIÓN"
                    break
        
        # Servicios (lista)
        for svc in DERECHOS_EMSSANAR_BOXALUD:
            if svc not in datos and svc in ["medicina general", "odontología", "promoción y prevención"]:
                pass
    
    return datos


def validar_pdf_por_carpeta(datos: dict, numero_carpeta: str) -> dict:
    """
    Valida que el PDF corresponda a la carpeta.
    
    Validaciones obligatorias para EMSSANAR CAPITA:
    - Tener número de documento
    - Estar vigente
    """
    validacion = {
        "es_valido": True,
        "errores": [],
        "warnings": []
    }
    
    # Validaciones obligatorias
    if not datos.get("Numero de identificacion"):
        validacion["es_valido"] = False
        validacion["errores"].append("Falta número de documento")
    
    estado = datos.get("Estado Afiliado")
    if not estado:
        validacion["es_valido"] = False
        validacion["errores"].append("Falta estado del afiliado")
    elif estado != "Vigente":
        validacion["es_valido"] = False
        validacion["errores"].append(f"Afiliado no vigente: {estado}")
    
    # Advertencias
    if not datos.get("Nombre Afiliado"):
        validacion["warnings"].append("No se pudo extraer nombre")
    
    if not datos.get("IPS"):
        validacion["warnings"].append("No se encontró IPS")
    
    return validacion


def procesar_carpeta_derechos(ruta_carpeta: str, entidad: str = "EMSSANAR") -> dict:
    """
    Procesa una carpeta de derechos: busca PDFs y extrae datos.
    
    Args:
        ruta_carpeta: Ruta a la carpeta (ej: /path/to/CAP447148)
        entidad: Entidad (EMSSANAR, etc.)
        
    Returns:
        Dict con PDFs encontrados y sus datos
    """
    from app.routes.derechos import PATRON_PDE
    import os
    
    resultado = {
        "carpeta": os.path.basename(ruta_carpeta),
        "ruta": ruta_carpeta,
        "pdfs": [],
        "sin_pdf": False
    }
    
    # Buscar PDFs en la carpeta
    archivos_pdf = []
    for f in os.listdir(ruta_carpeta):
        if f.lower().endswith(".pdf") and PATRON_PDE.search(f):
            archivos_pdf.append(f)
    
    if not archivos_pdf:
        resultado["sin_pdf"] = True
        return resultado
    
    # Procesar cada PDF
    for nombre_pdf in archivos_pdf:
        ruta_pdf = os.path.join(ruta_carpeta, nombre_pdf)
        
        # Extraer texto
        texto = extraer_texto_pdf(ruta_pdf)
        
        # Extraer datos según entidad
        numero_carpeta = os.path.basename(ruta_carpeta)
        
        if entidad == "EMSSANAR":
            datos = extraer_datos_emssanar(texto, numero_carpeta)
        else:
            datos = {"texto_completo": texto[:500] if texto else None}
        
        # Validar
        validacion = validar_pdf_por_carpeta(datos, numero_carpeta)
        
        resultado["pdfs"].append({
            "nombre": nombre_pdf,
            "ruta": ruta_pdf,
            "datos": datos,
            "validacion": validacion
        })
    
    return resultado