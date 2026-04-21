"""Servicio para manejo de hoja Revisión.

Este módulo detecta problemas en las facturas y los lista
en la hoja "Revision" para revisión manual.

Problemas detectados:
- Decimales: Facturas con valores decimales en Vlr. Subsidiado o Vlr. Procedimiento
- Doble tipo procedimiento: Facturas con más de un tipo de procedimiento
- Ruta duplicada: Pacientes con >= 3 facturas en Promoción y Prevención
- Convenio de procedimiento: Procedimientos que no corresponden al convenio
- Cantidades: Facturas con cantidades anómalas
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.constants import (
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    REVISION_SHEET,
    REVISION_HEADERS,
    URGENCIA_REVISION_HEADERS,
    TARGET_PROCEDURES,
    PYP_CUPS_CODES,
    RUTA_DUPLICADA_THRESHOLD,
    CANTIDAD_CONSULTAS_MIN,
    CANTIDAD_MAX,
    CANTIDAD_PYP_MIN,
    AREA_ODONTOLOGIA,
    AREA_URGENCIAS,
    AREA_EQUIPOS_BASICOS,
    CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO,
    LABORATORIO_NO,
    CENTRO_COSTO_APOYO_DIAGNOSTICO,
    CODIGOS_EXCEPTUADOS,
    URGENCIA_DATA_ROW_BACKGROUND_COLOR,
    CODIGOS_PYP_URGENCIAS,
    CENTRO_COSTO_PYP_URGENCIAS,
    CODIGOS_QUIROFANO_URGENCIAS,
    CENTRO_COSTO_QUIROFANO_URGENCIAS,
    CODIGOS_LABORATORIO_URGENCIAS,
    CENTRO_COSTO_LABORATORIO_URGENCIAS,
    CENTRO_COSTO_ODONTOLOGIA,
    CENTRO_COSTO_EXTRAMURAL,
    CENTRO_COSTO_EQUIPOS_BASICOS,
    PROFESIONALES_ODONTOLOGIA,
    # IDE Contrato Urgencias
    CODIGO_IDE_CONTRATO_URGENCIAS,
    ENTIDAD_IDE_CONTRATO_URGENCIAS,
    IDE_CONTRATO_REQUERIDO_URGENCIAS,
    CODIGO_IDE_CONTRATO_861801_EPSI05,
    ENTIDAD_IDE_CONTRATO_861801_EPSI05,
    IDE_CONTRATO_REQUERIDO_861801_EPSI05,
    CODIGO_IDE_CONTRATO_890405_EPSI05,
    ENTIDAD_IDE_CONTRATO_890405_EPSI05,
    IDE_CONTRATO_CON_INSERCION_890405_EPSI05,
    IDE_CONTRATO_SIN_INSERCION_890405_EPSI05,
    CODIGO_INSERCION_BUSCAR,
    # Nueva regla EPSIC5
    CODIGO_IDE_CONTRATO_EPSIC5,
    ENTIDAD_IDE_CONTRATO_EPSIC5,
    IDE_CONTRATO_REQUERIDO_EPSIC5,
    CODIGO_IDE_CONTRATO_890405_EPSIC5,
    ENTIDAD_IDE_CONTRATO_890405_EPSIC5,
    IDE_CONTRATO_CON_INSERCION_890405_EPSIC5,
    IDE_CONTRATO_SIN_INSERCION_890405_EPSIC5,
    # Nueva regla ESS118 + Código 735301
    CODIGO_IDE_CONTRATO_735301,
    ENTIDAD_IDE_CONTRATO_735301,
    IDE_CONTRATO_REQUERIDO_735301,
    # Nueva regla ESS118 + Código 906340 -> IDE Contrato debe ser 839
    CODIGO_IDE_CONTRATO_906340_ESS118,
    ENTIDAD_IDE_CONTRATO_906340_ESS118,
    IDE_CONTRATO_REQUERIDO_906340_ESS118,
    # Nueva regla ESS118 + Código 861801 -> IDE Contrato debe ser 974
    CODIGO_IDE_CONTRATO_861801_ESS118,
    ENTIDAD_IDE_CONTRATO_861801_ESS118,
    IDE_CONTRATO_REQUERIDO_861801_ESS118,
    # Nueva regla ESS118 + Código 890405 -> IDE Contrato 977 o 973 según inserción
    CODIGO_IDE_CONTRATO_890405_ESS118,
    ENTIDAD_IDE_CONTRATO_890405_ESS118,
    IDE_CONTRATO_SIN_INSERCION_890405_ESS118,
    IDE_CONTRATO_CON_INSERCION_890405_ESS118,
    # Nueva regla ESSC18 + Código 906340 -> IDE Contrato debe ser 842
    CODIGO_IDE_CONTRATO_906340_ESSC18,
    ENTIDAD_IDE_CONTRATO_ESSC18,
    IDE_CONTRATO_REQUERIDO_906340_ESSC18,
    # Nueva regla ESSC18 + Código 861801 -> IDE Contrato debe ser 975
    CODIGO_IDE_CONTRATO_861801_ESSC18,
    IDE_CONTRATO_REQUERIDO_861801_ESSC18,
    # Nueva regla ESSC18 + Código 890405 -> IDE Contrato según inserción
    CODIGO_IDE_CONTRATO_890405_ESSC18,
    IDE_CONTRATO_CON_INSERCION_890405_ESSC18,
    IDE_CONTRATO_SIN_INSERCION_890405_ESSC18,
    # Nueva regla EPS037 + Código 906340 -> IDE Contrato debe ser 962
    CODIGO_IDE_CONTRATO_906340_EPS037,
    ENTIDAD_IDE_CONTRATO_EPS037,
    IDE_CONTRATO_REQUERIDO_906340_EPS037,
    # Nueva regla EPS037 + Código 861801 -> IDE Contrato debe ser 961
    CODIGO_IDE_CONTRATO_861801_EPS037,
    IDE_CONTRATO_REQUERIDO_861801_EPS037,
    # Nueva regla EPS037 + Código 890405 -> IDE Contrato según inserción
    CODIGO_IDE_CONTRATO_890405_EPS037,
    IDE_CONTRATO_CON_INSERCION_890405_EPS037,
    IDE_CONTRATO_SIN_INSERCION_890405_EPS037,
    # Nueva regla EPSS41 + Código 906340 -> IDE 959
    CODIGO_IDE_CONTRATO_906340_EPSS41,
    IDE_CONTRATO_REQUERIDO_906340_EPSS41,
    # Nueva regla EPSS41 + Código 861801 -> IDE 958
    CODIGO_IDE_CONTRATO_861801_EPSS41,
    IDE_CONTRATO_REQUERIDO_861801_EPSS41,
    # Nueva regla EPSS41 + Código 890405 -> IDE según inserción
    CODIGO_IDE_CONTRATO_890405_EPSS41,
    IDE_CONTRATO_CON_INSERCION_890405_EPSS41,
    IDE_CONTRATO_SIN_INSERCION_890405_EPSS41,
    # Nueva regla ESS062 + Código 861801 -> IDE Contrato debe ser 922
    CODIGO_IDE_CONTRATO_861801_ESS062,
    ENTIDAD_IDE_CONTRATO_ESS062,
    IDE_CONTRATO_REQUERIDO_861801_ESS062,
    # Nueva regla ESS062 + Código 890405 -> IDE Contrato según inserción
    CODIGO_IDE_CONTRATO_890405_ESS062,
    IDE_CONTRATO_CON_INSERCION_890405_ESS062,
    IDE_CONTRATO_SIN_INSERCION_890405_ESS062,
    # Nueva regla ESSC62 + Código 861801 -> IDE Contrato debe ser 863
    CODIGO_IDE_CONTRATO_861801_ESSC62,
    ENTIDAD_IDE_CONTRATO_ESSC62,
    IDE_CONTRATO_REQUERIDO_861801_ESSC62,
    # Nueva regla ESSC62 + Código 890405 -> IDE Contrato según si tiene 890405
    CODIGO_IDE_CONTRATO_890405_ESSC62,
    CODIGO_A_BUSCAR_890405_ESSC62,
    IDE_CONTRATO_CON_INSERCION_890405_ESSC62,
    IDE_CONTRATO_SIN_INSERCION_890405_ESSC62,
    # Urgencias - Entidad -> IDE Contrato
    URGENCIA_ENTIDAD_CONTRATO,
    URGENCIA_ENTIDAD_MULTIPLE_CONTRATO,
    # ESS118 + Procedimientos PyP -> IDE Contrato 970 o 974
    ENTIDAD_IDE_CONTRATO_ESS118_PYP,
    IDE_CONTRATO_MULTIPLE_ESS118_PYP,
    IDE_CONTRATO_MULTIPLE_ESS118_NO_PYP,
    # ESSC18 + Procedimientos PyP -> IDE Contrato 975
    ENTIDAD_IDE_CONTRATO_ESSC18_PYP,
    IDE_CONTRATO_MULTIPLE_ESSC18_PYP,
    IDE_CONTRATO_MULTIPLE_ESSC18_NO_PYP,
    # EPSS41 + Procedimientos PyP -> IDE Contrato 955 o 958
    ENTIDAD_IDE_CONTRATO_EPSS41_PYP,
    IDE_CONTRATO_MULTIPLE_EPSS41_PYP,
    IDE_CONTRATO_MULTIPLE_EPSS41_NO_PYP,
    # EPS037 + Procedimientos PyP -> IDE Contrato 961
    ENTIDAD_IDE_CONTRATO_EPS037_PYP,
    IDE_CONTRATO_MULTIPLE_EPS037_PYP,
    IDE_CONTRATO_MULTIPLE_EPS037_NO_PYP,
    # EPSI05 + Procedimientos PyP -> IDE Contrato 977
    ENTIDAD_IDE_CONTRATO_EPSI05_PYP,
    IDE_CONTRATO_MULTIPLE_EPSI05_PYP,
    IDE_CONTRATO_MULTIPLE_EPSI05_NO_PYP,
    # EPSIC5 + Procedimientos PyP -> IDE Contrato 979
    ENTIDAD_IDE_CONTRATO_EPSIC5_PYP,
    IDE_CONTRATO_MULTIPLE_EPSIC5_PYP,
    IDE_CONTRATO_MULTIPLE_EPSIC5_NO_PYP,
    # RES001 + Procedimientos PyP -> IDE Contrato 954
    ENTIDAD_IDE_CONTRATO_RES001_PYP,
    IDE_CONTRATO_MULTIPLE_RES001_PYP,
    IDE_CONTRATO_MULTIPLE_RES001_NO_PYP,
    # ESS062 + Procedimientos PyP -> IDE Contrato 922
    ENTIDAD_IDE_CONTRATO_ESS062_PYP,
    IDE_CONTRATO_MULTIPLE_ESS062_PYP,
    IDE_CONTRATO_MULTIPLE_ESS062_NO_PYP,
    # ESSC62 + Procedimientos PyP -> IDE Contrato 863
    ENTIDAD_IDE_CONTRATO_ESSC62_PYP,
    IDE_CONTRATO_MULTIPLE_ESSC62_PYP,
    IDE_CONTRATO_MULTIPLE_ESSC62_NO_PYP,
    # 0001 + Procedimientos PyP -> IDE Contrato 17
    ENTIDAD_IDE_CONTRATO_0001_PYP,
    IDE_CONTRATO_MULTIPLE_0001_PYP,
    IDE_CONTRATO_MULTIPLE_0001_NO_PYP,
    # EPSS005 + Procedimientos PyP -> IDE Contrato 933
    ENTIDAD_IDE_CONTRATO_EPSS005_PYP,
    IDE_CONTRATO_MULTIPLE_EPSS005_PYP,
    IDE_CONTRATO_MULTIPLE_EPSS005_NO_PYP,
    # EPSC005 + Procedimientos PyP -> IDE Contrato 932
    ENTIDAD_IDE_CONTRATO_EPSC005_PYP,
    IDE_CONTRATO_MULTIPLE_EPSC005_PYP,
    IDE_CONTRATO_MULTIPLE_EPSC005_NO_PYP,
    # 86 + Procedimientos NO PyP -> IDE Contrato 911
    ENTIDAD_IDE_CONTRATO_86_NO_PYP,
    IDE_CONTRATO_MULTIPLE_86_NO_PYP,
    # 86000 + Procedimientos PyP -> IDE Contrato 920
    ENTIDAD_IDE_CONTRATO_86000_PYP,
    IDE_CONTRATO_MULTIPLE_86000_PYP,
    IDE_CONTRATO_MULTIPLE_86000_NO_PYP,
    # Equipos Básicos - Reglas independientes (comparte PYP_CUPS_CODES con Odontología)
    EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD,
    EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN,
    EQUIPOS_BASICOS_CANTIDAD_MAX,
    EQUIPOS_BASICOS_CANTIDAD_PYP_MIN,
)

from app.utils.formatting import (
    create_header_style,
    create_data_row_style,
    create_urgencia_header_style,
    create_urgencia_data_row_style,
    auto_adjust_column_width,
)

# Importar reglas transversales
from app.services.transversales import (
    detect_decimales,
    detect_tipo_documento_edad,
    detect_codigo_entidad_vs_entidad_afiliacion,
)

logger = logging.getLogger(__name__)


def _normalize_header(value: Any) -> str:
    """Normaliza un header a minúsculas sin espacios extra."""
    return str(value).strip().lower() if value is not None else ""


def _normalize_invoice(value: Any) -> str | None:
    """Normaliza un número de factura a string."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and value == int(value):
        return str(int(value))
    return str(value).strip() or None


