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
    CODIGO_IDE_CONTRATO_861801,
    ENTIDAD_IDE_CONTRATO_861801,
    IDE_CONTRATO_REQUERIDO_861801,
    CODIGO_IDE_CONTRATO_890405,
    ENTIDAD_IDE_CONTRATO_890405,
    IDE_CONTRATO_CON_INSERCION_890405,
    IDE_CONTRATO_SIN_INSERCION_890405,
    CODIGO_INSERCION_BUSCAR,
    # Nueva regla EPSIC5
    CODIGO_IDE_CONTRATO_EPSIC5,
    ENTIDAD_IDE_CONTRATO_EPSIC5,
    IDE_CONTRATO_REQUERIDO_EPSIC5,
    CODIGO_IDE_CONTRATO_890405_EPSIC5,
    ENTIDAD_IDE_CONTRATO_890405_EPSIC5,
    IDE_CONTRATO_CON_INSERCION_890405_EPSIC5,
    IDE_CONTRATO_SIN_INSERCION_890405_EPSIC5,
    # Regla ESS118
    ENTIDAD_IDE_CONTRATO_ESS118,
    CODIGOS_IDE_CONTRATO_NO_969,
    IDE_CONTRATO_PROHIBIDO_ESS118,
    # Nueva regla ESS118 + Código 735301
    CODIGO_IDE_CONTRATO_735301,
    ENTIDAD_IDE_CONTRATO_735301,
    IDE_CONTRATO_REQUERIDO_735301,
    # Nueva regla ESS118 + Código 906340 -> IDE Contrato debe ser 839
    CODIGO_IDE_CONTRATO_906340,
    ENTIDAD_IDE_CONTRATO_906340,
    IDE_CONTRATO_REQUERIDO_906340,
    # Nueva regla ESS118 + Código 861801 -> IDE Contrato debe ser 974
    CODIGO_IDE_CONTRATO_861801,
    IDE_CONTRATO_REQUERIDO_861801,
    # Nueva regla ESS118 + Código 890405 -> IDE Contrato 977 o 973 según inserción
    IDE_CONTRATO_SIN_INSERCION_890405,
    IDE_CONTRATO_CON_INSERCION_890405,
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
    # Nueva regla Código 906340 + Entidad=ESS118 + Entidad Cobrar="NUEVA EMPRESA PROMOTORA DE SALUD S.A." -> IDE 957
    CODIGO_IDE_CONTRATO_906340_EMPRESA,
    ENTIDAD_IDE_CONTRATO_EMPRESA,
    ENTIDAD_COBRAR_NUEVA_EMPRESA,
    IDE_CONTRATO_REQUERIDO_906340_EMPRESA,
    # Nueva regla Código 861801 + Entidad=ESS118 + Entidad Cobrar="NUEVA EMPRESA PROMOTORA DE SALUD S.A." -> IDE 958
    CODIGO_IDE_CONTRATO_861801_EMPRESA,
    IDE_CONTRATO_REQUERIDO_861801_EMPRESA,
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
    # Nueva regla Código 890405 + Entidad=ESS118 + Entidad Cobrar="NUEVA EMPRESA PROMOTORA DE SALUD S.A." -> IDE según inserción
    CODIGO_IDE_CONTRATO_890405_EMPRESA,
    IDE_CONTRATO_CON_INSERCION_890405_EMPRESA,
    IDE_CONTRATO_SIN_INSERCION_890405_EMPRESA,
    # Urgencias - Entidad -> IDE Contrato
    URGENCIA_ENTIDAD_CONTRATO,
    URGENCIA_ENTIDAD_MULTIPLE_CONTRATO,
    # Equipos Básicos - Reglas independientes
    EQUIPOS_BASICOS_TARGET_PROCEDURES,
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
        "codigo": "Cód. Equivalente CUPS",
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
) -> list[str]:
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
        
        if vlr_sub_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_sub_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
        
        if not has_decimals and vlr_proc_idx is not None:
            vlr = data_sheet.cell(row=row, column=vlr_proc_idx + 1).value
            if isinstance(vlr, float) and vlr % 1 != 0:
                has_decimals = True
        
        if has_decimals and factura_str not in decimal_invoices:
            decimal_invoices.append(factura_str)
            logger.debug("Factura %s con decimales detectada", factura_str)
    
    return decimal_invoices


