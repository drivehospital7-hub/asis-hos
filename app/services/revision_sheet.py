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
from typing import Any

from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.constants import (
    CONVENIO_ASISTENCIAL,
    CONVENIO_PYP,
    REVISION_SHEET,
    TARGET_PROCEDURES,
    RUTA_DUPLICADA_THRESHOLD,
    CANTIDAD_CONSULTAS_MIN,
    CANTIDAD_MAX,
    CANTIDAD_PYP_MIN,
)

logger = logging.getLogger(__name__)


# Headers de la hoja Revisión
REVISION_HEADERS = {
    1: "Decimales",
    2: "Doble tipo procedimiento",
    3: "Ruta Duplicada",
    4: "Convenio de procedimiento",
    5: "Cantidades",
}


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


def _get_column_indices(headers: list[Any]) -> dict[str, int | None]:
    """
    Mapea nombres de columna a sus índices.
    
    Returns:
        Dict con nombre de columna -> índice (0-based) o None
    """
    indices: dict[str, int | None] = {
        "numero_factura": None,
        "vlr_subsidiado": None,
        "vlr_procedimiento": None,
        "tipo_procedimiento": None,
        "procedimiento": None,
        "identificacion": None,
        "convenio_facturado": None,
        "cantidad": None,
    }
    
    header_mapping = {
        ("número factura", "numero factura"): "numero_factura",
        ("vlr. subsidiado",): "vlr_subsidiado",
        ("vlr. procedimiento",): "vlr_procedimiento",
        ("tipo procedimiento",): "tipo_procedimiento",
        ("procedimiento",): "procedimiento",
        ("nº identificación", "numero identificacion"): "identificacion",
        ("convenio facturado",): "convenio_facturado",
        ("cantidad",): "cantidad",
    }
    
    for i, header in enumerate(headers):
        normalized = _normalize_header(header)
        for variants, key in header_mapping.items():
            if normalized in variants:
                indices[key] = i
                break
    
    return indices


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
    convenio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, ident_idx, convenio_idx):
        return []
    
    conteo_ident: dict[str, set[str]] = defaultdict(set)
    
    for row in range(2, data_sheet.max_row + 1):
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        if convenio != CONVENIO_PYP:
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


def _detect_cantidades_anomalas(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Detecta facturas con cantidades anómalas."""
    num_fact_idx = indices["numero_factura"]
    tipo_proc_idx = indices["tipo_procedimiento"]
    cantidad_idx = indices["cantidad"]
    convenio_idx = indices["convenio_facturado"]
    
    if None in (num_fact_idx, tipo_proc_idx, cantidad_idx, convenio_idx):
        return []
    
    problemas = []
    
    for row in range(2, data_sheet.max_row + 1):
        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = _normalize_invoice(numero_factura)
        if not factura_str:
            continue
        
        tipo_value = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        cantidad = data_sheet.cell(row=row, column=cantidad_idx + 1).value
        convenio = data_sheet.cell(row=row, column=convenio_idx + 1).value
        
        if not isinstance(cantidad, (int, float)):
            continue
        
        # Reglas de cantidad anómala
        is_anomaly = (
            # Consultas >= 2
            (tipo_value == "Consultas" and cantidad >= CANTIDAD_CONSULTAS_MIN)
            # Cualquier cantidad > 10
            or cantidad > CANTIDAD_MAX
            # PyP >= 3
            or (convenio == CONVENIO_PYP and cantidad >= CANTIDAD_PYP_MIN)
        )
        
        if is_anomaly and factura_str not in problemas:
            problemas.append(factura_str)
            logger.debug(
                "Fila %s: Cantidad anómala (Tipo: %s, Convenio: %s, Cant: %s)",
                row,
                tipo_value,
                convenio,
                cantidad,
            )
    
    return problemas


def _write_column(sheet: Worksheet, column: int, values: list[str], start_row: int = 2) -> None:
    """Escribe una lista de valores en una columna."""
    for i, value in enumerate(values, start=start_row):
        sheet.cell(row=i, column=column, value=value)


def create_revision_sheet(workbook: Workbook) -> dict[str, Any]:
    """
    Crea la hoja Revision con los problemas detectados.
    
    Args:
        workbook: Libro de Excel (debe tener una hoja activa con datos)
    
    Returns:
        Dict con información de los problemas encontrados
    """
    sheet = workbook.create_sheet(title=REVISION_SHEET)
    data_sheet = workbook.active
    
    # Aplicar headers
    for col, header in REVISION_HEADERS.items():
        sheet.cell(row=1, column=col, value=header)
    
    # Obtener índices de columnas
    headers = [
        data_sheet.cell(row=1, column=col).value
        for col in range(1, data_sheet.max_column + 1)
    ]
    indices = _get_column_indices(headers)
    
    # Detectar problemas
    decimales = _detect_decimals(data_sheet, indices)
    doble_tipo = _detect_doble_tipo_procedimiento(data_sheet, indices)
    ruta_dup = _detect_ruta_duplicada(data_sheet, indices)
    convenio_proc = _detect_convenio_procedimiento(data_sheet, indices)
    cantidades = _detect_cantidades_anomalas(data_sheet, indices)
    
    # Escribir resultados
    _write_column(sheet, 1, decimales)
    _write_column(sheet, 2, doble_tipo)
    _write_column(sheet, 3, ruta_dup)
    _write_column(sheet, 4, convenio_proc)
    _write_column(sheet, 5, cantidades)
    
    logger.info(
        "Hoja Revision creada - Decimales: %d, Doble tipo: %d, "
        "Ruta duplicada: %d, Convenio proc: %d, Cantidades: %d",
        len(decimales),
        len(doble_tipo),
        len(ruta_dup),
        len(convenio_proc),
        len(cantidades),
    )
    
    return {
        "rule": "create_revision_sheet",
        "sheet": REVISION_SHEET,
        "headers": list(REVISION_HEADERS.values()),
        "decimal_invoices_found": len(decimales),
        "doble_tipo_invoices_found": len(doble_tipo),
        "ruta_duplicada_found": len(ruta_dup),
        "convenio_de_procedimiento_found": len(convenio_proc),
        "cantidades_found": len(cantidades),
    }