def _get_column_indices(headers: list[Any]) -> tuple[dict[str, int | None], list[str]]:
    """
    Mapea nombres de columna a sus índices.
    
    REQUIERE COINCIDENCIA EXACTA - NO infiere nombres similares.
    Si una columna no coincide exactamente, retorna None y la reporta en la lista de errores.
    
    Args:
        headers: Lista de nombres de columna del Excel
        
    Returns:
        Tuple de (dict con nombre de columna -> índice 0-based o None, 
                  lista de columnas NO encontradas)
    """
    indices: dict[str, int | None] = {
        "numero_factura": None,
        "vlr_subsidiado": None,
        "vlr_procedimiento": None,
        "codigo_tipo_procedimiento": None,
        "tipo_procedimiento": None,
        "codigo": None,
        "codigo_equiv": None,
        "procedimiento": None,
        "identificacion": None,
        "convenio_facturado": None,
        "cantidad": None,
        "laboratorio": None,
        "centro_costo": None,
        "codigo_entidad_cobrar": None,
        "entidad_cobrar": None,
        "entidad_afiliacion": None,
        "tipo_factura_descripcion": None,
        "ide_contrato": None,
        "tipo_identificacion": None,
        "fec_nacimiento": None,
        "fec_factura": None,
        "profesional_identificacion": None,
        "profesional_atiende": None,
    }
    
    # Nombres EXACTOS requeridos - uno solo por columna, sin variantes
    # Si no coincide exactamente, NO infiere - reporta error
    required_headers: dict[str, str] = {
        "numero_factura": "Número Factura",
        "vlr_subsidiado": "Vlr. Subsidiado",
        "vlr_procedimiento": "Vlr. Procedimiento",
        "codigo_tipo_procedimiento": "Código Tipo Procedimiento",
        "tipo_procedimiento": "Tipo Procedimiento",
        "codigo": "Código",
        "codigo_equiv": "Cód. Equivalente CUPS",
        "procedimiento": "Procedimiento",
        "identificacion": "Nº Identificación",
        "convenio_facturado": "Convenio Facturado",
        "cantidad": "Cantidad",
        "laboratorio": "Laboratorio",
        "centro_costo": "Centro Costo",
        "codigo_entidad_cobrar": "Cód Entidad Cobrar",
        "entidad_cobrar": "Entidad Cobrar",
        "entidad_afiliacion": "Entidad Afiliación",
        "tipo_factura_descripcion": "Tipo Factura Descripción",
        "ide_contrato": "IDE Contrato",
        "tipo_identificacion": "Tipo Identificación",
        "fec_nacimiento": "Fec. Nacimiento",
        "fec_factura": "Fec. Factura",
        "profesional_identificacion": "Identificación Profesional",
        "profesional_atiende": "Profesional Atiende",
    }
    
# Normalizar headers del Excel para comparación EXACTA (sin strip para mantener espacios)
    excel_headers_normalized: dict[str, int] = {}
    for i, header in enumerate(headers):
        if header is not None:
            # Usar el header tal cual viene del Excel
            normalized = str(header).strip()
            excel_headers_normalized[normalized] = i
    
    # Buscar coincidencia EXACTA para cada columna requerida
    missing_columns: list[str] = []
    for key, required_name in required_headers.items():
        # Buscar con el nombre exacto
        if required_name in excel_headers_normalized:
            indices[key] = excel_headers_normalized[required_name]
        else:
            # NO encontrado - reportar como faltante
            missing_columns.append(required_name)
    
    # Log de结果
    found_columns = [k for k, v in indices.items() if v is not None]
    if missing_columns:
        logger.error("Columnas FALTANTES (no hay coincidencia exacta): %s", missing_columns)
    
    logger.info("Indices detectados (coincidencia exacta): %d/%d", len(found_columns), len(indices))
    
    return indices, missing_columns


def _detect_decimals(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con valores decimales."""
    decimal_invoices = []
    
    num_fact_idx = indices["numero_factura"]
    vlr_sub_idx = indices["vlr_subsidiado"]
    vlr_proc_idx = indices["vlr_procedimiento"]
    
    if num_fact_idx is None:
        return []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        has_decimals = False
        valores_con_decimal = []
        
        if vlr_sub_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_sub_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
                valores_con_decimal.append(f"Vlr. Subsidiado: {vlr}")
        
        if not has_decimals and vlr_proc_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_proc_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
                valores_con_decimal.append(f"Vlr. Procedimiento: {vlr}")
        
        if has_decimals and factura_str not in [d.get("factura") for d in decimal_invoices]:
            decimal_invoices.append({
                "factura": factura_str,
                "valores": ", ".join(valores_con_decimal),
            })
            logger.debug("Factura %s con decimales detectada", factura_str)
    
    return decimal_invoices


def _detect_doble_tipo_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con más de un tipo de procedimiento."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    
    if num_fact_idx is None or tipo_proc_idx is None:
        return []
    
    tipo_por_factura: dict[str, set[str]] = {}
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        if tipo_value is not None:
            tipo_str = str(tipo_value).strip()
            if tipo_str:
                tipo_por_factura.setdefault(factura_str, set()).add(tipo_str)
    
    result = []
    for fact, tipos in tipo_por_factura.items():
        if len(tipos) > 1:
            result.append({
                "factura": fact,
                "tipos": ", ".join(sorted(tipos)),
            })
    return result


def _detect_ruta_duplicada(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta pacientes con múltiples facturas en PyP."""
    num_fact_idx = indices["numero_factura"]
    ident_idx = indices["identificacion"]
    contrato_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, ident_idx, contrato_idx):
        return []
    
    conteo_ident: dict[str, set[str]] = defaultdict(set)
    
    for row in range(2, data_sheet.max_row + 1):
        contrato = data_sheet.cell(row=row, column=contrato_idx + 1).value
        if contrato != CONVENIO_PYP:
            continue
        
        ident = data_sheet.cell(row=row, column=ident_idx + 1).value
        factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        
        if ident is not None and factura is not None:
            ident_str = str(ident).strip()
            factura_str = str(factura).strip()
            if ident_str and factura_str:
                conteo_ident[ident_str].add(factura_str)
    
    result = []
    for ident, facturas in conteo_ident.items():
        if len(facturas) >= RUTA_DUPLICADA_THRESHOLD:
            result.append({
                "identificacion": ident,
                "facturas": ", ".join(sorted(facturas)),
                "cantidad": len(facturas),
            })
    return result


def _detect_ruta_duplicada_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta pacientes con múltiples facturas en PyP (Equipos Básicos - reglas independientes)."""
    num_fact_idx = indices["numero_factura"]
    ident_idx = indices["identificacion"]
    contrato_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, ident_idx, contrato_idx):
        return []
    
    conteo_ident: dict[str, set[str]] = defaultdict(set)
    
    for row in range(2, data_sheet.max_row + 1):
        contrato = data_sheet.cell(row=row, column=contrato_idx + 1).value
        if contrato != CONVENIO_PYP:
            continue
        
        ident = data_sheet.cell(row=row, column=ident_idx + 1).value
        factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        
        if ident is not None and factura is not None:
            ident_str = str(ident).strip()
            factura_str = str(factura).strip()
            if ident_str and factura_str:
                conteo_ident[ident_str].add(factura_str)
    
    result = []
    for ident, facturas in conteo_ident.items():
        if len(facturas) >= EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD:
            result.append({
                "identificacion": ident,
                "facturas": ", ".join(sorted(facturas)),
                "cantidad": len(facturas),
            })
    return result


def _detect_convenio_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con procedimientos que no corresponden al convenio.
    
    Usa el código CUPS (columna 'Código') para validar.
    """
    num_fact_idx = indices["numero_factura"]
    convenio_idx = indices["convenio_facturado"]
    codigo_idx = indices.get("codigo")
    
    if None in (num_fact_idx, convenio_idx) or codigo_idx is None:
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        
        if codigo is None:
            continue
        
        # Normalizar código: quitar espacios, mayúsculas
        codigo_str = str(codigo).strip().upper()
        should_add = False
        problema_tipo = ""
        
        # Caso 1: Convenio Asistencial con códigos PyP
        if convenio == CONVENIO_ASISTENCIAL and codigo_str in PYP_CUPS_CODES:
            should_add = True
            problema_tipo = "Asistencial con procedimiento PyP"
            logger.debug(
                "Fila %s: Asistencial con código PyP: %s",
                row,
                codigo_str,
            )
        
        # Caso 2: Convenio PyP con códigos NO PyP
        elif convenio == CONVENIO_PYP and codigo_str not in PYP_CUPS_CODES:
            should_add = True
            problema_tipo = "PyP con procedimiento no PyP"
            logger.debug(
                "Fila %s: PyP con código diferente: %s",
                row,
                codigo_str,
            )
        
        if should_add and factura_str not in [p.get("factura") for p in problemas]:
            problemas.append({
                "factura": factura_str,
                "convenio": str(convenio) if convenio else "",
                "codigo": codigo_str,
                "problema": problema_tipo,
            })
    
    return problemas