def _detect_doble_tipo_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
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
    
    return [fact for fact, tipos in tipo_por_factura.items() if len(tipos) > 1]


def _detect_ruta_duplicada(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
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
    
    return [
        ident for ident, facturas in conteo_ident.items()
        if len(facturas) >= RUTA_DUPLICADA_THRESHOLD
    ]


def _detect_ruta_duplicada_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
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
    
    # Usar umbral configurable de Equipos Básicos
    return [
        ident for ident, facturas in conteo_ident.items()
        if len(facturas) >= EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD
    ]


def _detect_convenio_procedimiento(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con procedimientos que no corresponden al convenio."""
    num_fact_idx = indices["numero_factura"]
    convenio_idx = indices["convenio_facturado"]
    proc_idx = indices["procedimiento"]
    
    if None in (num_fact_idx, convenio_idx, proc_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value
        
        if procedimiento is None:
            continue
        
        proc_str = str(procedimiento).strip()
        should_add = False
        
        # Caso 1: Convenio Asistencial con procedimientos PyP
        if convenio == CONVENIO_ASISTENCIAL and proc_str in TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: Asistencial con procedimiento PyP: %s",
                row,
                proc_str,
            )
        
# Caso 2: Convenio PyP con procedimientos NO PyP
        elif convenio == CONVENIO_PYP and proc_str not in TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: PyP con procedimiento diferente: %s",
                row,
                proc_str,
            )
        
        if should_add and factura_str not in problemas:
            problemas.append(factura_str)
    
    return problemas


def _detect_convenio_procedimiento_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con procedimientos que no corresponden al convenio (Equipos Básicos - reglas independientes)."""
    num_fact_idx = indices["numero_factura"]
    convencio_idx = indices["convenio_facturado"]
    proc_idx = indices["procedimiento"]
    
    if None in (num_fact_idx, convencio_idx, proc_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convencio = data_sheet.cell(row=row, column=convencio_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value
        
        if procedimiento is None:
            continue
        
        proc_str = str(procedimiento).strip()
        should_add = False
        
        # Caso 1: Convencio Asistencial con procedimientos PyP (Equipos Básicos)
        if convencio == CONVENIO_ASISTENCIAL and proc_str in EQUIPOS_BASICOS_TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: Asistencial con procedimiento PyP (Equipos Básicos): %s",
                row,
                proc_str,
            )
        
        # Caso 2: Convencio PyP con procedimientos NO PyP (Equipos Básicos)
        elif convencio == CONVENIO_PYP and proc_str not in EQUIPOS_BASICOS_TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: PyP con procedimiento diferente (Equipos Básicos): %s",
                row,
                proc_str,
            )
        
        if should_add and factura_str not in problemas:
            problemas.append(factura_str)
    
    return problemas


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con procedimientos que no corresponden al convenio (Equipos Básicos - reglas independientes)."""
    num_fact_idx = indices["numero_factura"]
    convencio_idx = indices["convenio_facturado"]
    proc_idx = indices["procedimiento"]
    
    if None in (num_fact_idx, convencio_idx, proc_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        convencio = data_sheet.cell(row=row, column=convencio_idx + 1).value
        procedimiento = data_sheet.cell(row=row, column=proc_idx + 1).value
        
        if procedimiento is None:
            continue
        
        proc_str = str(procedimiento).strip()
        should_add = False
        
        # Caso 1: Convencio Asistencial con procedimientos PyP (Equipos Básicos)
        if convencio == CONVENIO_ASISTENCIAL and proc_str in EQUIPOS_BASICOS_TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: Asistencial con procedimiento PyP (Equipos Básicos): %s",
                row,
                proc_str,
            )
        
        # Caso 2: Convencio PyP con procedimientos NO PyP (Equipos Básicos)
        elif convencio == CONVENIO_PYP and proc_str not in EQUIPOS_BASICOS_TARGET_PROCEDURES:
            should_add = True
            logger.debug(
                "Fila %s: PyP con procedimiento diferente (Equipos Básicos): %s",
                row,
                proc_str,
            )
        
        if should_add and factura_str not in problemas:
            problemas.append(factura_str)
    
    return problemas


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con cantidades anómalas."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    convencio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, convencio_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        convencio = data_sheet.cell(row=row, column=convencio_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Reglas de cantidad anómala
        is_anomaly = (
            # Consultas >= 2
            (tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > 10
            or cantidad > CANTIDAD_MAX
            # PyP >= 3
            or (convencio == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in problemas:
            problemas.append(factura_str)
            logger.debug(
                "Fila %s: Cantidad anómala (Tipo: %s, Convenio: %s, Cant: %s)",
                row,
                tipo_value,
                convento,
                cantidad,
            )
    
    return problemas


def _detect_cantidades_anomalas_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con cantidades anómalas (Equipos Básicos - reglas independientes)."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    convencio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, convencio_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        convencio = data_sheet.cell(row=row, column=convencio_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Reglas de cantidad anómala (Equipos Básicos - configurables)
        is_anomaly = (
            # Consultas >= umbral configurable
            (tipo_value == "Consultas" and cantidad >= EQUIPOS_BASICOS_CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > máximo configurable
            or cantidad > EQUIPOS_BASICOS_CANTIDAD_MAX
            # PyP >= umbral configurable
            or (convencio == CONVENIO_PYP and cantidad >= EQUIPOS_BASICOS_CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in problemas:
            problemas.append(factura_str)
            logger.debug(
                "Fila %s: Cantidad anómala Equipos Básicos (Tipo: %s, Convenios: %s, Cant: %s)",
                row,
                tipo_value,
                convencio,
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
) -> set[str]:
    """
    Retorna set de códigos CUPS para ESS118 que NO están en la DB.
    
    Returns:
        Set de códigos que no se encontraron en procedimientos.db
    """
    from app.services.procedimientos_db import get_procedimiento
    
    EPS_DB = "EMSSANAR_CAPITA"
    
    codigo_idx = indices.get("codigo")
    codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
    entidad_cobrar_idx = indices.get("entidad_cobrar")
    
    if codigo_idx is None:
        return set()
    
    # Collect códigos únicos para ESS118
    codigos_ess118 = set()
    
    for row in range(2, data_sheet.max_row + 1):
        es_ess118 = False
        
        if codigo_entidad_idx is not None:
            codigo_entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value
            if codigo_entidad:
                entidad_normalizada = str(codigo_entidad).strip().upper()
                if "ESS118" in entidad_normalizada:
                    es_ess118 = True
        
        if not es_ess118 and entidad_cobrar_idx is not None:
            entidad = data_sheet.cell(row=row, column=entidad_cobrar_idx + 1).value
            if entidad:
                entidad_normalizada = str(entidad).strip().upper()
                if "ESS118" in entidad_normalizada:
                    es_ess118 = True
        
        if not es_ess118:
            continue
        
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        if codigo:
            codigos_ess118.add(str(codigo).strip())
    
    # Filtrar los que no están en la DB
    codigos_no_en_db = set()
    for codigo in codigos_ess118:
        proc = get_procedimiento(EPS_DB, codigo)
        if not proc:
            codigos_no_en_db.add(codigo)
    
    return codigos_no_en_db


def _detect_centro_costo_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    codigos_no_en_db: set[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    Detecta facturas con problemas de centro de costo y advertencias de derechos:
    -Regla 1: Código=02 Y Laboratorio=No Y Centro != APOYO DIAGNOSTICO-IMAGENOLOGIA
    -Regla 2: Código=14 Y Centro == TRASLADOS
    -Regla 3: Código en (990211, 890205, 890405, 861801) Y Centro != PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN
    -Regla 4: Código en (735301, 90DS02) Y Centro != QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO
    -Regla 5: Código en lista laboratorio Y Entidad=ESS118 Y Tipo=Intramural Y Centro != LABORATORIO CLINICO
    -Regla nueva: Si código NO está en DB Y Entidad=ESS118 Y IDE=969 -> ERROR
    
    Args:
        data_sheet: Hoja de datos
        indices: Índices de columnas
        codigos_no_en_db: Set de códigos que no están en la DB (para regla 969)
    
    Returns:
        Tuple de dos listas:
        - problemas_centros: lista de dicts con keys: "factura", "centro_actual", "centro_deberia"
        - problemas_ide_contrato: lista de dicts con keys: "factura", "ide_contrato_actual", "ide_contrato_deberia"
    """
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
        CODIGO_IDE_CONTRATO_861801,
        ENTIDAD_IDE_CONTRATO_861801,
        IDE_CONTRATO_REQUERIDO_861801,
        CODIGO_IDE_CONTRATO_890405,
        ENTIDAD_IDE_CONTRATO_890405,
        IDE_CONTRATO_CON_INSERCION_890405,
        IDE_CONTRATO_SIN_INSERCION_890405,
    )
    
    # Debug: mostrar los índices detectados
    logger.info("Indices detectados para urgencias: %s", indices)
    
    num_fact_idx = indices["numero_factura"]
    ident_idx = indices.get("identificacion")
    codigo_tipo_proc_idx = indices.get("codigo_tipo_procedimiento")
    codigo_idx = indices.get("codigo")
    laboratorio_idx = indices.get("laboratorio")
    centro_costo_idx = indices.get("centro_costo")
    codigo_entidad_cobrar_idx = indices.get("codigo_entidad_cobrar")
    entidad_cobrar_idx = indices.get("entidad_cobrar")
    tipo_factura_descripcion_idx = indices.get("tipo_factura_descripcion")
    ide_contrato_idx = indices.get("ide_contrato")
    proc_idx = indices.get("procedimiento")
    
    logger.info("Índices relevantes - codigo_tipo_proc: %s, codigo: %s, laboratorio: %s, centro_costo: %s, ide_contrato: %s, codigo_entidad: %s",
                codigo_tipo_proc_idx, codigo_idx, laboratorio_idx, centro_costo_idx, ide_contrato_idx, codigo_entidad_cobrar_idx)
    
    if num_fact_idx is None:
        return []
    
    # Si no tenemos las columnas necesarias, no podemos validar
    if codigo_tipo_proc_idx is None and laboratorio_idx is None and centro_costo_idx is None:
        logger.warning("No se encontraron columnas necesarias para validación de urgencias")
        return [], []
    
    problemas_centros = []
    problemas_ide_contrato = []
    facturas_ya_procesadas_centros = set()
    # NOTA: No usamos set para IDE Contrato porque cada regla es independiente
    # y una factura puede tener múltiples errores (ej: diferente código)
    
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
            })
            facturas_ya_procesadas_centros.add(factura_str)
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
                })
                facturas_ya_procesadas_centros.add(factura_str)
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
                })
                facturas_ya_procesadas_centros.add(factura_str)
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
                })
                facturas_ya_procesadas_centros.add(factura_str)
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
                    })
                    facturas_ya_procesadas_centros.add(factura_str)
                    logger.info(
                        "REGLA5: Fila %s: Código=%s, ESS118+Intramural, Centro incorrecto (Centro: '%s')",
                        row,
                        codigo_excluir,
                        centro_costo_str,
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
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_861801:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801,
                })
                # NO agregamos a set para permitir múltiples errores por factura

        # ----- Regla 8: Código=890405 + Entidad=EPSI05
        # Si identificación tiene código 861801 -> IDE Contrato = 976
        # Si identificación NO tiene código 861801 -> IDE Contrato = 977
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_890405:
            # Determinar el IDE Contrato esperado basado en si tiene inserción
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405 if ident_str in identificaciones_con_insercion else IDE_CONTRATO_SIN_INSERCION_890405
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

