"""Servicio orquestador de exportación Excel.

Este módulo es el punto de entrada principal para la exportación de archivos
Excel con hojas de cruce y revisión. Coordina los demás módulos:
- validators: Validación de paths
- column_filter: Filtrado de columnas
- cruce_sheet: Creación de hoja CruceFacturas
- revision_sheet: Creación de hoja Revision
- formatting: Formato condicional
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.constants import (
    CRUCE_FACTURAS_SHEET,
    REVISION_SHEET,
    AREA_ODONTOLOGIA,
    AREA_URGENCIAS,
    REVISION_HEADERS,
    URGENCIA_REVISION_HEADERS,
    COLUMNS_TO_KEEP,
    URGENCIA_COLUMNS_TO_KEEP,
)
from app.services.cruce_sheet import create_cruce_facturas_sheet
from app.services.revision_sheet import create_revision_sheet
from app.utils.column_filter import filter_columns
from app.utils.formatting import apply_all_conditional_formatting
from app.utils.input_data import (
    resolve_safe_excel_absolute,
    resolve_safe_excel_in_input,
    resolve_safe_excel_in_output,
)
from app.utils.validators import validate_excel_path

logger = logging.getLogger(__name__)


def _copy_file(source: Path, destination: Path) -> None:
    """Copia el archivo fuente al destino."""
    shutil.copy2(source, destination)
    logger.info("Archivo copiado: %s -> %s", source.name, destination.name)


def export_excel_with_cruce_facturas(
    *,
    filename: str,
    sheet_name: str | None = None,
    header_row: int = 0,
    area: str = AREA_ODONTOLOGIA,
) -> dict[str, Any]:
    """
    Exporta un archivo Excel con hojas de cruce y revisión.
    
    Este es el orquestador principal que:
    1. Valida el archivo de entrada
    2. Copia el archivo a output
    3. Filtra columnas de la hoja de datos
    4. Crea hoja CruceFacturas con headers
    5. Crea hoja Revision con problemas detectados (según área)
    6. Aplica formato condicional
    7. Guarda el archivo
    
    Args:
        filename: Nombre del archivo en input/
        sheet_name: Nombre de la hoja a procesar (None = hoja activa)
        header_row: Fila de headers (no usado actualmente, reservado para futuro)
        area: Área del sistema ("odontologia" o "urgencias")
    
    Returns:
        Dict con formato estándar:
        {
            "status": "success" | "error",
            "data": {...},
            "errors": [...]
        }
    """
    logger.info("Iniciando exportación: %s", filename)
    
    # 1. Resolver y validar path de entrada (soporta repo o archivo subido)
    source_path, source_error = resolve_safe_excel_absolute(filename)
    if source_error:
        logger.error("Error resolviendo archivo de entrada: %s", source_error)
        return {"status": "error", "data": {}, "errors": [source_error]}
    assert source_path is not None
    
    validation_error = validate_excel_path(source_path)
    if validation_error:
        logger.error("Error de validación: %s", validation_error)
        return {"status": "error", "data": {}, "errors": [validation_error]}
    
    # 2. Resolver path de salida
    # Usar nombre original del archivo (sin el UUID del temp upload)
    original_filename = Path(filename).name
    if "_" in original_filename:
        # Es un archivo temporal: extraer nombre original despues del UUID
        parts = original_filename.split("_", 1)
        if len(parts) == 2 and len(parts[0]) == 32:  # UUID es 32 hex chars
            original_filename = parts[1]
    
    output_path, output_error = resolve_safe_excel_in_output(original_filename)
    if output_error:
        logger.error("Error resolviendo archivo de salida: %s", output_error)
        return {"status": "error", "data": {}, "errors": [output_error]}
    assert output_path is not None
    
    try:
        # 3. Copiar archivo a output
        _copy_file(source_path, output_path)
        
        # 4. Cargar workbook
        workbook = load_workbook(output_path)
        
        # 5. Obtener hoja de datos
        if sheet_name and sheet_name in workbook.sheetnames:
            data_sheet = workbook[sheet_name]
        else:
            data_sheet = workbook.active
        
        # 6. Filtrar columnas (según el área)
        if area == AREA_URGENCIAS:
            # Urgencias: no ocultar columnas (None = mantener todas)
            columns_to_keep = None
        else:
            columns_to_keep = COLUMNS_TO_KEEP
        
        filter_result = filter_columns(data_sheet, columns_to_keep=columns_to_keep)
        logger.info("Columnas filtradas: %s", filter_result)
        
        # 7. Crear hoja Revision (según el área)
        revision_info = create_revision_sheet(workbook, area=area)
        
        # 8. Crear hoja CruceFacturas
        cruce_sheet, cruce_info = create_cruce_facturas_sheet(workbook)
        
        # 9. Mover CruceFacturas a última posición (después de Revision)
        cruce_sheet_obj = workbook[CRUCE_FACTURAS_SHEET]
        workbook.move_sheet(cruce_sheet_obj, offset=1)
        
        # 10. Aplicar formato condicional
        formatting_results = apply_all_conditional_formatting(cruce_sheet, data_sheet)
        
        # 10. Guardar
        workbook.save(output_path)
        logger.info("Archivo guardado: %s", output_path.name)
        
    except Exception as exc:
        logger.exception("Error exportando Excel")
        return {"status": "error", "data": {}, "errors": [str(exc)]}
    
    logger.info("Exportación completada: %s", output_path.name)
    
    return {
        "status": "success",
        "data": {
            "input_file": source_path.name,
            "output_file": output_path.name,
            "output_path": str(output_path),
            "sheet": CRUCE_FACTURAS_SHEET,
            "headers_written": ["B1", "D1", "F1"],
            "filter_result": filter_result,
            "applied_rules": [
                cruce_info,
                revision_info,
                *formatting_results,
            ],
        },
        "errors": [],
    }
