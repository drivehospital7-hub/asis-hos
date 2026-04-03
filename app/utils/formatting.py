"""Formato condicional para hojas Excel.

Este módulo contiene las funciones para aplicar formato condicional
a las hojas de Excel (colores según reglas de negocio).
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.constants import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    CONVENIO_ASISTENCIAL,
    CENTRO_COSTO_ODONTOLOGIA,
    ENTIDAD_MALLAMAS,
)

logger = logging.getLogger(__name__)


def find_column_letter_by_header(
    sheet: Worksheet,
    header_name: str,
    headers_row: int = 1,
) -> str | None:
    """
    Busca la letra de columna para un header dado.

    Args:
        sheet: Hoja de Excel
        header_name: Nombre del header a buscar
        headers_row: Fila donde están los headers (por defecto 1)

    Returns:
        Letra de la columna o None si no se encuentra
    """
    from openpyxl.utils import get_column_letter

    for col in range(1, sheet.max_column + 1):
        cell_value = sheet.cell(row=headers_row, column=col).value
        if cell_value == header_name:
            return get_column_letter(col)
    return None


def create_fill(color: str) -> PatternFill:
    """Crea un PatternFill con el color especificado."""
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


def apply_conditional_convenio_facturado(
    sheet: Worksheet,
    headers_row: int = 1,
) -> dict[str, Any]:
    """
    Aplica formato condicional rojo para regla de convenio facturado.
    
    Condición: Entidad=MALLAMAS, Convenio=Asistencial, Centro=ODONTOLOGIA
    → resalta en rojo (indicando posible error de convenio)
    
    Args:
        sheet: Hoja de datos
        headers_row: Fila de headers
    
    Returns:
        Dict con información de la regla aplicada
    """
    entidad_col = find_column_letter_by_header(sheet, "Entidad Cobrar", headers_row)
    convenio_col = find_column_letter_by_header(sheet, "Convenio Facturado", headers_row)
    centro_col = find_column_letter_by_header(sheet, "Centro Costo", headers_row)

    if not all([entidad_col, convenio_col, centro_col]):
        logger.warning(
            "No se pueden aplicar reglas de convenio facturado: "
            "columnas requeridas no encontradas."
        )
        return {"rule": "convenio_facturado_conditional", "applied": False}

    max_row = sheet.max_row
    fill = create_fill(COLOR_RED)

    data_range = f"{convenio_col}2:{convenio_col}{max_row}"
    formula = (
        f"=AND(${entidad_col}2=\"{ENTIDAD_MALLAMAS}\","
        f"${convenio_col}2=\"{CONVENIO_ASISTENCIAL}\","
        f"${centro_col}2=\"{CENTRO_COSTO_ODONTOLOGIA}\")"
    )

    rule = FormulaRule(formula=[formula], fill=fill)
    sheet.conditional_formatting.add(data_range, rule)

    logger.info(
        "Formato condicional aplicado a Convenio Facturado en %s (rojo)",
        data_range,
    )

    return {"rule": "convenio_facturado_conditional", "applied": True}


def apply_conditional_tipo_identificacion(
    sheet: Worksheet,
    headers_row: int = 1,
) -> dict[str, Any]:
    """
    Aplica formato condicional rojo para regla de tipo de identificación.
    
    Valida que el tipo de documento coincida con la edad:
    - < 7 años: RC (Registro Civil)
    - 7-17 años: TI (Tarjeta de Identidad)  
    - >= 18 años: CC (Cédula de Ciudadanía)
    - Para extranjeros: MS (<18) o AS (>=18)
    
    Args:
        sheet: Hoja de datos
        headers_row: Fila de headers
    
    Returns:
        Dict con información de la regla aplicada
    """
    tipo_id_col = find_column_letter_by_header(sheet, "Tipo Identificación", headers_row)
    fec_nac_col = find_column_letter_by_header(sheet, "Fec. Nacimiento", headers_row)
    fec_fact_col = find_column_letter_by_header(sheet, "Fec. Factura", headers_row)

    if not all([tipo_id_col, fec_nac_col, fec_fact_col]):
        logger.warning(
            "No se pueden aplicar reglas de tipo identificación: "
            "columnas requeridas no encontradas."
        )
        return {"rule": "tipo_identificacion_conditional", "applied": False}

    max_row = sheet.max_row
    fill = create_fill(COLOR_RED)

    data_range = f"{tipo_id_col}2:{tipo_id_col}{max_row}"
    
    # Fórmula que valida tipo de documento según edad
    formula = (
        f"=IF(OR(${tipo_id_col}2=\"RC\",${tipo_id_col}2=\"TI\",${tipo_id_col}2=\"CC\"), "
        f"OR("
        f"AND(DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")<7, ${tipo_id_col}2<>\"RC\"), "
        f"AND(DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")>=7, "
        f"DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")<18, ${tipo_id_col}2<>\"TI\"), "
        f"AND(DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")>=18, ${tipo_id_col}2<>\"CC\")), "
        f"IF(OR(${tipo_id_col}2=\"MS\",${tipo_id_col}2=\"AS\"), "
        f"OR("
        f"AND(DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")<18, ${tipo_id_col}2<>\"MS\"), "
        f"AND(DATEDIF(${fec_nac_col}2,${fec_fact_col}2,\"Y\")>=18, ${tipo_id_col}2<>\"AS\")), "
        f"FALSE))"
    )

    rule = FormulaRule(formula=[formula], fill=fill)
    sheet.conditional_formatting.add(data_range, rule)

    logger.info(
        "Formato condicional aplicado a Tipo Identificación en %s (rojo)",
        data_range,
    )

    return {"rule": "tipo_identificacion_conditional", "applied": True}


def apply_conditional_cruce_facturas(
    cruce_sheet: Worksheet,
    data_sheet: Worksheet,
    numero_factura_col: str,
) -> dict[str, Any]:
    """
    Aplica formato condicional a la hoja CruceFacturas y a la columna Número Factura.
    
    Colores según columna de CruceFacturas:
    - B: Verde (Facturas Ok)
    - D: Amarillo (Facturas Pendientes)
    - F: Rojo (PDFs)
    
    Args:
        cruce_sheet: Hoja CruceFacturas
        data_sheet: Hoja de datos
        numero_factura_col: Letra de la columna Número Factura
    
    Returns:
        Dict con información de las reglas aplicadas
    """
    max_data_row = data_sheet.max_row
    
    # Configuración: (columna, color)
    columns_config = [
        ("B", COLOR_GREEN),   # Facturas Ok
        ("D", COLOR_YELLOW),  # Facturas Pendientes
        ("F", COLOR_RED),     # PDFs
    ]
    
    # Aplicar formato a columnas de CruceFacturas
    for col_letter, color in columns_config:
        fill = create_fill(color)
        header_cell = f"{col_letter}1"
        
        # Fórmula: si el valor existe en la columna Número Factura
        formula = (
            f"COUNTIF({data_sheet.title}!${numero_factura_col}$2:"
            f"${numero_factura_col}${max_data_row},"
            f"{cruce_sheet.title}!{header_cell})>0"
        )
        
        rule = FormulaRule(formula=[formula], fill=fill)
        cruce_range = f"{col_letter}1:{col_letter}{max_data_row + 50}"
        cruce_sheet.conditional_formatting.add(cruce_range, rule)
        
        logger.debug(
            "Formato condicional aplicado a %s con color %s",
            cruce_range,
            color,
        )
    
    # Aplicar formato a columna Número Factura en hoja de datos
    for col_letter, color in columns_config:
        fill = create_fill(color)
        
        # Fórmula: si el número de factura aparece en la columna de CruceFacturas
        formula = (
            f"=COUNTIF({cruce_sheet.title}!{col_letter}:{col_letter}, "
            f"{numero_factura_col}2)>0"
        )
        
        rule = FormulaRule(formula=[formula], fill=fill)
        data_range = f"{numero_factura_col}2:{numero_factura_col}{max_data_row}"
        data_sheet.conditional_formatting.add(data_range, rule)
        
        logger.debug(
            "Formato condicional aplicado a %s verificando %s!%s",
            data_range,
            cruce_sheet.title,
            col_letter,
        )
    
    return {
        "rule": "cruce_facturas_conditional",
        "applied": True,
        "cruce_columns": ["B", "D", "F"],
    }


def apply_all_conditional_formatting(
    cruce_sheet: Worksheet,
    data_sheet: Worksheet,
) -> list[dict[str, Any]]:
    """
    Aplica todas las reglas de formato condicional.
    
    Args:
        cruce_sheet: Hoja CruceFacturas
        data_sheet: Hoja de datos
    
    Returns:
        Lista de resultados de cada regla aplicada
    """
    results = []
    
    # Buscar columna Número Factura
    numero_factura_col = find_column_letter_by_header(data_sheet, "Número Factura")
    if not numero_factura_col:
        logger.warning("No se encontró columna 'Número Factura' en la hoja de datos")
        return [{"rule": "all_conditional", "applied": False, "reason": "missing_column"}]
    
    # Aplicar reglas de datos
    results.append(apply_conditional_convenio_facturado(data_sheet))
    results.append(apply_conditional_tipo_identificacion(data_sheet))
    
    # Aplicar reglas de cruce
    results.append(apply_conditional_cruce_facturas(
        cruce_sheet, data_sheet, numero_factura_col
    ))
    
    return results