# ----- Regla 11: Entidad=ESS118 + Códigos específicos -> IDE Contrato NO puede ser 969
        # (Independiente - NO depende de otras reglas)
        if codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESS118:
            if codigo_excluir in CODIGOS_IDE_CONTRATO_NO_969:
                if ide_contrato_str == IDE_CONTRATO_PROHIBIDO_ESS118:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": "cualquiera EXCEPTO 969",
                    })
                    logger.debug(
                        "Fila %s: Entidad=ESS118, Código=%s, IDE 969 no permitido",
                        row,
                        codigo_excluir,
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
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_906340:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_906340,
                )

        # ----- Regla 14: Cód Entidad Cobrar=ESS118 + Código=861801 -> IDE Contrato debe ser 974
        # Urgencias y Contratos
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_861801:
            if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801,
                })
                logger.debug(
                    "Fila %s: Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                    row,
                    codigo_entidad_str,
                    codigo_excluir,
                    ide_contrato_str,
                    IDE_CONTRATO_REQUERIDO_861801,
                )

        # ----- Regla 15: Cód Entidad Cobrar=ESS118 + Código=890405 -> IDE Contrato 977 o 973 según inserción
        # Urgencias y Contratos - si la identificación tiene código 861801 en otra fila
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405 and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_890405:
            # Determinar IDE esperado según si tiene inserción
            tiene_insercion = ident_str in identificaciones_con_insercion
            ide_esperado = IDE_CONTRATO_CON_INSERCION_890405 if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405
            
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

        # ----- Regla 16: Cód Entidad Cobrar=ESSC18 + Código=906340 -> IDE Contrato debe ser 842
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
        if codigo_excluir == CODIGO_IDE_CONTRATO_906340_EMPRESA:
            if codigo_entidad_str == "EPSS41":
                if ide_contrato_str != IDE_CONTRATO_REQUERIDO_906340_EMPRESA:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "codigo_entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_906340_EMPRESA,
                    })
                    logger.debug(
                        "Fila %s: Cód Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                        row,
                        codigo_entidad_str,
                        codigo_excluir,
                        ide_contrato_str,
                        IDE_CONTRATO_REQUERIDO_906340_EMPRESA,
                    )

        # ----- Regla 23: Código 861801 + Cód Entidad Cobrar=EPSS41 -> IDE 958
        # SOLO usa "Cód Entidad Cobrar", NO "Entidad Cobrar"
        if codigo_excluir == CODIGO_IDE_CONTRATO_861801_EMPRESA:
            if codigo_entidad_str == "EPSS41":
                if ide_contrato_str != IDE_CONTRATO_REQUERIDO_861801_EMPRESA:
                    problemas_ide_contrato.append({
                        "factura": factura_str,
                        "procedimiento": proc_str,
                        "codigo": codigo_excluir,
                        "codigo_entidad": codigo_entidad_str,
                        "ide_contrato_actual": ide_contrato_str,
                        "ide_contrato_deberia": IDE_CONTRATO_REQUERIDO_861801_EMPRESA,
                    })
                    logger.debug(
                        "Fila %s: Cód Entidad=%s, Código=%s, IDE incorrecto (Actual: '%s', Esperado: %s)",
                        row,
                        codigo_entidad_str,
                        codigo_excluir,
                        ide_contrato_str,
                        IDE_CONTRATO_REQUERIDO_861801_EMPRESA,
                    )

        # ----- Regla 24: Código 890405 + Cód Entidad Cobrar=EPSS41 -> IDE según inserción
        # SOLO usa "Cód Entidad Cobrar", NO "Entidad Cobrar"
        if codigo_excluir == CODIGO_IDE_CONTRATO_890405_EMPRESA:
            if codigo_entidad_str == "EPSS41":
                tiene_insercion = ident_str in identificaciones_con_insercion
                ide_esperado = IDE_CONTRATO_CON_INSERCION_890405_EMPRESA if tiene_insercion else IDE_CONTRATO_SIN_INSERCION_890405_EMPRESA
                
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

    # ----- NUEVA REGLA: Código NO está en DB + Entidad=ESS118 + IDE=969 -> ERROR
    # Si el código no existe en la base de datos de procedimientos, no puede tener IDE 969
    if codigos_no_en_db and codigo_entidad_str == ENTIDAD_IDE_CONTRATO_ESS118:
        if codigo_excluir in codigos_no_en_db:
            if ide_contrato_str == IDE_CONTRATO_PROHIBIDO_ESS118:
                problemas_ide_contrato.append({
                    "factura": factura_str,
                    "procedimiento": proc_str,
                    "codigo": codigo_excluir,
                    "entidad": codigo_entidad_str,
                    "ide_contrato_actual": ide_contrato_str,
                    "ide_contrato_deberia": "cualquiera EXCEPTO 969",
                    "nota": "Código NO encontrado en DB de procedimientos",
                })
                logger.info(
                    "REGLA DB: Fila %s: Código '%s' NO está en DB + IDE 969 -> ERROR",
                    row,
                    codigo_excluir,
                )

    return problemas_centros, problemas_ide_contrato


