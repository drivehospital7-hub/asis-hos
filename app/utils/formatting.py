"""Formato condicional para hojas Excel.

Este módulo contiene las funciones para aplicar formato condicional
a las hojas de Excel (colores según reglas de negocio).
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill, Border, Side
from openpyxl.worksheet.worksheet import Worksheet

from app.constants import (
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    CONVENIO_ASISTENCIAL,
    CENTRO_COSTO_ODONTOLOGIA,
    ENTIDAD_MALLAMAS,
    HEADER_BACKGROUND_COLOR,
    HEADER_BORDER_COLOR,
    DATA_ROW_BACKGROUND_COLOR,
    URGENCIA_HEADER_BACKGROUND_COLOR,
    URGENCIA_HEADER_BORDER_COLOR,
    URGENCIA_DATA_ROW_BACKGROUND_COLOR,
)

logger = logging.getLogger(__name__)


def create_header_style() -> dict:
    """
    Crea un diccionario de estilos para encabezados.
    
    Returns:
        Dict con Font, PatternFill y Border configurados
    """
    from openpyxl.styles import Alignment
    
    # Negrita
    font = Font(bold=True)
    
    # Color de fondo azulado
    fill = PatternFill(
        start_color=HEADER_BACKGROUND_COLOR,
        end_color=HEADER_BACKGROUND_COLOR,
        fill_type="solid",
    )
    
    # Borde azulado
    side = Side(color=HEADER_BORDER_COLOR, style="thin")
    border = Border(left=side, right=side, top=side, bottom=side)
    
    # Alineación a la izquierda
    alignment = Alignment(horizontal="left", vertical="center")
    
    return {
        "font": font,
        "fill": fill,
        "border": border,
        "alignment": alignment,
    }


def create_data_row_style() -> dict:
    """
    Crea un diccionario de estilos para filas de datos (sin negrita).
    
    Returns:
        Dict con PatternFill y Border configurados
    """
    from openpyxl.styles import Alignment
    
    # Color de fondo azulado muy claro (sin negrita)
    fill = PatternFill(
        start_color=DATA_ROW_BACKGROUND_COLOR,
        end_color=DATA_ROW_BACKGROUND_COLOR,
        fill_type="solid",
    )
    
    # Borde azulado claro
    side = Side(color="B4C7E7", style="thin")
    border = Border(left=side, right=side, top=side, bottom=side)
    
    # Alineación a la izquierda
    alignment = Alignment(horizontal="left", vertical="center")
    
    return {
        "fill": fill,
        "border": border,
        "alignment": alignment,
    }


def create_urgencia_header_style() -> dict:
    """
    Crea un diccionario de estilos para headers de Revision Urgencias.
    
    Características:
    - Negrita
    - Fondo rojo claro
    - Bordes rojos
    
    Returns:
        Dict con Font, PatternFill y Border configurados
    """
    from openpyxl.styles import Alignment
    
    # Negrita
    font = Font(bold=True)
    
    # Color de fondo rojo claro
    fill = PatternFill(
        start_color=URGENCIA_HEADER_BACKGROUND_COLOR,
        end_color=URGENCIA_HEADER_BACKGROUND_COLOR,
        fill_type="solid",
    )
    
    # Borde rojo
    side = Side(color=URGENCIA_HEADER_BORDER_COLOR, style="thin")
    border = Border(left=side, right=side, top=side, bottom=side)
    
    # Alineación a la izquierda
    alignment = Alignment(horizontal="left", vertical="center")
    
    return {
        "font": font,
        "fill": fill,
        "border": border,
        "alignment": alignment,
    }


def create_urgencia_data_row_style() -> dict:
    """
    Crea un diccionario de estilos para filas de datos de Revision Urgencias.
    
    Características:
    - Fondo rojo claro
    - Bordes rojos
    
    Returns:
        Dict con PatternFill y Border configurados
    """
    from openpyxl.styles import Alignment
    
    # Color de fondo rojo muy claro
    fill = PatternFill(
        start_color=URGENCIA_DATA_ROW_BACKGROUND_COLOR,
        end_color=URGENCIA_DATA_ROW_BACKGROUND_COLOR,
        fill_type="solid",
    )
    
    # Borde rojo
    side = Side(color=URGENCIA_HEADER_BORDER_COLOR, style="thin")
    border = Border(left=side, right=side, top=side, bottom=side)
    
    # Alineación a la izquierda
    alignment = Alignment(horizontal="left", vertical="center")
    
    return {
        "fill": fill,
        "border": border,
        "alignment": alignment,
    }


def auto_adjust_column_width(sheet: Worksheet, max_rows: int = 10) -> dict[str, int]:
    """
    Ajusta el ancho de las columnas según el contenido de las celdas.
    
    Args:
        sheet: Hoja de Excel
        max_rows: Número de filas a evaluar para calcular el ancho máximo
    
    Returns:
        Dict con letra de columna -> ancho ajustado
    """
    from openpyxl.utils import get_column_letter
    
    column_widths = {}
    
    for col in range(1, sheet.max_column + 1):
        col_letter = get_column_letter(col)
        max_length = 0
        
        for row in range(1, min(max_rows + 1, sheet.max_row + 1)):
            cell = sheet.cell(row=row, column=col)
            if cell.value:
                cell_length = len(str(cell.value))
                # Ajustar por caracteres chinos/unicode
                max_length = max(max_length, cell_length)
        
        # Ancho con padding (mínimo 8, máximo 50)
        if max_length > 0:
            adjusted_width = min(max(max_length + 2, 8), 50)
            sheet.column_dimensions[col_letter].width = adjusted_width
            column_widths[col_letter] = adjusted_width
    
    logger.debug("Anchos de columnas ajustados: %s", column_widths)
    return column_widths


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
    identificacion_col: str | None = None,
) -> dict[str, Any]:
    """
    Aplica formato condicional a la hoja CruceFacturas y a las columnas de datos.
    
    Colores según columna de CruceFacturas:
    - B: Verde (Cruce Facturas - coincide con Número Factura)
    - D: Amarillo (Cruce Identificación - coincide con Nº Identificación)
    
    Args:
        cruce_sheet: Hoja CruceFacturas
        data_sheet: Hoja de datos
        numero_factura_col: Letra de la columna Número Factura
        identificacion_col: Letra de la columna Nº Identificación (opcional)
    
    Returns:
        Dict con información de las reglas aplicadas
    """
    max_data_row = data_sheet.max_row
    
    # Configuración para Cruce Facturas (columna B - verde)
    # Comprobar contra Número Factura
    fill_b = create_fill(COLOR_GREEN)
    formula_b = (
        f"COUNTIF({data_sheet.title}!${numero_factura_col}$2:"
        f"${numero_factura_col}${max_data_row},"
        f"{cruce_sheet.title}!B2)>0"
    )
    rule_b = FormulaRule(formula=[formula_b], fill=fill_b)
    cruce_range_b = f"B2:B{max_data_row + 50}"
    cruce_sheet.conditional_formatting.add(cruce_range_b, rule_b)
    
    logger.debug(
        "Formato condicional aplicado a %s con color verde (Número Factura)",
        cruce_range_b,
    )
    
    # Configuración para Cruce Identificación (columna D - amarillo)
    # Comprobar contra Nº Identificación
    if identificacion_col:
        fill_d = create_fill(COLOR_YELLOW)
        formula_d = (
            f"COUNTIF({data_sheet.title}!${identificacion_col}$2:"
            f"${identificacion_col}${max_data_row},"
            f"{cruce_sheet.title}!D2)>0"
        )
        rule_d = FormulaRule(formula=[formula_d], fill=fill_d)
        cruce_range_d = f"D2:D{max_data_row + 50}"
        cruce_sheet.conditional_formatting.add(cruce_range_d, rule_d)
        
        logger.debug(
            "Formato condicional aplicado a %s con color amarillo (Nº Identificación)",
            cruce_range_d,
        )
    
    # Aplicar formato a columna Número Factura en hoja de datos (verde)
    fill_b_data = create_fill(COLOR_GREEN)
    formula_b_data = (
        f"=COUNTIF({cruce_sheet.title}!B:B, {numero_factura_col}2)>0"
    )
    rule_b_data = FormulaRule(formula=[formula_b_data], fill=fill_b_data)
    data_range_b = f"{numero_factura_col}2:{numero_factura_col}{max_data_row}"
    data_sheet.conditional_formatting.add(data_range_b, rule_b_data)
    
    logger.debug(
        "Formato condicional aplicado a %s verificando Cruce Facturas",
        data_range_b,
    )
    
    # Aplicar formato a columna Nº Identificación en hoja de datos (amarillo)
    if identificacion_col:
        fill_d_data = create_fill(COLOR_YELLOW)
        formula_d_data = (
            f"=COUNTIF({cruce_sheet.title}!D:D, {identificacion_col}2)>0"
        )
        rule_d_data = FormulaRule(formula=[formula_d_data], fill=fill_d_data)
        data_range_d = f"{identificacion_col}2:{identificacion_col}{max_data_row}"
        data_sheet.conditional_formatting.add(data_range_d, rule_d_data)
        
        logger.debug(
            "Formato condicional aplicado a %s verificando Cruce Identificación",
            data_range_d,
        )
    
    return {
        "rule": "cruce_facturas_conditional",
        "applied": True,
        "cruce_columns": ["B", "D"],
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
    
    # Buscar columna Nº Identificación
    identificacion_col = find_column_letter_by_header(data_sheet, "Nº Identificación")
    if not identificacion_col:
        logger.warning("No se encontró columna 'Nº Identificación' en la hoja de datos")
    
    # Aplicar reglas de datos (solo conveniencia - tipo identificación se muestra en HTML)
    results.append(apply_conditional_convenio_facturado(data_sheet))
    
    # Aplicar reglas de cruce
    results.append(apply_conditional_cruce_facturas(
        cruce_sheet, data_sheet, numero_factura_col, identificacion_col
    ))
    
    return results