def _detect_convenio_procedimiento_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con procedimientos que no corresponden al convenio (Equipos Básicos).
    
    Usa el código CUPS (columna 'Código') para validar.
    """
    num_fact_idx = indices["numero_factura"]
    convenio_idx = indices["convenio_facturado"]
    codigo_idx = indices.get("codigo")
    
    if None in (num_fact_idx, convenio_idx) or codigo_idx is None:
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        
        if codigo is None:
            continue
        
        # Normalizar código: quitar espacios, mayúsculas
        codigo_str = str(codigo).strip().upper()
        should_add = False
        problema_tipo = ""
        
        # Caso 1: Convenio Asistencial con códigos PyP (Equipos Básicos)
        if convenio == CONVENIO_ASISTENCIAL and codigo_str in PYP_CUPS_CODES:
            should_add = True
            problema_tipo = "Asistencial con procedimiento PyP"
            logger.debug(
                "Fila %s: Asistencial con código PyP (Equipos Básicos): %s",
                row,
                codigo_str,
            )
        
        # Caso 2: Convenio PyP con códigos NO PyP (Equipos Básicos)
        elif convenio == CONVENIO_PYP and codigo_str not in PYP_CUPS_CODES:
            should_add = True
            problema_tipo = "PyP con procedimiento no PyP"
            logger.debug(
                "Fila %s: PyP con código diferente (Equipos Básicos): %s",
                row,
                codigo_str,
            )
        
        if should_add and factura_str not in [p.get("factura") for p in problemas]:
            problemas.append({
                "factura": factura_str,
                "convenio": str(convenio) if convenio else "",
                "codigo": codigo_str,
                "problema": problema_tipo,
            })
    
    return problemas


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con cantidades anómalas."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    conveniencia_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, conveniencia_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        conveniencia = data_sheet.cell(row=row, column=conveniencia_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Determinar tipo de problema
        problema_tipo = ""
        if tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN:
            problema_tipo = f"Consultas con cantidad {cantidad} (mín. {CANTIDAD_CONSULTAS_MIN})"
        elif cantidad > CANTIDAD_MAX:
            problema_tipo = f"Cantidad {cantidad} > máximo {CANTIDAD_MAX}"
        elif conveniencia == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN:
            problema_tipo = f"PyP con cantidad {cantidad} (mín. {CANTIDAD_PYP_MIN})"
        
        # Reglas de cantidad anómala
        is_anomaly = (
            # Consultas >= 2
            (tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > 10
            or cantidad > CANTIDAD_MAX
            # PyP >= 3
            or (conveniencia == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in [p.get("factura") for p in problemas]:
            problemas.append({
                "factura": factura_str,
                "tipo_procedimiento": str(tipo_value) if tipo_value else "",
                "cantidad": cantidad,
                "convenio": str(conveniencia) if conveniencia else "",
                "problema": problema_tipo,
            })
            logger.debug(
                "Fila %s: Cantidad anómala (Tipo: %s, Convenio: %s, Cant: %s)",
                row,
                tipo_value,
                conveniencia,
                cantidad,
            )
    
    return problemas


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con cantidades anómalas."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    procedimiento_idx = indices["procedimiento"]
    conveniencia_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, procedimiento_idx, conveniencia_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=procedimiento_idx + 1).value
        conveniencia = data_sheet.cell(row=row, column=conveniencia_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Determinar tipo de problema
        problema_tipo = ""
        if tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN:
            problema_tipo = f"Consultas con cantidad {cantidad} (mín. {CANTIDAD_CONSULTAS_MIN})"
        elif cantidad > CANTIDAD_MAX:
            problema_tipo = f"Cantidad {cantidad} > máximo {CANTIDAD_MAX}"
        elif conveniencia == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN:
            problema_tipo = f"PyP con cantidad {cantidad} (mín. {CANTIDAD_PYP_MIN})"
        
        # Reglas de cantidad anómala
        is_anomaly = (
            # Consultas >= 2
            (tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > 10
            or cantidad > CANTIDAD_MAX
            # PyP >= 3
            or (conveniencia == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in [p.get("factura") for p in problemas]:
            problemas.append({
                "factura": factura_str,
                "tipo_procedimiento": str(tipo_value) if tipo_value else "",
                "procedimiento": str(procedimiento).strip() if procedimiento else "",
                "cantidad": cantidad,
                "convenio": str(conveniencia) if conveniencia else "",
                "problema": problema_tipo,
            })
            logger.debug(
                "Fila %s: Cantidad anómala (Tipo: %s, Procedimiento: %s, Cant: %s)",
                row,
                tipo_value,
                procedimiento,
                cantidad,
            )
    
    return problemas


def _detect_cantidades_anomalas_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict]:
    """Detecta facturas con cantidades anómalas (Equipos Básicos - reglas independientes)."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    procedimiento_idx = indices["procedimiento"]
    conveniencia_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, procedimiento_idx, conveniencia_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=procedimiento_idx + 1).value
        convenio = data_sheet.cell(row=row, column=conveniencia_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Determinar tipo de problema
        problema_tipo = ""
        if tipo_value == "Consultas" and cantidad >= EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN:
            problema_tipo = f"Consultas con cantidad {cantidad} (mín. {EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN})"
        elif cantidad > EQUIPOS_BASICOS_CANTIDAD_MAX:
            problema_tipo = f"Cantidad {cantidad} > máximo {EQUIPOS_BASICOS_CANTIDAD_MAX}"
        elif convenio == CONVENIO_PYP and cantidad >= EQUIPOS_BASICOS_CANTIDAD_PYP_MIN:
            problema_tipo = f"PyP con cantidad {cantidad} (mín. {EQUIPOS_BASICOS_CANTIDAD_PYP_MIN})"
        
        # Reglas de cantidad anómala (Equipos Básicos - configurables)
        is_anomaly = (
            # Consultas >= umbral configurable
            (tipo_value == "Consultas" and cantidad >= EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > máximo configurable
            or cantidad > EQUIPOS_BASICOS_CANTIDAD_MAX
            # PyP >= umbral configurable
            or (convenio == CONVENIO_PYP and cantidad >= EQUIPOS_BASICOS_CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in [p.get("factura") for p in problemas]:
            problemas.append({
                "factura": factura_str,
                "tipo_procedimiento": str(tipo_value) if tipo_value else "",
                "procedimiento": str(procedimiento).strip() if procedimiento else "",
                "cantidad": cantidad,
                "convenio": str(convenio) if convenio else "",
                "problema": problema_tipo,
            })
            logger.debug(
                "Fila %s: Cantidad anómala Equipos Básicos (Tipo: %s, Procedimiento: %s, Cant: %s)",
                row,
                tipo_value,
                procedimiento,
                cantidad,
            )
    
    return problemas


def _detect_tipo_identificacion_edad(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
    """
    Detecta facturas donde el tipo de identificación no coincide con la edad.
    
    Reglas:
    - < 7 años: RC (Registro Civil)
    - 7-17 años: TI (Tarjeta de Identidad)
    - >= 18 años: CC (Cédula de Ciudadanía)
    - Extranjeros < 18 años: MS
    - Extranjeros >= 18 años: AS
    - CN (Certificado de Nacimiento): solo válido si edad < 2 meses
    - CE (Cédula Extranjería): solo válido si edad > 7 años
    
    Returns:
        Lista de dicts con keys: "factura", "tipo_actual", "tipo_deberia", "edad"
    """
    from datetime import datetime
    
    tipo_id_idx = indices["tipo_identificacion"]
    fec_nac_idx = indices["fec_nacimiento"]
    fec_fact_idx = indices["fec_factura"]
    num_fact_idx = indices["numero_factura"]
    
    if None in (tipo_id_idx, fec_nac_idx, fec_fact_idx, num_fact_idx):
        logger.warning(
            "No se pueden detectar errores de tipo identificación: "
            "columnas requeridas no encontradas. "
            "tipo_id=%s, fec_nac=%s, fec_fact=%s, num_fact=%s",
            tipo_id_idx, fec_nac_idx, fec_fact_idx, num_fact_idx
        )
        return []
    
    problemas = []
    facturas_ya_procesadas = set()
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str or factura_str in facturas_ya_procesadas:
            continue
        
        tipo_id = data_sheet.cell(row=row, column=tipo_id_idx + 1).value
        fec_nac = data_sheet.cell(row=row, column=fec_nac_idx + 1).value
        fec_fact = data_sheet.cell(row=row, column=fec_fact_idx + 1).value
        
        logger.debug(
            "Fila %s: tipo_id=%s, fec_nac=%s, fec_fact=%s",
            row, repr(tipo_id), repr(fec_nac), repr(fec_fact)
        )
        
        if not tipo_id or not fec_nac or not fec_fact:
            continue
        
        tipo_id_str = str(tipo_id).strip().upper()
        
        # Calcular edad
        try:
            # Intentar convertir fechas - varios formatos
            if isinstance(fec_nac, datetime):
                fecha_nac = fec_nac
            else:
                fec_nac_str = str(fec_nac).strip()
                # Intentar con formato fecha+hora primero
                try:
                    fecha_nac = datetime.strptime(fec_nac_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha_nac = datetime.strptime(fec_nac_str, "%Y-%m-%d")
            
            if isinstance(fec_fact, datetime):
                fecha_fact = fec_fact
            else:
                fec_fact_str = str(fec_fact).strip()
                try:
                    fecha_fact = datetime.strptime(fec_fact_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    fecha_fact = datetime.strptime(fec_fact_str, "%Y-%m-%d")
            
            # Calcular edad en años
            edad = fecha_fact.year - fecha_nac.year
            if (fecha_fact.month, fecha_fact.day) < (fecha_nac.month, fecha_nac.day):
                edad -= 1
            
            # Calcular edad en meses para validaciones especiales (CN)
            edad_meses = (fecha_fact.year - fecha_nac.year) * 12 + (fecha_fact.month - fecha_nac.month)
            
            logger.debug(
                "Fila %s: FechaNac=%s, FechaFact=%s, Edad calculada=%d años, %d meses",
                row, fecha_nac.date(), fecha_fact.date(), edad, edad_meses
            )
        except (ValueError, TypeError) as e:
            logger.debug("Fila %s: Error calculando edad: %s", row, e)
            continue
        
        # Determinar tipo correcto según edad
        tipo_correcto = None
        if tipo_id_str in ("RC", "TI", "CC"):
            if edad < 7:
                tipo_correcto = "RC"
            elif edad < 18:
                tipo_correcto = "TI"
            else:
                tipo_correcto = "CC"
        elif tipo_id_str in ("MS", "AS"):
            if edad < 18:
                tipo_correcto = "MS"
            else:
                tipo_correcto = "AS"
        elif tipo_id_str == "CN":
            # CN solo válido si edad < 2 meses
            if edad_meses >= 2:
                tipo_correcto = "ERROR"  # CN no válido para >= 2 meses
        elif tipo_id_str == "CE":
            # CE solo válido si edad > 7 años
            if edad <= 7:
                tipo_correcto = "ERROR"  # CE no válido para <= 7 años
        # Tipos no válidos siempre son error
        elif tipo_id_str in ("NIP", "NIT", "PAS", "PE", "SC"):
            tipo_correcto = "ERROR"  # Tipos no permitidos
        
        logger.debug(
            "Fila %s: Edad=%d, Tipo actual=%s, Tipo correcto=%s",
            row, edad, tipo_id_str, tipo_correcto
        )
        
        # Si hay error, registrar
        if tipo_correcto and tipo_id_str != tipo_correcto:
            problemas.append({
                "factura": factura_str,
                "tipo_actual": tipo_id_str,
                "tipo_deberia": tipo_correcto,
                "edad": str(edad),
            })
            facturas_ya_procesadas.add(factura_str)
            logger.debug(
                "Fila %s: Tipo identificación incorrecto (Edad: %d, Tipo: %s, Debería: %s)",
                row,
                edad,
                tipo_id_str,
                tipo_correcto,
)

    return problemas


def _detect_ide_contrato_odontologia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
    """
    Detenta facturas con problemas de IDE Contrato en Odontología.
    
    Reglas:
    - ESS118 + Código PyP -> IDE debe ser 970 o 974
    - ESS118 + Código NO PyP -> IDE debe ser 969 o 973
    - ESSC18 + Código PyP -> IDE debe ser 975
    - ESSC18 + Código NO PyP -> IDE debe ser 968
    
    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas
    
    Returns:
        Lista de dicts con keys: "factura", "codigo", "entidad", "ide_contrato_actual", "ide_contrato_deberia", "nota"
    """
    num_fact_idx = indices["numero_factura"]
    codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
    codigo_idx = indices.get("codigo")
    ide_contrato_idx = indices.get("ide_contrato")
    
    logger.info(
        "IDE Contrato - Índices: numero_factura=%s, codigo_entidad=%s, codigo=%s, ide_contrato=%s",
        num_fact_idx,
        codigo_entidad_idx,
        codigo_idx,
        ide_contrato_idx,
    )
    
    if None in (num_fact_idx, codigo_entidad_idx) or codigo_idx is None or ide_contrato_idx is None:
        logger.warning(
            "IDE Contrato - Columnas necesarias no encontradas: "
            "num_factura=%s, codigo_entidad=%s, codigo=%s, ide_contrato=%s",
            num_fact_idx,
            codigo_entidad_idx,
            codigo_idx,
            ide_contrato_idx,
        )
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        codigo_entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        ide_contrato = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        
        if codigo_entidad is None or codigo is None or ide_contrato is None:
            continue
        
        codigo_entidad_str = str(codigo_entidad).strip().upper()
        codigo_str = str(codigo).strip().upper()
        ide_str = str(ide_contrato).strip()
        
        # Determinar IDE esperado según entidad y código
        ide_esperado = None
        nota = ""
        
        if codigo_entidad_str == "ESS118":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESS118_PYP
                nota = "ESS118 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESS118_NO_PYP
                nota = "ESS118 + NO PyP"
        
        elif codigo_entidad_str == "ESSC18":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESSC18_PYP
                nota = "ESSC18 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESSC18_NO_PYP
                nota = "ESSC18 + NO PyP"
        
        elif codigo_entidad_str == "EPSS41":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSS41_PYP
                nota = "EPSS41 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSS41_NO_PYP
                nota = "EPSS41 + NO PyP"
        
        elif codigo_entidad_str == "EPS037":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPS037_PYP
                nota = "EPS037 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPS037_NO_PYP
                nota = "EPS037 + NO PyP"
        
        elif codigo_entidad_str == "EPSI05":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSI05_PYP
                nota = "EPSI05 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSI05_NO_PYP
                nota = "EPSI05 + NO PyP"
        
        elif codigo_entidad_str == "EPSIC5":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSIC5_PYP
                nota = "EPSIC5 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSIC5_NO_PYP
                nota = "EPSIC5 + NO PyP"
        
        elif codigo_entidad_str == "RES001":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_RES001_PYP
                nota = "RES001 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_RES001_NO_PYP
                nota = "RES001 + NO PyP"
        
        elif codigo_entidad_str == "ESS062":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESS062_PYP
                nota = "ESS062 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESS062_NO_PYP
                nota = "ESS062 + NO PyP"
        
        elif codigo_entidad_str == "ESSC62":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESSC62_PYP
                nota = "ESSC62 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_ESSC62_NO_PYP
                nota = "ESSC62 + NO PyP"
        
        elif codigo_entidad_str == "0001":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_0001_PYP
                nota = "0001 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_0001_NO_PYP
                nota = "0001 + NO PyP"
        
        elif codigo_entidad_str == "EPSS005":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSS005_PYP
                nota = "EPSS005 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSS005_NO_PYP
                nota = "EPSS005 + NO PyP"
        
        elif codigo_entidad_str == "EPSC005":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSC005_PYP
                nota = "EPSC005 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_EPSC005_NO_PYP
                nota = "EPSC005 + NO PyP"
        
        elif codigo_entidad_str == "86" and codigo_str not in PYP_CUPS_CODES:
            # Solo aplica para NO PyP (PyP no tiene regla)
            ide_esperado_set = IDE_CONTRATO_MULTIPLE_86_NO_PYP
            nota = "86 + NO PyP"
        
        elif codigo_entidad_str == "86000":
            if codigo_str in PYP_CUPS_CODES:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_86000_PYP
                nota = "86000 + PyP"
            else:
                ide_esperado_set = IDE_CONTRATO_MULTIPLE_86000_NO_PYP
                nota = "86000 + NO PyP"
        
        else:
            # Entidad no tiene regla específica, skip
            continue
        
        if ide_str not in ide_esperado_set:
            problemas.append({
                "factura": factura_str,
                "codigo": codigo_str,
                "cod_entidad": codigo_entidad_str,
                "ide_actual": ide_str,
                "ide_deberia": " o ".join(sorted(ide_esperado_set)),
                "nota": nota,
            })
            logger.debug(
                "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado uno de: %s)",
                row,
                codigo_entidad_str,
                codigo_str,
                ide_str,
                ide_esperado_set,
            )
    
    logger.info("IDE Contrato - Filas procesadas: %d, Problemas encontrados: %d", row - 1, len(problemas))
    return problemas


def _detect_centro_costo_odontologia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    profesional_dias: dict[str, list[int]] | None = None,
    permitir_todos_centros: bool = False,
    centros_validos: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Detecta facturas con problemas de centro de costo en Odontología.
    
    Dos modos de operación:
    
    1. permitir_todos_centros = True (validación desactivada):
       - Solo se permiten: "ODONTOLOGIA" y "SERVICIOS ODONTOLOGIA -EXTRAMURALES"
       - Cualquier otro centro es error
    
    2. permitir_todos_centros = False (validación activada con días):
       - Por defecto: Centro debe ser "ODONTOLOGIA"
       - Si el profesional (por identificación) tiene días seleccionados en el calendario
         Y la fecha de factura coincide con uno de esos días -> Centro debe ser "SERVICIOS ODONTOLOGIA -EXTRAMURALES"
       - Si el centro es diferente a los dos permitidos Y no coincide con fecha+día -> ERROR
       - Si el centro es diferente a los dos permitidos Y coincide con fecha+día -> ERROR
       
    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas
        profesional_dias: Dict {identificacion: [dias]} con los días seleccionados por profesional
        permitir_todos_centros: Si True, solo permite ODONTOLOGIA y EXTRAMURAL (sin validación por fecha)
        centros_validos: Lista personalizada de centros válidos (por defecto: Odontología y Extramural)
    
    Returns:
        Lista de dicts con keys: "factura", "centro_actual", "centro_deberia", "profesional", "fec_factura"
    """
    problemas = []
    
    # Valores por defecto
    if centros_validos is None:
        centros_validos = [CENTRO_COSTO_ODONTOLOGIA, CENTRO_COSTO_EXTRAMURAL]
    
    num_fact_idx = indices["numero_factura"]
    centro_costo_idx = indices["centro_costo"]
    fec_factura_idx = indices["fec_factura"]
    profesional_id_idx = indices["profesional_identificacion"]
    
    logger.info("Índices para validación centro costo - numero_fact: %s, centro_costo: %s, fec_factura: %s, profesional_id: %s",
                num_fact_idx, centro_costo_idx, fec_factura_idx, profesional_id_idx)
    
    if num_fact_idx is None or centro_costo_idx is None:
        logger.warning("Columnas necesarias no encontradas para validar centro de costo")
        return []
    
    for row in range(2, data_sheet.max_row + 1):
        # Obtener datos de la fila
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        centro_costo = data_sheet.cell(row=row, column=centro_costo_idx + 1).value
        centro_costo_str = str(centro_costo).strip().upper() if centro_costo else ""
        
        # Obtener fecha de factura
        fec_factura = data_sheet.cell(row=row, column=fec_factura_idx + 1).value if fec_factura_idx is not None else None
        dia_factura = None
        fec_factura_dt = None  # datetime object para usar en strftime
        
        # Debug: log de la fecha cruda
        if row <= 3:  # Solo las primeras 3 filas
            logger.debug("Fila %s (%s) - fec_factura raw: %s (type: %s)", row, factura_str, fec_factura, type(fec_factura).__name__)
        
        if fec_factura:
            try:
                if isinstance(fec_factura, datetime):
                    dia_factura = fec_factura.day
                    fec_factura_dt = fec_factura
                elif isinstance(fec_factura, (int, float)):
                    # Puede ser un número de serie de Excel
                    try:
                        from datetime import datetime as dt, timedelta
                        excel_date = int(fec_factura)
                        dia_factura = (dt(1900, 1, 1) + timedelta(days=excel_date - 1)).day
                        fec_factura_dt = (dt(1900, 1, 1) + timedelta(days=excel_date - 1))
                    except:
                        pass
                elif isinstance(fec_factura, str):
                    # Intentar múltiples formatos de fecha
                    formatos = [
                        "%Y-%m-%d %H:%M:%S",  # 2026-04-06 06:40:14
                        "%Y-%m-%d",            # 2026-04-06
                        "%d/%m/%Y", "%d-%m-%Y",
                        "%d-%b-%Y", "%b %d, %Y", "%d %b %Y",
                        "%m/%d/%Y", "%Y/%m/%d",
                        "%d.%m.%Y", "%Y.%m.%d",
                    ]
                    for fmt in formatos:
                        try:
                            fec_factura_dt = datetime.strptime(fec_factura.strip(), fmt)
                            dia_factura = fec_factura_dt.day
                            if row <= 3:
                                logger.debug("Fila %s (%s) - fecha parseada '%s' con formato '%s', día: %s", 
                                            row, factura_str, fec_factura, fmt, dia_factura)
                            break
                        except ValueError:
                            continue
                    if dia_factura is None and row <= 3:
                        logger.debug("Fila %s (%s) - NO se pudo parsear fecha: '%s'", row, factura_str, fec_factura)
            except Exception as e:
                if row <= 3:
                    logger.debug("Fila %s (%s) - error parseando fecha '%s': %s", row, factura_str, fec_factura, e)
        
        # Obtener identificación del profesional
        profesional_id = None
        if profesional_id_idx is not None:
            profesional_id = data_sheet.cell(row=row, column=profesional_id_idx + 1).value
            if profesional_id:
                profesional_id = str(profesional_id).strip()
        
        # Debug: log de la identificación del profesional
        if row <= 3:
            logger.debug("Fila %s (%s) - profesional_id raw: %s (index: %s)", row, factura_str, profesional_id, profesional_id_idx)
        
        # Determinar centro correcto según el modo
        if permitir_todos_centros:
            # Modo simple: solo permitir los dos centros válidos
            centro_correcto = None  # No hay uno específico, cualquiera de los dos es válido
        else:
            # Modo con validación por fecha
            dias_profesional = []
            if profesional_dias and profesional_id and profesional_id in profesional_dias:
                dias_profesional = profesional_dias[profesional_id]
                if row <= 3:
                    logger.debug("Fila %s (%s) - profesional_id: %s, dias_profesional: %s, dia_factura: %s", 
                               row, factura_str, profesional_id, dias_profesional, dia_factura)
            
            if dia_factura and dias_profesional and dia_factura in dias_profesional:
                centro_correcto = CENTRO_COSTO_EXTRAMURAL
            else:
                centro_correcto = CENTRO_COSTO_ODONTOLOGIA
        
        # Validar - usar centros_validos del parámetro (con valor por defecto)
        if centros_validos is None:
            centros_validos = [CENTRO_COSTO_ODONTOLOGIA, CENTRO_COSTO_EXTRAMURAL]
        
        # Debug: mostrar info completa para filas con problemas
        if row == 133 or row == 259 or row == 3:
            dias_profesional_debug = dias_profesional if permitir_todos_centros is False else "N/A (modo simple)"
            logger.debug("Fila %s (%s) - DEBUG COMPLETO: profesional_id=%s, fec_factura=%s, dia_factura=%s, dias_profesional=%s, centro_costo_str=%s, centro_correcto=%s, permitir_todos_centros=%s",
                        row, factura_str, profesional_id, fec_factura, dia_factura, dias_profesional_debug, centro_costo_str, centro_correcto, permitir_todos_centros)
        
        # Caso 1: Centro no está en la lista de válidos → siempre error
        if centro_costo_str not in centros_validos:
            problema = {
                "factura": factura_str,
                "centro_actual": centro_costo_str,
                "centro_deberia": centro_correcto if centro_correcto else "ODONTOLOGIA o SERVICIOS ODONTOLOGIA -EXTRAMURALES",
                "profesional": profesional_id or "",
                "fec_factura": fec_factura_dt.strftime("%Y-%m-%d") if fec_factura_dt else "",
            }
            problemas.append(problema)
            logger.debug(
                "Fila %s: Centro de costo inválido (%s, debería ser uno de: %s)",
                row,
                centro_costo_str,
                centros_validos,
            )
        # Caso 2: Validación activada Y centro no coincide con el esperado según fecha
        elif not permitir_todos_centros and centro_correcto and centro_costo_str != centro_correcto:
            problema = {
                "factura": factura_str,
                "centro_actual": centro_costo_str,
                "centro_deberia": centro_correcto,
                "profesional": profesional_id or "",
                "fec_factura": fec_factura_dt.strftime("%Y-%m-%d") if fec_factura_dt else "",
            }
            problemas.append(problema)
            logger.debug(
                "Fila %s: Centro de costo no coincide con fecha (%s, debería ser %s para día %s)",
                row,
                centro_costo_str,
                centro_correcto,
                dia_factura,
            )
    
    return problemas


def _get_codigos_no_en_db_ess118(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, str]]:
    """
    Retorna lista de problemas de códigos CUPS que NO están en la DB.
    
    Regla: IDE Contrato = 969 Y Código Tipo Procedimiento no es 9,12,13 
           Y código NO está en tabla procedimiento → ERROR
    
    Nota: Se consulta la tabla procedimiento de PostgreSQL (no la DB externa).
    
    Returns:
        Lista de dicts con keys: "factura", "codigo", "procedimiento", "entidad"
    """
    # Cargar códigos válidos de la tabla procedimiento relacionados con nota_hoja = 3
    from app.database import SessionLocal
    from app.models import Procedimiento, NotasTecnicas
    
    db = SessionLocal()
    try:
        # Obtener cups de procedimiento relacionados con id_nota_hoja = 3
        cups_validos = set(
            row.cups 
            for row in db.query(Procedimiento.cups)
            .join(NotasTecnicas, NotasTecnicas.id_procedimiento == Procedimiento.id)
            .filter(NotasTecnicas.id_nota_hoja == 3)
            .distinct()
            .all()
        )
    finally:
        db.close()
    
    if not cups_validos:
        logger.warning("No hay códigos en tabla procedimiento para nota_hoja=3")
        return []
    
    logger.info("Códigos válidos (nota_hoja=3): %d", len(cups_validos))
    
    codigo_idx = indices.get("codigo")
    ide_contrato_idx = indices.get("ide_contrato")
    codigo_tipo_proc_idx = indices.get("codigo_tipo_procedimiento")
    num_fact_idx = indices.get("numero_factura")
    proc_idx = indices.get("procedimiento")
    codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
    
    if codigo_idx is None:
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        # Verificar IDE Contrato = 969
        ide_contrato = None
        if ide_contrato_idx is not None:
            ide_contrato = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        
        ide_str = str(ide_contrato).strip() if ide_contrato else ""
        
        # Solo procesar si IDE = 969
        if ide_str != "969":
            continue
        
        # Excluir Código Tipo Procedimiento = 09, 12, 13
        if codigo_tipo_proc_idx is not None:
            codigo_tipo = data_sheet.cell(row=row, column=codigo_tipo_proc_idx + 1).value
            if codigo_tipo and str(codigo_tipo).strip() in ["09", "12", "13"]:
                continue
        
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        if not codigo:
            continue
        
        codigo_str = str(codigo).strip()
        
        # Verificar si existe en la tabla procedimiento
        if codigo_str not in cups_validos:
            # Agregar problema individual por cada fila
            factura = ""
            if num_fact_idx is not None:
                factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value or ""
            
            procedimiento = ""
            if proc_idx is not None:
                procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value or ""
            
            entidad = ""
            if codigo_entidad_idx is not None:
                entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value or ""
            
            problemas.append({
                "factura": str(factura),
                "codigo": codigo_str,
                "procedimiento": str(procedimiento),
                "entidad": str(entidad),
            })
    
    return problemas


def _detect_centro_costo_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    problemas_codigos_no_en_db: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    """
    Detecta facturas con problemas de centro de costo, IDE contrato y cups equivalentes:
    -Regla 1: Código=02 Y Laboratorio=No Y Centro != APOYO DIAGNOSTICO-IMAGENOLOGIA
    -Regla 2: Código=14 Y Centro == TRASLADOS
    -Regla 3: Código en (990211, 890205, 890405, 861801) Y Centro != PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN
    -Regla 4: Código en (735301, 90DS02) Y Centro != QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO
    -Regla 5: Código en lista laboratorio Y Entidad=ESS118 Y Tipo=Intramural Y Centro != LABORATORIO CLINICO
    -Regla nueva: Si código NO está en DB Y Entidad=ESS118 Y IDE=969 -> ERROR
    -Cups equivalentes: Código=890201 Y Cód. Equivalente CUPS=890201 -> ERROR
    
    Args:
        data_sheet: Hoja de datos
        indices: Índices de columnas
        problemas_codigos_no_en_db: Lista de problemas de códigos no en la DB (para regla 969)
    
    Returns:
        Tuple de tres listas:
        - problemas_centros: lista de dicts con keys: "factura", "centro_actual", "centro_deberia"
        - problemas_ide_contrato: lista de dicts con keys: "factura", "ide_contrato_actual", "ide_contrato_deberia"
        - problemas_cups_equivalentes: lista de dicts con keys: "factura", "codigo", "codigo_equiv"
    """
    # Crear set de códigos para búsquedas rápidas
    codigos_no_en_db_set = set()
    if problemas_codigos_no_en_db:
        codigos_no_en_db_set = {item["codigo"] for item in problemas_codigos_no_en_db}
    from app.constants import (
        CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO,
        CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS,
        LABORATORIO_NO,
        CENTRO_COSTO_APOYO_DIAGNOSTICO,
        CENTRO_COSTO_TRASLADOS,
        CODIGOS_PYP_URGENCIAS,
        CENTRO_COSTO_PYP_URGENCIAS,
        CODIGOS_QUIROFANO_URGENCIAS,
        CENTRO_COSTO_QUIROFANO_URGENCIAS,
        CODIGOS_LABORATORIO_URGENCIAS,
        CENTRO_COSTO_LABORATORIO_URGENCIAS,
        CODIGO_IDE_CONTRATO_URGENCIAS,
        ENTIDAD_IDE_CONTRATO_URGENCIAS,
        IDE_CONTRATO_REQUERIDO_URGENCIAS,
        CODIGO_IDE_CONTRATO_861801_EPSI05,
        ENTIDAD_IDE_CONTRATO_861801_EPSI05,
        IDE_CONTRATO_REQUERIDO_861801_EPSI05,
        CODIGO_IDE_CONTRATO_890405_EPSI05,
        ENTIDAD_IDE_CONTRATO_890405_EPSI05,
        IDE_CONTRATO_CON_INSERCION_890405_EPSI05,
        IDE_CONTRATO_SIN_INSERCION_890405_EPSI05,
CODIGO_CUPS_HOSPITALIZACION,
        CENTRO_COSTO_HOSPITALIZACION_ESTANCIA,
        CODIGO_CUPS_URGENCIAS,
        CENTRO_COSTO_URGENCIAS,
        CODIGO_CUPS_URGENCIAS_861101,
    )
    
    # Debug: mostrar los índices detectados
    logger.info("Indices detectados para urgencias: %s", indices)
    
    num_fact_idx = indices["numero_factura"]
    ident_idx = indices.get("identificacion")
    codigo_tipo_proc_idx = indices.get("codigo_tipo_procedimiento")
    codigo_idx = indices.get("codigo")
    codigo_equiv_idx = indices.get("codigo_equiv")
    laboratorio_idx = indices.get("laboratorio")
    centro_costo_idx = indices.get("centro_costo")
    codigo_entidad_cobrar_idx = indices.get("codigo_entidad_cobrar")
    entidad_cobrar_idx = indices.get("entidad_cobrar")
    tipo_factura_descripcion_idx = indices.get("tipo_factura_descripcion")
    ide_contrato_idx = indices.get("ide_contrato")
    proc_idx = indices.get("procedimiento")
    
    logger.info("Índices relevantes - codigo_tipo_proc: %s, codigo: %s, codigo_equiv: %s, laboratorio: %s, centro_costo: %s, ide_contrato: %s, codigo_entidad: %s",
                codigo_tipo_proc_idx, codigo_idx, codigo_equiv_idx, laboratorio_idx, centro_costo_idx, ide_contrato_idx, codigo_entidad_cobrar_idx)
    
    if num_fact_idx is None:
        return []
    
    # Si no tenemos las columnas necesarias, no podemos validar
    if codigo_tipo_proc_idx is None and laboratorio_idx is None and centro_costo_idx is None:
        logger.warning("No se encontraron columnas necesarias para validación de urgencias")
        return [], [], []
    
    problemas_centros = []
    problemas_ide_contrato = []
    problemas_cups_equivalentes = []
    # NO usamos set para centros de costos - cada fila con error se incluye (permite múltiples errores por factura en diferentes procedimientos)
    
    # ----- Pre-recorrido:收集 identificaciones con código 861801
    identificaciones_con_insercion = set()
    if ident_idx is not None and codigo_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero_ident = data_sheet.cell(row=row, column=ident_idx + 1).value
            codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
            if numero_ident and codigo:
                ident_normalized = str(numero_ident).strip()
                codigo_normalized = str(codigo).strip()
                if codigo_normalized == CODIGO_INSERCION_BUSCAR:
                    identificaciones_con_insercion.add(ident_normalized)
    
    # ----- Pre-recorrido:收集 identificaciones con código 890405 (para ESSC62)
    identificaciones_con_890405 = set()
    if ident_idx is not None and codigo_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero_ident = data_sheet.cell(row=row, column=ident_idx + 1).value
            codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
            if numero_ident and codigo:
                ident_normalized = str(numero_ident).strip()
                codigo_normalized = str(codigo).strip()
                if codigo_normalized == CODIGO_A_BUSCAR_890405_ESSC62:
                    identificaciones_con_890405.add(ident_normalized)
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        # Obtener valores de las columnas
        codigo_tipo_proc = None
        if codigo_tipo_proc_idx is not None:
            codigo_tipo_proc = data_sheet.cell(row=row, column=codigo_tipo_proc_idx + 1).value
        
        codigo = None
        if codigo_idx is not None:
            codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        
        codigo_equiv = None
        if codigo_equiv_idx is not None:
            codigo_equiv = data_sheet.cell(row=row, column=codigo_equiv_idx + 1).value
        
        laboratorio = None
        if laboratorio_idx is not None:
            laboratorio = data_sheet.cell(row=row, column=laboratorio_idx + 1).value
        
        centro_costo = None
        if centro_costo_idx is not None:
            centro_costo = data_sheet.cell(row=row, column=centro_costo_idx + 1).value
        
        codigo_entidad_cobrar = None
        if codigo_entidad_cobrar_idx is not None:
            codigo_entidad_cobrar = data_sheet.cell(row=row, column=codigo_entidad_cobrar_idx + 1).value
        
        entidad_cobrar = None
        if entidad_cobrar_idx is not None:
            entidad_cobrar = data_sheet.cell(row=row, column=entidad_cobrar_idx + 1).value
        
        tipo_factura_descripcion = None
        if tipo_factura_descripcion_idx is not None:
            tipo_factura_descripcion = data_sheet.cell(row=row, column=tipo_factura_descripcion_idx + 1).value
        
        ide_contrato = None
        if ide_contrato_idx is not None:
            ide_contrato = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        
        numero_identificacion = None
        if ident_idx is not None:
            numero_identificacion = data_sheet.cell(row=row, column=ident_idx + 1).value
        
        procedimiento = None
        if proc_idx is not None:
            procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value
        
        # Normalizar strings (definir ANTES de usar)
        codigo_str = str(codigo_tipo_proc).strip() if codigo_tipo_proc else ""
        codigo_excluir = str(codigo).strip() if codigo else ""
        codigo_equiv_str = str(codigo_equiv).strip() if codigo_equiv else ""
        laboratorio_str = str(laboratorio).strip() if laboratorio else ""
        centro_costo_str = str(centro_costo).strip() if centro_costo else ""
        codigo_entidad_str = str(codigo_entidad_cobrar).strip() if codigo_entidad_cobrar else ""
        entidad_cobrar_str = str(entidad_cobrar).strip() if entidad_cobrar else ""
        tipo_factura_str = str(tipo_factura_descripcion).strip() if tipo_factura_descripcion else ""
        ide_contrato_str = str(ide_contrato).strip() if ide_contrato else ""
        ident_str = str(numero_identificacion).strip() if numero_identificacion else ""
        proc_str = str(procedimiento).strip() if procedimiento else ""
        
        # Debug: log de las primeras filas para ver qué valores vienen
        if row <= 5:
            logger.info("Fila %s DEBUG: factura=%s, codigo_tipo_proc=%s, codigo=%s, laboratorio=%s, centro_costo=%s, ide_contrato=%s",
                       row, factura_str, repr(codigo_tipo_proc), repr(codigo), repr(laboratorio), repr(centro_costo), repr(ide_contrato))
        
        # ----- Regla 1: Código=02 + Laboratorio=No + Centro !=IMAGENOLOGIA
        # (Independiente - con excepciones propias: no aplica a ciertos códigos)
        regla_1_activa = (
            codigo_str == CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO and
            laboratorio_str == LABORATORIO_NO
        )
        # Excepciones específicas de la Regla 1 (no afecta otras reglas)
        es_exceptuado = codigo_excluir in CODIGOS_EXCEPTUADOS
        if regla_1_activa and not es_exceptuado and centro_costo_str != CENTRO_COSTO_APOYO_DIAGNOSTICO:
            problemas_centros.append({
                "factura": factura_str,
                "centro_actual": centro_costo_str,
                "centro_deberia": CENTRO_COSTO_APOYO_DIAGNOSTICO,
                "codigo": codigo_excluir,
                "procedimiento": proc_str,
            })
            logger.info(
                "REGLA1: Fila %s: Código=02, Lab=No, Centroincorrecto (Centro: '%s', CódigoProc: '%s')",
                row,
                centro_costo,
                codigo_excluir,
            )
        
        # ----- Regla 2: Código=14 + Centro Distinto a TRASLADOS
        # (Independiente)
        if codigo_str == CODIGO_TIPO_PROCEDIMIENTO_TRASLADOS:
            if centro_costo_str != CENTRO_COSTO_TRASLADOS:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_TRASLADOS,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
                logger.info(
                    "REGLA2: Fila %s: Código=14, Centrodistinto a TRASLADOS",
                    row,
                )
        
        # ----- Regla 3: Código en (990211, 890205, 890405, 861801) + Centro != PROCEDIMIENTO PYP
        # (Independiente)
        if codigo_excluir in CODIGOS_PYP_URGENCIAS:
            if centro_costo_str != CENTRO_COSTO_PYP_URGENCIAS:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_PYP_URGENCIAS,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
                logger.info(
                    "REGLA3: Fila %s: Código=%s, Centro incorrecto (Centro: '%s')",
                    row,
                    codigo_excluir,
                    centro_costo_str,
                )
        
        # ----- Regla 4: Código en (735301, 90DS02) + Centro != QUIRÓFANOS
        # (Independiente)
        if codigo_excluir in CODIGOS_QUIROFANO_URGENCIAS:
            if centro_costo_str != CENTRO_COSTO_QUIROFANO_URGENCIAS:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_QUIROFANO_URGENCIAS,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
                logger.info(
                    "REGLA4: Fila %s: Código=%s, Centro incorrecto (Centro: '%s')",
                    row,
                    codigo_excluir,
                    centro_costo_str,
                )
        
        # ----- Regla 5: Código en lista laboratorio + Entidad=ESS118 + Tipo=Intramural -> Centro LABORATORIO
        # (Independiente)
        if codigo_excluir in CODIGOS_LABORATORIO_URGENCIAS:
            if codigo_entidad_str == "ESS118" and tipo_factura_str == "Intramural":
                centro_valido = centro_costo_str in (
                    CENTRO_COSTO_LABORATORIO_URGENCIAS,
                    f"{CENTRO_COSTO_LABORATORIO_URGENCIAS}.",
                )
                if not centro_valido:
                    problemas_centros.append({
                        "factura": factura_str,
                        "centro_actual": centro_costo_str,
                        "centro_deberia": CENTRO_COSTO_LABORATORIO_URGENCIAS,
                        "codigo": codigo_excluir,
                        "procedimiento": proc_str,
                    })
                    logger.info(
                        "REGLA5: Fila %s: Código=%s, ESS118+Intramural, Centro incorrecto (Centro: '%s')",
                        row,
                        codigo_excluir,
                        centro_costo_str,
                    )
        
        # ----- Regla nueva: Tipo Factura=Hospitalización + Código CUPS 890601 -> Centro de costo debe ser "HOSPITALIZACIÓN - ESTANCIA GENERAL"
        if codigo_excluir == CODIGO_CUPS_HOSPITALIZACION and tipo_factura_str == "Hospitalización":
            if centro_costo_str != CENTRO_COSTO_HOSPITALIZACION_ESTANCIA:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_HOSPITALIZACION_ESTANCIA,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
        
        # ----- Regla nueva: Código CUPS 890408 -> Centro de costo debe ser "URGENCIAS"
        if codigo_excluir == CODIGO_CUPS_URGENCIAS:
            if centro_costo_str != CENTRO_COSTO_URGENCIAS:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_URGENCIAS,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
        
        # ----- Regla nueva: Código CUPS 861101 -> Centro de costo debe ser "URGENCIAS"
        if codigo_excluir == CODIGO_CUPS_URGENCIAS_861101:
            if centro_costo_str != CENTRO_COSTO_URGENCIAS:
                problemas_centros.append({
                    "factura": factura_str,
                    "centro_actual": centro_costo_str,
                    "centro_deberia": CENTRO_COSTO_URGENCIAS,
                    "codigo": codigo_excluir,
                    "procedimiento": proc_str,
                })
                logger.info(
                    "REGLA (861101): Fila %s: Código=%s, Centro incorrecto (Centro: '%s', Debería: '%s')",
                    row,
                    codigo_excluir,
                    centro_costo_str,
                    CENTRO_COSTO_URGENCIAS,
                )

        # ----- Grupo: Cups equivalentes urgencias
        # ----- Regla: Si Código = 890201 → ERROR (debe usarse 890701)
        if codigo_excluir == "890201":
            logger.warning("DETECTADO cups equiv error: factura=%s, codigo=%s", factura_str, codigo_excluir)
            problemas_cups_equivalentes.append({
                "factura": factura_str,
                "codigo": codigo_excluir,
                "codigo_equiv": "",
                "accion": "Usar 890701",
            })
            logger.info(
                "REGLA (Cups equivalentes): Fila %s: Código=%s -> debe usarse 890701",
                row,
                codigo_excluir,
            )
        
        # ----- Regla 6: Código=906340 + Cód Entidad Cobrar=EPSI05 -> IDE Contrato debe ser 986
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_URGENCIAS and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_URGENCIAS:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_URGENCIAS:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_URGENCIAS,
                })
                logger.info(
                    "REGLA6: Fila %s: Código=%s, Entidad=%s, IDE Contrato incorrecto (IDE: '%s')",
                    row,
                    codigo_excluir,
                    codigo_entidad_str,
                    ide_contrato_str,
                )

        # ----- Regla 7: Código=861801 + Entidad=EPSI05 -> IDE Contrato debe ser 977
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_EPSI05 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_861801_EPSI05:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_EPSI05:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_EPSI05,
                })
                # NO agregamos a set para permitir múltiples errores por factura

        # ----- Regla 8: Código=890405 + Entidad=EPSI05
        # Si identificación tiene código 861801 -> IDE Contrato = 976
        # Si identificación NO tiene código 861801 -> IDE Contrato = 977
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_EPSI05 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_890405_EPSI05:
            # Determinar el IDE Contrato esperado basado en si tiene inserción
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_EPSI05 if ident_str in identificaciones_con_insercion else IDE_CONTRATO_SIN_INSERCION_890405_EPSI05
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "tiene_insercion": ident_str in identificaciones_con_insercion,
                })
                logger.debug(
                    "Fila %s: Código=890405, Entidad=EPSI05, IDE incorrecto (Actual: '%s', Esperado: '%s', Tiene inserción: %s)",
                    row,
                    ide_contrato_str,
                    ide_esperado,
                    ident_str in identificaciones_con_insercion,
                )

        # ----- Regla 9: Código=861801 + Entidad=EPSIC5 (OTHER entity, not EPSI05)
        # IDE Contrato siempre debe ser 979
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_EPSIC5 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_EPSIC5:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_EPSIC5:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_EPSIC5,
                })
                logger.debug(
                    "Fila %s: Código=%s, Entidad=%s, IDE Contrato incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_excluir,
                    codigo_entidad_str,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_EPSIC5,
                )

        # ----- Regla 10: Código=890405 + Entidad=EPSIC5 (OTHER entity, not EPSI05)
        # Si identificación tiene código 861801 -> IDE Contrato = 967
        # Si identificación NO tiene código 861801 -> IDE Contrato = 979
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_EPSIC5 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_890405_EPSIC5:
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_EPSIC5 if ident_str in identificaciones_con_insercion else IDE_CONTRATO_SIN_INSERCION_890405_EPSIC5
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "tiene_insercion": ident_str in identificaciones_con_insercion,
                })
                logger.debug(
                    "Fila %s: Código=890405, Entidad=EPSIC5, IDE incorrecto (Actual: '%s', Esperado: %s, Tiene inserción: %s)",
                    row,
                    ide_contrato_str,
                    ide_esperado,
                    ident_str in identificaciones_con_insercion,
                )

        # ----- Regla 12: Cód Entidad Cobrar=ESS118 + Código=735301 -> IDE Contrato debe ser 970
        # Urgencias y Contratos
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_735301 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_735301:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_735301:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_735301,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_735301,
                )

        # ----- Regla 13: Cód Entidad Cobrar=ESS118 + Código=906340 -> IDE Contrato debe ser 839
        # Urgencias y Contratos
        # (Independiente - NO depende de otras reglas)
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340_ESS118 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_906340_ESS118:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340_ESS118:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340_ESS118,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_906340_ESS118,
                )

        # ----- Regla 14: Cód Entidad Cobrar=ESS118 + Código=861801 -> IDE Contrato debe ser 974
        # Urgencias y Contratos
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_ESS118 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_861801_ESS118:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_ESS118:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_ESS118,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801_ESS118,
                )

        # ----- Regla 15: Cód Entidad Cobrar=ESS118 + Código=890405 -> IDE Contrato 977 o 973 según inserción
        # Urgencias y Contratos - si la identificación tiene código 861801 en otra fila
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_ESS118 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_890405_ESS118:
            # Determinar IDE esperado según si tiene inserción
            tiene_insercion = ident_str in identificaciones_con_insercion
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_ESS118 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_ESS118
            
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "nota": "Tiene inserción 861801" if tiene_insercion else "Sin inserción 861801",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Inserción: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    ide_esperado,
                    tiene_insercion,
                )

        # ----- Regla 18: Cód Entidad Cobrar=ESSC18 + Código=906340 -> IDE Contrato debe ser 842
        # Urgencias y Contratos
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340_ESSC18 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESSC18:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340_ESSC18:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340_ESSC18,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_906340_ESSC18,
                )

        # ----- Regla 17: Cód Entidad Cobrar=ESSC18 + Código=861801 -> IDE Contrato debe ser 975
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_ESSC18 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESSC18:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_ESSC18:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_ESSC18,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801_ESSC18,
                )

        # ----- Regla 18: Cód Entidad Cobrar=ESSC18 + Código=890405 -> IDE Contrato según inserción
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_ESSC18 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESSC18:
            tiene_insercion = ident_str in identificaciones_con_insercion
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_ESSC18 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_ESSC18
            
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "nota": "Tiene inserción 861801" if tiene_insercion else "Sin inserción 861801",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Inserción: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    ide_esperado,
                    tiene_insercion,
                )

        # ----- Regla 19: Cód Entidad Cobrar=EPS037 + Código=906340 -> IDE Contrato debe ser 962
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340_EPS037 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_EPS037:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340_EPS037:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340_EPS037,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_906340_EPS037,
                )

        # ----- Regla 20: Cód Entidad Cobrar=EPS037 + Código=861801 -> IDE Contrato debe ser 961
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_EPS037 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_EPS037:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_EPS037:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_EPS037,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801_EPS037,
                )

        # ----- Regla 21: Cód Entidad Cobrar=EPS037 + Código=890405 -> IDE Contrato según inserción
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_EPS037 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_EPS037:
            tiene_insercion = ident_str in identificaciones_con_insercion
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_EPS037 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_EPS037
            
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "nota": "Tiene inserción 861801" if tiene_insercion else "Sin inserción 861801",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Inserción: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    ide_esperado,
                    tiene_insercion,
                )

        # ----- Regla 22: Código 906340 + Cód Entidad Cobrar=EPSS41 -> IDE 959
        # SOLO usa "Cód Entidad Cobrar", NO "Entidad Cobrar"
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340_EPSS41:
            if codigo_entidad_str == "EPSS41":
                if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340_EPSS41:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "codigo_entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340_EPSS41,
                    })
                    logger.debug(
                        "Fila %s: Cód Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                        row,
                        codigo_entidad_str,
                        codigo_excluir,
                        ide_contrato_str,
                        IDE_CONTRATO_REQUERIDO_906340_EPSS41,
                    )

        # ----- Regla 23: Código 861801 + Cód Entidad Cobrar=EPSS41 -> IDE 958
        # SOLO usa "Cód Entidad Cobrar", NO "Entidad Cobrar"
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_EPSS41:
            if codigo_entidad_str == "EPSS41":
                if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_EPSS41:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "codigo_entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_EPSS41,
                    })
                    logger.debug(
                        "Fila %s: Cód Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                        row,
                        codigo_entidad_str,
                        codigo_excluir,
                        ide_contrato_str,
                        IDE_CONTRATO_REQUERIDO_861801_EPSS41,
                    )

        # ----- Regla 24: Código 890405 + Cód Entidad Cobrar=EPSS41 -> IDE según inserción
        # SOLO usa "Cód Entidad Cobrar", NO "Entidad Cobrar"
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_EPSS41:
            if codigo_entidad_str == "EPSS41":
                tiene_insercion = ident_str in identificaciones_con_insercion
                ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_EPSS41 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_EPSS41
                
                if ide_contrato_str != ide_esperado:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "codigo_entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": ide_esperado,
                        "nota": "Tiene inserción 861801" if tiene_insercion else "Sin inserción 861801",
                    })
                    logger.debug(
                        "Fila %s: Cód Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Inserción: %s)",
                        row,
                        codigo_entidad_str,
                        codigo_excluir,
                        ide_contrato_str,
                        ide_esperado,
                        tiene_insercion,
                    )

        # ----- Regla 25: ESS062 + Código 861801 -> IDE Contrato debe ser 922
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_ESS062 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESS062:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_ESS062:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_ESS062,
                    "nota": "ESS062 + Código 861801 -> IDE 922",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801_ESS062,
                )

        # ----- Regla 26: ESS062 + Código 890405 -> IDE Contrato según inserción
        # Si identificación tiene código 861801 -> IDE 921
        # Si identificación NO tiene código 861801 -> IDE 922
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_ESS062 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESS062:
            tiene_insercion = ident_str in identificaciones_con_insercion
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_ESS062 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_ESS062
            
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "nota": "ESS062 + 890405 -> IDE 921 (con 861801)" if tiene_insercion else "ESS062 + 890405 -> IDE 922 (sin 861801)",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Inserción: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    ide_esperado,
                    tiene_insercion,
                )

        # ----- Regla 27: ESSC62 + Código 861801 -> IDE Contrato debe ser 863
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_ESSC62 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESSC62:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_ESSC62:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_ESSC62,
                    "nota": "ESSC62 + Código 861801 -> IDE 863",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801_ESSC62,
                )

        # ----- Regla 28: ESSC62 + Código 890405 -> IDE Contrato según si tiene 890405
        # Si identificación tiene código 890405 en otro procedimiento -> IDE 862
        # Si identificación NO tiene código 890405 -> IDE 863
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_ESSC62 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESSC62:
            tiene_890405 = ident_str in identificaciones_con_890405
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_ESSC62 if tiene_890405 else IDE_CONTRATO_SIN_INSERCION_890405_ESSC62
            
            if ide_contrato_str != ide_esperado:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": ide_esperado,
                    "nota": "ESSC62 + 890405 -> IDE 862 (con 890405)" if tiene_890405 else "ESSC62 + 890405 -> IDE 863 (sin 890405)",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s, Tiene 890405: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    ide_esperado,
                    tiene_890405,
                )

        # ----- Regla 29: Entidad -> IDE Contrato (mapeo directo, sin importar código)
        # Valida que cada entidad tenga su contrato específico
        # EXCLUYE entidades con múltiples contratos válidos (Regla 30)
        if codigo_entidad_str and codigo_entidad_str in URGENCIA_ENTIDAD_CONTRATO:
            if codigo_entidad_str in URGENCIA_ENTIDAD_MULTIPLE_CONTRATO:
                # Esta entidad se maneja en la regla de múltiples contratos, skip
                pass
            else:
                ide_contrato_requerido = URGENCIA_ENTIDAD_CONTRATO[codigo_entidad_str]
                if ide_contrato_str != ide_contrato_requerido:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": ide_contrato_requerido,
                        "nota": "Regla Entidad->Contrato",
                    })
                    logger.debug(
                        "Fila %s: Entidad=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                        row,
                        codigo_entidad_str,
                        ide_contrato_str,
                        ide_contrato_requerido,
                    )

        # ----- Regla 30: Entidad con múltiples contratos válidos
        if codigo_entidad_str and codigo_entidad_str in URGENCIA_ENTIDAD_MULTIPLE_CONTRATO:
            contratos_validos = URGENCIA_ENTIDAD_MULTIPLE_CONTRATO[codigo_entidad_str]
            if ide_contrato_str not in contratos_validos:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": f"uno de: {contratos_validos}",
                    "nota": "Entidad con múltiples contratos válidos",
                })
                logger.debug(
                    "Fila %s: Entidad=%s, IDE incorrecto (Actual: '%s', Esperado uno de: %s)",
                    row,
                    codigo_entidad_str,
                    ide_contrato_str,
                    contratos_validos,
                )

    return problemas_centros, problemas_ide_contrato, problemas_cups_equivalentes


def _log_verificacion_codigos_ess118(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """
    Verifica códigos CUPS con IDE Contrato = 969 contra la tabla procedimiento.
    
    Muestra en el log todos los códigos que NO se encuentran en la tabla procedimiento.
    
    Returns:
        Lista de códigos no encontrados en la DB
    """
    # Cargar códigos válidos de la tabla procedimiento relacionados con nota_hoja = 3
    from app.database import SessionLocal
    from app.models import Procedimiento, NotasTecnicas
    
    db = SessionLocal()
    try:
        cups_validos = set(
            row.cups 
            for row in db.query(Procedimiento.cups)
            .join(NotasTecnicas, NotasTecnicas.id_procedimiento == Procedimiento.id)
            .filter(NotasTecnicas.id_nota_hoja == 3)
            .distinct()
            .all()
        )
    finally:
        db.close()
    
    if not cups_validos:
        logger.warning("No hay códigos en tabla procedimiento para nota_hoja=3")
        return set()
    
    # Usar claves del diccionario indices
    codigo_idx = indices.get("codigo")
    ide_contrato_idx = indices.get("ide_contrato")
    codigo_tipo_proc_idx = indices.get("codigo_tipo_procedimiento")
    
    if codigo_idx is None:
        logger.warning("No hay índice de Código")
        return set()
    
    # Collect códigos únicos con IDE = 969
    codigos_ide_969 = set()
    
    for row in range(2, data_sheet.max_row + 1):
        # Verificar IDE = 969
        ide_contrato = None
        if ide_contrato_idx is not None:
            ide_contrato = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        
        ide_str = str(ide_contrato).strip() if ide_contrato else ""
        
        if ide_str != "969":
            continue
        
        # Verificar excepción: Código Tipo Procedimiento = 09, 12, 13 → no incluir
        codigo_tipo = None
        if codigo_tipo_proc_idx:
            codigo_tipo = data_sheet.cell(row=row, column=codigo_tipo_proc_idx + 1).value
        
        if codigo_tipo and str(codigo_tipo).strip() in ["09", "12", "13"]:
            continue
        
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        if codigo:
            codigos_ide_969.add(str(codigo).strip())
    
    if not codigos_ide_969:
        return set()
    
    # Verificar cada código contra la tabla procedimiento
    codigos_no_encontrados = set()
    
    for codigo in codigos_ide_969:
        if codigo not in cups_validos:
            codigos_no_encontrados.add(codigo)
    
    return codigos_no_encontrados


def _log_resumen_ide_contrato(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> None:
    """
    Log de resumen de valores únicos de código y entidad para debug de reglas IDE Contrato.
    """
    codigo_idx = indices.get("codigo")
    codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
    ide_contrato_idx = indices.get("ide_contrato")
    
    if codigo_idx is None or codigo_entidad_idx is None:
        logger.warning("No hay índices de código o entidad para resumir")
        return
    
    codigos_set = set()
    entidades_set = set()
    ide_contratos_set = set()
    
    for row in range(2, min(data_sheet.max_row + 1, 500)):  # Limitado a primeras 500 filas
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value
        
        if codigo:
            codigos_set.add(str(codigo).strip())
        if entidad:
            entidades_set.add(str(entidad).strip())
        
        if ide_contrato_idx is not None:
            ide = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
            if ide:
                ide_contratos_set.add(str(ide).strip())
    
    # Mostrar las primeras 10 filas de datos crudos
    logger.warning("=== PRIMERAS FILAS DATOS IDE CONTRATO ===")
    for row in range(2, min(data_sheet.max_row + 1, 12)):
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        codigo_entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value if codigo_entidad_idx is not None else None
        ide = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value if ide_contrato_idx is not None else None
        factura = data_sheet.cell(row=row, column=indices.get("numero_factura", 0) + 1).value if indices.get("numero_factura") is not None else None
        
        logger.warning("Fila %d: Factura=%s, Código=%s, CódEntidad=%s, IDE=%s",
                       row, factura, codigo, codigo_entidad, ide)
    logger.warning("==========================================")
    
    logger.warning("=== RESUMEN DATOS EXCEL PARA REGLAS IDE CONTRATO ===")
    logger.warning("Códigos únicos encontrados (%d): %s", len(codigos_set), sorted(codigos_set))
    logger.warning("Códigos Entidad únicos encontrados (%d): %s", len(entidades_set), sorted(entidades_set))
    logger.warning("IDE Contrato únicos encontrados (%d): %s", len(ide_contratos_set), sorted(ide_contratos_set))
    logger.warning("=========================================================")


def _write_column(sheet: Worksheet, column: int, values: list[str], start_row: int = 2) -> None:
    """Escribe una lista de valores en una columna."""
    for i, value in enumerate(values, start=start_row):
        sheet.cell(row=i, column=column, value=value)


def create_revision_sheet(
    workbook: Workbook,
    data_sheet: Worksheet,
    area: str = AREA_ODONTOLOGIA,
    profesional_dias: dict[str, list[int]] | None = None,
    permitir_todos_centros: bool = False,
) -> dict[str, Any]:
    """
    Crea la hoja Revision con los problemas detectados.
    
    Args:
        workbook: Libro de Excel (debe tener una hoja activa con datos)
        data_sheet: Hoja de datos a analizar
        area: Área del sistema ("odontologia" o "urgencias")
        profesional_dias: Dict {identificacion: [dias]} con días seleccionados por profesional
        permitir_todos_centros: Si True, solo permite ODONTOLOGIA y EXTRAMURAL
    
    Returns:
        Dict con información de los problemas encontrados
    """
    sheet = workbook.create_sheet(title=REVISION_SHEET)
    
    # Insertar fila vacía arriba
    sheet.insert_rows(1)
    
    # Obtener índices de columnas (coincidencia exacta - reporta faltantes)
    headers = [
        data_sheet.cell(row=1, column=col).value
        for col in range(1, data_sheet.max_column + 1)
    ]
    indices, missing_columns = _get_column_indices(headers)
    
    # Si hay columnas faltantes, incluir en el resultado para mostrar al usuario
    if missing_columns:
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
    
    # Seleccionar headers según el área
    if area == AREA_URGENCIAS:
        revision_headers = URGENCIA_REVISION_HEADERS
        header_style = create_urgencia_header_style()
    else:
        revision_headers = REVISION_HEADERS
        header_style = create_header_style()
    
    # Aplicar headers con estilo en fila 2
    for col, header in revision_headers.items():
        cell = sheet.cell(row=2, column=col, value=header)
        cell.font = header_style["font"]
        cell.fill = header_style["fill"]
        cell.border = header_style["border"]
        cell.alignment = header_style["alignment"]
    
# Detectar problemas según el área
    if area == AREA_URGENCIAS:
        # Urgencias: detectar códigos NO en DB para ESS118
        logger.warning("=== VERIFICANDO CÓDIGOS ESS118 CONTRA DB ===")
        problemas_codigos_no_en_db = _get_codigos_no_en_db_ess118(data_sheet, indices)
        
        # Extraer códigos únicos para logging
        codigos_no_en_db_set = {item["codigo"] for item in problemas_codigos_no_en_db}
        
        if problemas_codigos_no_en_db:
            logger.warning("Procedimientos NO encontrados en DB para ESS118 (%d errores): %s",
                        len(problemas_codigos_no_en_db), sorted(codigos_no_en_db_set))
        else:
            logger.warning("Todos los códigos de ESS118 están en DB")
        problemas_centros, problemas_ide_contrato, problemas_cups_equivalentes = _detect_centro_costo_urgencias(
            data_sheet, indices, problemas_codigos_no_en_db
        )
        
        # Formatear para Excel: "FACTURA|CODIGO|PROCEDIMIENTO|CENTRO_ACTUAL|CENTRO_DEBERIA"
        centros_costo_str = [
            f"{item['factura']}|{item.get('codigo', '')}|{item.get('procedimiento', '')}|{item['centro_actual']}|{item['centro_deberia']}"
            for item in problemas_centros
        ]
        
        # Formatear IDE Contrato: incluir todos los datos
        ide_contrato_str = [
            f"{item['factura']}|{item.get('procedimiento', '-')}|{item.get('codigo', '-')}|{item.get('entidad', '-')}|{item['ide_contrato_actual']}|{item['ide_contrato_deberia']}"
            for item in problemas_ide_contrato
        ]
        
        # Formatear Cups equivalentes: "FACTURA|CODIGO|CODIGO_EQUIV|ACCION"
        cups_equiv_str = [
            f"{item['factura']}|{item['codigo']}|{item['codigo_equiv']}|{item['accion']}"
            for item in problemas_cups_equivalentes
        ]
        
        # Escribir en Excel: fila 3+
        _write_column(sheet, 1, centros_costo_str, start_row=3)
        _write_column(sheet, 2, ide_contrato_str, start_row=3)
        _write_column(sheet, 3, cups_equiv_str, start_row=3)
        
        # ParaJSON: un solo bloque para IDE Contrato (con todos los campos)
        problemas_encontrados = {
            "No se encuentra coincidencia con los siguientes centros de costos": [
                f"{item['factura']}|{item['centro_actual']}|{item['centro_deberia']}"
                for item in problemas_centros
            ],
            "Problemas de IDE Contrato": problemas_ide_contrato,
            "Cups equivalentes urgencias": problemas_cups_equivalentes,
        }
    else:
        # Odontología: todas las validaciones existentes
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        logger.info("create_revision_sheet - area=%s, Llamando _detect_ide_contrato_odontologia", area)
        ide_contrato = _detect_ide_contrato_odontologia(data_sheet, indices)
        logger.info("create_revision_sheet - IDE Contrato encontrados: %d", len(ide_contrato))
        
        # Formatear para Excel: "FACTURA TIPO_ACTUAL -> TIPO_DEBERIA (Edad: X)"
        tipo_id_edad_str = [
            f"{item['factura']} {item['tipo_actual']} -> {item['tipo_deberia']} (Edad: {item['edad']})"
            for item in tipo_id_edad
        ]
        
        # Formatear IDE Contrato: "FACTURA|CÓDIGO|ENTIDAD|IDE_ACTUAL|IDE_DEBERIA"
        ide_contrato_str = [
            f"{item['factura']}|{item['codigo']}|{item['entidad']}|{item['ide_contrato_actual']}|{item['ide_contrato_deberia']}"
            for item in ide_contrato
        ]
        
        # Escribir resultados en fila 3+
        _write_column(sheet, 1, decimales, start_row=3)
        _write_column(sheet, 2, doble_tipo, start_row=3)
        _write_column(sheet, 3, ruta_dup, start_row=3)
        _write_column(sheet, 4, conveniente_proc, start_row=3)
        _write_column(sheet, 5, cantidades, start_row=3)
        _write_column(sheet, 6, tipo_id_edad_str, start_row=3)
        _write_column(sheet, 8, ide_contrato_str, start_row=3)
        
        problemas_encontrados = {
            "Decimales": decimales,
            "Doble tipo procedimiento": doble_tipo,
            "Ruta Duplicada": ruta_dup,
            "Convenio de procedimiento": conveniente_proc,
            "Cantidades": cantidades,
            "Tipo Identificación": [item["factura"] for item in tipo_id_edad],
            "IDE Contrato": ide_contrato,
        }
    
    # Aplicar estilo a filas de datos (fila 3+) según el área
    if area == AREA_URGENCIAS:
        data_style = create_urgencia_data_row_style()
    else:
        data_style = create_data_row_style()
    
    for row in range(3, sheet.max_row + 1):
        for col in range(1, sheet.max_column + 1):
            cell = sheet.cell(row=row, column=col)
            cell.fill = data_style["fill"]
            cell.border = data_style["border"]
            cell.alignment = data_style["alignment"]
    
    # Ajustar ancho de columnas automáticamente
    column_widths = auto_adjust_column_width(sheet)
    
    # Logging según el área
    if area == AREA_URGENCIAS:
        logger.info(
            "Hoja Revision Urgencias creada - Centros de Costos: %d, Cups Equivalentes: %d",
            len(problemas_centros),
            len(problemas_cups_equivalentes),
        )
    else:
        logger.info(
            "Hoja Revision Odontología creada - Decimales: %d, Doble tipo: %d, "
            "Ruta duplicada: %d, Convenio proc: %d, Cantidades: %d, Tipo ID: %d, IDE Contrato: %d",
            len(decimales),
            len(doble_tipo),
            len(ruta_dup),
            len(conveniente_proc),
            len(cantidades),
            len(tipo_id_edad),
            len(ide_contrato),
        )
    
    # Build resultado según el área
    if area == AREA_URGENCIAS:
        return {
            "rule": "create_revision_sheet",
            "sheet": REVISION_SHEET,
            "area": area,
            "headers": list(URGENCIA_REVISION_HEADERS.values()),
            "centros_de_costos_found": len(problemas_centros),
            "problemas": problemas_encontrados,
            "column_widths": column_widths,
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
        }
    else:
        return {
            "rule": "create_revision_sheet",
            "sheet": REVISION_SHEET,
            "area": area,
            "headers": list(REVISION_HEADERS.values()),
            "decimal_invoices_found": len(decimales),
            "doble_tipo_invoices_found": len(doble_tipo),
            "ruta_duplicada_found": len(ruta_dup),
            "convenio_de_procedimiento_found": len(conveniente_proc),
            "cantidades_found": len(cantidades),
            "tipo_identificacion_found": len(tipo_id_edad),
            "ide_contrato_found": len(ide_contrato),
            "problemas": problemas_encontrados,
            "column_widths": column_widths,
            "missing_columns": missing_columns,
        }


def detect_all_problems(
    data_sheet: Worksheet,
    area: str = AREA_ODONTOLOGIA,
    profesional_dias: dict[str, list[int]] | None = None,
    permitir_todos_centros: bool = False,
) -> dict[str, Any]:
    """
    Detecta todos los problemas en las facturas SIN crear hoja Excel.
    
    Esta función retorna los resultados para mostrarlos en el HTML del área.
    
    Args:
        data_sheet: Hoja de Excel con los datos
        area: Área del sistema ("odontologia", "urgencias" o "equipos_basicos")
        profesional_dias: Dict {identificacion: [dias]} con días seleccionados por profesional
        permitir_todos_centros: Si True, solo permite ODONTOLOGIA y EXTRAMURAL sin validación por fecha
    
    Returns:
        Dict con los problemas encontrados por categoría
    """
    # Obtener índices de columnas (coincidencia exacta - reporta faltantes)
    headers = [
        data_sheet.cell(row=1, column=col).value
        for col in range(1, data_sheet.max_column + 1)
    ]
    indices, missing_columns = _get_column_indices(headers)
    
    # Si hay columnas faltantes, incluir en el resultado para mostrar al usuario
    if missing_columns:
        logger.error("Columnas faltantes en el Excel: %s", missing_columns)
    
    if area == AREA_URGENCIAS:
        # Urgencias: detectar códigos NO en DB con IDE=969
        # Excluir Código Tipo Procedimiento = 09, 12, 13
        
        # Debug: mostrar índices encontrados en el dict 'indices'
        logger.warning("=== DEBUG: Indices del dict para ESS118 ===")
        logger.warning(f"  Código: {indices.get('codigo')}")
        logger.warning(f"  Cód. Equivalente CUPS: {indices.get('codigo_equiv')}")
        logger.warning(f"  Código Tipo Procedimiento: {indices.get('codigo_tipo_procedimiento')}")
        logger.warning(f"  Codigo_Entidad: {indices.get('codigo_entidad_cobrar')}")
        logger.warning(f"  IDE Contrato: {indices.get('ide_contrato')}")
        
        logger.warning("=== VERIFICANDO CÓDIGOS ESS118 CONTRA DB ===")
        problemas_codigos_no_en_db = _get_codigos_no_en_db_ess118(data_sheet, indices)
        
        # Extraer códigos únicos para logging
        codigos_no_en_db_set = {item["codigo"] for item in problemas_codigos_no_en_db}
        
        if problemas_codigos_no_en_db:
            logger.warning("Procedimientos NO en DB (ESS118 + IDE=969): %d errores, códigos: %s",
                        len(problemas_codigos_no_en_db), sorted(codigos_no_en_db_set))
        else:
            logger.warning("No hay códigos sin DB con IDE=969 para ESS118")
        
        # Debug: mostrar valores de las primeras filas ESS118
        logger.warning("=== DEBUG: 5 primeras filas ESS118 ===")
        codigo_equiv_idx = indices.get("codigo_equiv")
        codigo_tipo_idx = indices.get("codigo_tipo_procedimiento")
        codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
        ide_idx = indices.get("ide_contrato")
        
        count = 0
        for row in range(2, data_sheet.max_row + 1):
            entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value if codigo_entidad_idx is not None else None
            if entidad and "ESS118" in str(entidad).upper():
                cod_equiv = data_sheet.cell(row=row, column=codigo_equiv_idx + 1).value if codigo_equiv_idx is not None else None
                cod_tipo = data_sheet.cell(row=row, column=codigo_tipo_idx + 1).value if codigo_tipo_idx is not None else None
                ide = data_sheet.cell(row=row, column=ide_idx + 1).value if ide_idx is not None else None
                logger.warning(f"  Fila {row}: equiv={cod_equiv}, tipo={cod_tipo}, IDE={ide}")
                count += 1
                if count >= 5:
                    break
        
        problemas_centros, problemas_ide_contrato, problemas_cups_equivalentes = _detect_centro_costo_urgencias(
            data_sheet, indices, problemas_codigos_no_en_db
        )
        
        # Agregar TODOS los procedimientos no encontrados en DB (no solo IDE=969)
        # como errores separados en ide_contrato
        for problema in problemas_codigos_no_en_db:
            problemas_ide_contrato.append({
                "factura": problema.get("factura", ""),
                "ide_contrato_actual": "N/A",
                "ide_contrato_deberia": "CÓDIGO NO EN DB",
                "procedimiento": problema.get("procedimiento", ""),
                "codigo": problema.get("codigo", ""),
                "entidad": problema.get("entidad", ""),
            })
        
        logger.info("Agregados %d procedimientos sin DB a problemas_ide_contrato", len(problemas_codigos_no_en_db))
        
        # reglas transversales
        decimales = detect_decimales(data_sheet, indices)
        tipo_identificacion_edad = detect_tipo_documento_edad(data_sheet, indices)
        # Nueva regla: Cód Entidad Cobrar vs Entidad Afiliación (solo loggear las 5 primeras filas)
        entidad_afiliacion_comparison = detect_codigo_entidad_vs_entidad_afiliacion(
            data_sheet, indices, limit_log=5
        )
        
        logger.info("detect_all_problems (Urgencias): problemas_centros=%d, problemas_ide_contrato=%d, decimales=%d, tipo_id_edad=%d, entidad_afiliacion=%d",
                   len(problemas_centros), len(problemas_ide_contrato), len(decimales), len(tipo_identificacion_edad), len(entidad_afiliacion_comparison))
        
        # Incluir TODOS los campos en el resultado
        return {
            "area": area,
            "problemas": {
                "centros_de_costos": [
                    {
                        "factura": item["factura"],
                        "codigo": item.get("codigo", ""),
                        "procedimiento": item.get("procedimiento", ""),
                        "centro_actual": item["centro_actual"],
                        "centro_deberia": item["centro_deberia"],
                    }
                    for item in problemas_centros
                ],
                "ide_contrato": [
                    {
                        "factura": item["factura"],
                        "ide_contrato_actual": item["ide_contrato_actual"],
                        "ide_contrato_deberia": item["ide_contrato_deberia"],
                        # Incluir campos adicionales si existen
                        "procedimiento": item.get("procedimiento", ""),
                        "codigo": item.get("codigo", ""),
                        "entidad": item.get("entidad", ""),
                        "nota": item.get("nota", ""),
                    }
                    for item in problemas_ide_contrato
                ],
                "cups_equivalentes": [
                    {
                        "factura": item["factura"],
                        "codigo": item["codigo"],
                        "codigo_equiv": item["codigo_equiv"],
                        "accion": item["accion"],
                    }
                    for item in problemas_cups_equivalentes
                ],
                # reglas transversales
                "decimales": decimales,
                "tipo_identificacion_edad": tipo_identificacion_edad,
                "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            },
            "totales": {
                "centros_de_costos": len(problemas_centros),
                "ide_contrato": len(problemas_ide_contrato),
                "cups_equivalentes": len(problemas_cups_equivalentes),
                "decimales": len(decimales),
                "tipo_identificacion_edad": len(tipo_identificacion_edad),
                "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            },
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
            "codigos_sin_db_ide_969": sorted(codigos_no_en_db_set) if problemas_codigos_no_en_db else [],
        }
    elif area == AREA_EQUIPOS_BASICOS:
        # Equipos Básicos: usar reglas independientes configurables
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada_equipos_basicos(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento_equipos_basicos(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas_equipos_basicos(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        logger.info("create_revision_sheet - Equipos Básicos, Llamando _detect_ide_contrato_odontologia")
        ide_contrato = _detect_ide_contrato_odontologia(data_sheet, indices)
        logger.info("create_revision_sheet - Equipos Básicos, IDE Contrato encontrados: %d", len(ide_contrato))
        
        # Regla transversal: Cód Entidad Cobrar vs Entidad Afiliación
        entidad_afiliacion_comparison = detect_codigo_entidad_vs_entidad_afiliacion(
            data_sheet, indices, limit_log=5
        )
        
        # Validación centro de costo (solo EQUIPOS BASICOS ODONTOLOGIA)
        centro_costo = _detect_centro_costo_odontologia(
            data_sheet, 
            indices, 
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
            centros_validos=[CENTRO_COSTO_EQUIPOS_BASICOS],
        )
        
        return {
            "area": area,
            "problemas": {
                "decimales": decimales,
                "doble_tipo_procedimiento": doble_tipo,
                "ruta_duplicada": ruta_dup,
                "convenio_procedimiento": conveniente_proc,
                "cantidades_anomalas": cantidades,
                "tipo_identificacion_edad": tipo_id_edad,
                "centro_costo": centro_costo,
                "ide_contrato": ide_contrato,
            },
            "totales": {
                "decimales": len(decimales),
                "doble_tipo_procedimiento": len(doble_tipo),
                "ruta_duplicada": len(ruta_dup),
                "convenio_procedimiento": len(conveniente_proc),
                "cantidades_anomalas": len(cantidades),
                "tipo_identificacion_edad": len(tipo_id_edad),
                "centro_costo": len(centro_costo),
                "ide_contrato": len(ide_contrato),
                "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            },
            "es_equipos_basicos": True,
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
        }
    else:
        # Odontología estándar: todas las validaciones
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        logger.info("detect_all_problems - Odontología, Llamando _detect_ide_contrato_odontologia")
        ide_contrato = _detect_ide_contrato_odontologia(data_sheet, indices)
        logger.info("detect_all_problems - Odontología, IDE Contrato encontrados: %d", len(ide_contrato))
        
        # Validación centro de costo Odontología
        centro_costo = _detect_centro_costo_odontologia(
            data_sheet, 
            indices, 
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )
        
        # Regla transversal: Cód Entidad Cobrar vs Entidad Afiliación
        entidad_afiliacion_comparison = detect_codigo_entidad_vs_entidad_afiliacion(
            data_sheet, indices, limit_log=5
        )
        
        return {
            "area": area,
            "problemas": {
                "decimales": decimales,
                "doble_tipo_procedimiento": doble_tipo,
                "ruta_duplicada": ruta_dup,
                "convenio_procedimiento": conveniente_proc,
                "cantidades_anomalas": cantidades,
                "tipo_identificacion_edad": tipo_id_edad,
                "centro_costo": centro_costo,
                "ide_contrato": ide_contrato,
                "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            },
            "totales": {
                "decimales": len(decimales),
                "doble_tipo_procedimiento": len(doble_tipo),
                "ruta_duplicada": len(ruta_dup),
                "convenio_procedimiento": len(conveniente_proc),
                "cantidades_anomalas": len(cantidades),
                "tipo_identificacion_edad": len(tipo_id_edad),
                "centro_costo": len(centro_costo),
                "ide_contrato": len(ide_contrato),
                "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            },
            "missing_columns": missing_columns,
        }