def _log_verificacion_codigos_ess118(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """
    Verifica códigos CUPS de ESS118 contra la base de datos de procedimientos.
    
    Muestra en el log todos los códigos que NO se encuentran en la DB (EMSSANAR_CAPITA).
    
    Returns:
        Lista de códigos no encontrados en la DB
    """
    from app.services.procedimientos_db import get_procedimiento
    
    EPS_DB = "EMSSANAR_CAPITA"
    
    # Usar nombres exactos de columnas
    codigo_idx = indices.get("Cód. Equivalente CUPS")
    codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
    entidad_cobrar_idx = indices.get("entidad_cobrar")
    codigo_tipo_proc_idx = indices.get("Código Tipo Procedimiento")
    
    if codigo_idx is None:
        logger.warning("No hay índice de Cód. Equivalente CUPS")
        return set()
    
    # Collect códigos únicos para ESS118
    codigos_ess118 = set()
    
    for row in range(2, data_sheet.max_row + 1):
        # Detectar si es ESS118 (por código entidad o nombre)
        es_ess118 = False
        
        if codigo_entidad_idx is not None:
            codigo_entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value
            if codigo_entidad:
                entidad_normalizada = str(codigo_entidad).strip().upper()
                if "ESS118" in entidad_normalizada:
                    es_ess118 = True
        
        if not es_ess118 and entidad_cobrar_idx is not None:
            entidad = data_sheet.cell(row=row, column=entidad_cobrar_idx + 1).value
            if entidad:
                entidad_normalizada = str(entidad).strip().upper()
                if "ESS118" in entidad_normalizada:
                    es_ess118 = True
        
        if not es_ess118:
            continue
        
        # Verificar例外ión: Código Tipo Procedimiento = 09, 12, 13 → no incluir
        codigo_tipo = None
        if codigo_tipo_proc_idx:
            codigo_tipo = data_sheet.cell(row=row, column=codigo_tipo_proc_idx + 1).value
        
        if codigo_tipo and str(codigo_tipo).strip() in ["09", "12", "13"]:
            continue
        
        codigo = data_sheet.cell(row=row, column=codigo_idx + 1).value
        if codigo:
            codigos_ess118.add(str(codigo).strip())
    
    if not codigos_ess118:
        return set()
    
    # Verificar cada código contra la DB
    codigos_no_encontrados = set()
    
    for codigo in codigos_ess118:
        proc = get_procedimiento(EPS_DB, codigo)
        if not proc:
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
        codigos_no_en_db = _get_codigos_no_en_db_ess118(data_sheet, indices)
        if codigos_no_en_db:
            logger.warning("Códigos NO encontrados en DB para ESS118 (%d): %s",
                        len(codigos_no_en_db), sorted(codigos_no_en_db))
        else:
            logger.warning("Todos los códigos de ESS118 están en DB")
        problemas_centros, problemas_ide_contrato = _detect_centro_costo_urgencies(
            data_sheet, indices, codigos_no_en_db
        )
        
        # Formatear para Excel: "FACTURA CENTRO_ACTUAL -> CENTRO_DEBERIA"
        centros_costo_str = [
            f"{item['factura']} {item['centro_actual']} -> {item['centro_deberia']}"
            for item in problemas_centros
        ]
        
        # Formatear IDE Contrato: incluir todos los datos
        ide_contrato_str = [
            f"{item['factura']}|{item.get('procedimiento', '-')}|{item.get('codigo', '-')}|{item.get('entidad', '-')}|{item['ide_contrato_actual']}|{item['ide_contrato_deberia']}"
            for item in problemas_ide_contrato
        ]
        
        # Escribir en Excel: fila 3+
        _write_column(sheet, 1, centros_costo_str, start_row=3)
        _write_column(sheet, 2, ide_contrato_str, start_row=3)
        
        # ParaJSON: un solo bloque para IDE Contrato (con todos los campos)
        problemas_encontrados = {
            "No se encuentra coincidencia con los siguientes centros de costos": [
                f"{item['factura']}|{item['centro_actual']}|{item['centro_deberia']}"
                for item in problemas_centros
            ],
            "Problemas de IDE Contrato": problemas_ide_contrato,
        }
    else:
        # Odontología: todas las validaciones existentes
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
        # Formatear para Excel: "FACTURA TIPO_ACTUAL -> TIPO_DEBERIA (Edad: X)"
        tipo_id_edad_str = [
            f"{item['factura']} {item['tipo_actual']} -> {item['tipo_deberia']} (Edad: {item['edad']})"
            for item in tipo_id_edad
        ]
        
        # Escribir resultados en fila 3+
        _write_column(sheet, 1, decimales, start_row=3)
        _write_column(sheet, 2, doble_tipo, start_row=3)
        _write_column(sheet, 3, ruta_dup, start_row=3)
        _write_column(sheet, 4, conveniente_proc, start_row=3)
        _write_column(sheet, 5, cantidades, start_row=3)
        _write_column(sheet, 6, tipo_id_edad_str, start_row=3)
        
        problemas_encontrados = {
            "Decimales": decimales,
            "Doble tipo procedimiento": doble_tipo,
            "Ruta Duplicada": ruta_dup,
            "Convenio de procedimiento": conveniente_proc,
            "Cantidades": cantidades,
            "Tipo Identificación": [item["factura"] for item in tipo_id_edad],
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
            "Hoja Revision Urgencias creada - Centros de Costos: %d",
            len(problemas_centros),
        )
    else:
        logger.info(
            "Hoja Revision Odontología creada - Decimales: %d, Doble tipo: %d, "
            "Ruta duplicada: %d, Convenio proc: %d, Cantidades: %d, Tipo ID: %d",
            len(decimales),
            len(doble_tipo),
            len(ruta_dup),
            len(conveniente_proc),
            len(cantidades),
            len(tipo_id_edad),
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
            "problemas": problemas_encontrados,
            "column_widths": column_widths,
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
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
        logger.warning(f"  Cód. Equivalente CUPS: {indices.get('codigo')}")
        logger.warning(f"  Código Tipo Procedimiento: {indices.get('codigo_tipo_procedimiento')}")
        logger.warning(f"  Codigo_Entidad: {indices.get('codigo_entidad_cobrar')}")
        logger.warning(f"  IDE Contrato: {indices.get('ide_contrato')}")
        
        logger.warning("=== VERIFICANDO CÓDIGOS ESS118 CONTRA DB ===")
        codigos_no_en_db = _get_codigos_no_en_db_ess118(data_sheet, indices)
        
        # Debug: mostrar valores de las primeras filas ESS118
        logger.warning("=== DEBUG: 5 primeras filas ESS118 ===")
        codigo_equiv_idx = indices.get("codigo")
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
        
        # Buscar los que tienen IDE=969
        if codigos_no_en_db:
            ide_contrato_idx = indices.get("ide_contrato")
            codigo_equiv_idx = indices.get("codigo")
            codigo_entidad_idx = indices.get("codigo_entidad_cobrar")
            codigo_tipo_idx = indices.get("codigo_tipo_procedimiento")
            
            codigos_no_en_db_con_969 = set()
            
            if ide_contrato_idx and codigo_equiv_idx and codigo_entidad_idx:
                for row in range(2, data_sheet.max_row + 1):
                    codigo_entidad = data_sheet.cell(row=row, column=codigo_entidad_idx + 1).value
                    if codigo_entidad and "ESS118" in str(codigo_entidad).upper():
                        codigo = data_sheet.cell(row=row, column=codigo_equiv_idx + 1).value
                        ide = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
                        
                        # Verificar excepción: Código Tipo Procedimiento
                        codigo_tipo = None
                        if codigo_tipo_idx:
                            codigo_tipo = data_sheet.cell(row=row, column=codigo_tipo_idx + 1).value
                        
                        # Si es 09, 12, o 13 → no es error
                        if codigo_tipo and str(codigo_tipo).strip() in ["09", "12", "13"]:
                            continue
                        
                        if codigo and ide:
                            codigo_str = str(codigo).strip()
                            ide_str = str(ide).strip()
                            
                            if codigo_str in codigos_no_en_db and ide_str == "969":
                                codigos_no_en_db_con_969.add(codigo_str)
            
            if codigos_no_en_db_con_969:
                logger.warning("Códigos NO en DB + IDE=969 (%d): %s",
                            len(codigos_no_en_db_con_969), sorted(codigos_no_en_db_con_969))
            else:
                logger.warning("No hay códigos sin DB con IDE=969")
        
        problemas_centros, problemas_ide_contrato = _detect_centro_costo_urgencias(
            data_sheet, indices, codigos_no_en_db
        )
        
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
                # reglas transversales
                "decimales": decimales,
                "tipo_identificacion_edad": tipo_identificacion_edad,
                "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            },
            "totales": {
                "centros_de_costos": len(problemas_centros),
                "ide_contrato": len(problemas_ide_contrato),
                "decimales": len(decimales),
                "tipo_identificacion_edad": len(tipo_identificacion_edad),
                "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            },
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
        }
    elif area == AREA_EQUIPOS_BASICOS:
        # Equipos Básicos: usar reglas independientes configurables
        decimales = _detect_decimals(data_sheet, indices)
        doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
        ruta_dup = _detect_ruta_duplicada_equipos_basicos(data_sheet, indices)
        conveniente_proc = _detect_convenio_procedimiento_equipos_basicos(data_sheet, indices)
        cantidades = _detect_cantidades_anomalas_equipos_basicos(data_sheet, indices)
        tipo_id_edad = _detect_tipo_identificacion_edad(data_sheet, indices)
        
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
            },
            "totales": {
                "decimales": len(decimales),
                "doble_tipo_procedimiento": len(doble_tipo),
                "ruta_duplicada": len(ruta_dup),
                "convenio_procedimiento": len(conveniente_proc),
                "cantidades_anomalas": len(cantidades),
                "tipo_identificacion_edad": len(tipo_id_edad),
                "centro_costo": len(centro_costo),
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
                "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            },
            "missing_columns": missing_columns,  # Columnas no encontradas (coincidencia exacta)
        }
