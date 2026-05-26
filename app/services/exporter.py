"""Servicio orquestador de exportación Excel (solo detección).

Actualmente solo se usa detect_problems_only() — lee un Excel con Polars,
ejecuta detectores y retorna JSON con problemas. Sin exportación ni hojas.
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any

import polars as pl

from app.constants import (
    AREA_ODONTOLOGIA,
    AREA_URGENCIAS,
    AREA_EQUIPOS_BASICOS,
    PROFESIONALES_ODONTOLOGIA,
)
from app.services.equipos_basicos.detect_all import detect_all_problems_equipos_basicos
from app.services.odontologia.detect_all import detect_all_problems_odontologia
from app.services.transversales.column_indices import get_column_indices
from app.services.urgencias.detect_all import detect_all_problems_urgencias
from app.services.processor_gate import (
    SEMAPHORE_TIMEOUT,
    acquire_semaphore,
    release_semaphore,
)
from app.utils.input_data import (
    resolve_safe_excel_absolute,
    resolve_safe_excel_in_input,
)
from app.utils.validators import validate_excel_path

logger = logging.getLogger(__name__)


class _CellValue:
    """Celda mínima — solo el valor, sin style, font, border ni metadata."""
    __slots__ = ("value",)

    def __init__(self, value: Any) -> None:
        self.value = value


class _SimpleSheet:
    """Hoja liviana de solo valores en lista 2D 1-based.

    Interface compatible con openpyxl Worksheet (cell, max_row, max_column)
    pero sin objetos Cell, estilos ni metadata.
    """
    __slots__ = ("_rows", "max_row", "max_column")

    def __init__(self, rows: list[list[Any]]) -> None:
        self._rows = rows  # rows[row][col], 1-based, row=0 y col=0 sin usar
        self.max_row = len(rows) - 1 if rows else 0
        self.max_column = max((len(r) - 1 for r in rows), default=0)

    def cell(self, row: int, column: int) -> _CellValue:
        try:
            return _CellValue(self._rows[row][column])
        except IndexError:
            return _CellValue(None)


def detect_problems_only(
    *,
    filename: str,
    sheet_name: str | None = None,
    area: str = AREA_ODONTOLOGIA,
    profesional: str = "",
    dias: list[int] | None = None,
    todos_profesionales_dias: dict[str, list[int]] | None = None,
    validar_centro_costo: bool = False,
) -> tuple[dict[str, Any], int]:
    """
    Solo detecta problemas en un Excel, SIN exportar ni crear archivos.

    Lee el Excel con Polars, extrae los encabezados, ejecuta los detectores
    y retorna los problemas. No crea hojas, no aplica formato,
    no guarda nada en output/.
    
    Adquiere el semáforo de concurrencia antes de procesar y lo libera
    en un bloque ``finally`` — nunca lo retiene si ocurre una excepción.
    
    Args:
        filename: Ruta al archivo Excel
        sheet_name: Nombre de la hoja (None = activa)
        area: Área del sistema
        profesional: Código del profesional (odontología)
        dias: Días seleccionados (odontología)
        todos_profesionales_dias: Todos los profesionales y días
        validar_centro_costo: Validar centro de costo por días
    
    Returns:
        Tupla (result_dict, status_code) donde status_code es:
        200 en éxito, 503 en timeout del semáforo, 500 en error interno.
    """
    # Adquirir semáforo de concurrencia — si timeout, retornar 503
    if not acquire_semaphore(timeout=SEMAPHORE_TIMEOUT):
        return (
            {
                "status": "error",
                "data": {},
                "errors": [
                    "Servidor ocupado. Intente nuevamente en unos momentos."
                ],
            },
            503,
        )

    try:
        result = _do_detect_problems(
            filename=filename,
            sheet_name=sheet_name,
            area=area,
            profesional=profesional,
            dias=dias,
            todos_profesionales_dias=todos_profesionales_dias,
            validar_centro_costo=validar_centro_costo,
        )
        return (result, 200)
    except Exception:
        logger.exception("Error no capturado en detect_problems_only")
        return (
            {
                "status": "error",
                "data": {},
                "errors": ["Error interno del servidor al procesar el archivo."],
            },
            500,
        )
    finally:
        release_semaphore()


def _do_detect_problems(
    *,
    filename: str,
    sheet_name: str | None = None,
    area: str = AREA_ODONTOLOGIA,
    profesional: str = "",
    dias: list[int] | None = None,
    todos_profesionales_dias: dict[str, list[int]] | None = None,
    validar_centro_costo: bool = False,
) -> dict[str, Any]:
    """
    Implementación interna de la detección de problemas.
    Separada para que detect_problems_only() pueda envolverla con el semáforo.
    Callers deben pasar area=AREA_EQUIPOS_BASICOS para procesar equipos básicos.
    """
    logger.info("Detectando problemas (sin exportar): %s", filename)
    
    # Construir datos para validación de centro costo (odontología/equipos básicos)
    profesional_dias = {}
    permitir_todos_centros = False
    
    if area in (AREA_ODONTOLOGIA, AREA_EQUIPOS_BASICOS):
        if validar_centro_costo and todos_profesionales_dias:
            for prof_codigo, dias_list in todos_profesionales_dias.items():
                if dias_list:
                    profesional_info = PROFESIONALES_ODONTOLOGIA.get(prof_codigo)
                    if profesional_info:
                        profesional_id = profesional_info.get("identificacion")
                        if profesional_id:
                            profesional_dias[profesional_id] = dias_list
            if not profesional_dias:
                permitir_todos_centros = True
        elif validar_centro_costo and profesional and dias:
            profesional_info = PROFESIONALES_ODONTOLOGIA.get(profesional)
            if profesional_info:
                profesional_id = profesional_info.get("identificacion")
                if profesional_id:
                    profesional_dias[profesional_id] = dias
        else:
            permitir_todos_centros = True
    
    # Resolver path
    source_path, source_error = resolve_safe_excel_absolute(filename)
    if source_error:
        return {"status": "error", "data": {}, "errors": [source_error]}
    assert source_path is not None
    
    validation_error = validate_excel_path(source_path)
    if validation_error:
        return {"status": "error", "data": {}, "errors": [validation_error]}
    
    # Leer Excel con Polars/Calamine — sin overhead de objetos Cell
    try:
        df = pl.read_excel(
            source_path,
            engine="calamine",
            has_header=False,
            sheet_name=sheet_name if sheet_name else None,
        )
    except Exception as exc:
        logger.exception("Error leyendo el Excel con Polars")
        return {"status": "error", "data": {}, "errors": [str(exc)]}

    if df.width == 0:
        return {"status": "error", "data": {}, "errors": ["El Excel no tiene columnas"]}

    max_col = df.width

    # Convertir a lista 2D 1-based (formato _SimpleSheet)
    rows: list[list[Any]] = [[None]]  # row=0 sin usar, col=0 sin usar
    for row_data in df.rows():
        row_vals: list[Any] = [None]  # col=0 sin usar
        row_vals.extend(row_data)
        rows.append(row_vals)

    del df

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
        "fecha_cierre": "Fecha Cierre",
        "profesional_identificacion": "Identificación Profesional",
        "profesional_atiende": "Profesional Atiende",
        "codigo_profesional": "Código Profesional",
        "responsable_cierra": "Responsable Cierra Facturar",
        "tarifario": "Tarifario",
        "tipo_usuario": "Tipo Usuario",
        "vlr_copago": "Vlr. Copago",
    }

    # --- Auto-detección de fila de headers ---
    # Algunos Excel tienen filas de título antes de los encabezados reales.
    # Escanea las primeras filas buscando una que contenga TODOS los names requeridos.
    MAX_SCAN_ROWS = 20
    nombres_requeridos: set[str] = set()
    for name in required_headers.values():
        name_norm = (
            unicodedata.normalize("NFC", name).strip().replace("\u00a0", " ")
        )
        nombres_requeridos.add(name_norm)

    detected_row = 1  # default: fila 1
    for check_row in range(1, min(len(rows), MAX_SCAN_ROWS + 1)):
        valores_fila: set[str] = set()
        for col in range(1, len(rows[check_row])):
            val = rows[check_row][col]
            if val is not None:
                norm = (
                    unicodedata.normalize("NFC", str(val))
                    .strip()
                    .replace("\u00a0", " ")
                )
                valores_fila.add(norm)
        if nombres_requeridos.issubset(valores_fila):
            detected_row = check_row
            logger.info(
                "Headers detectados automáticamente en fila %d", detected_row
            )
            break

    # Reubicar headers en row=1 si se detectaron más abajo
    # (todos los detectores asumen headers en row=1, datos desde row=2)
    if detected_row > 1:
        clean_rows: list[list[Any]] = [[None]]  # row 0 sin usar
        clean_rows.append(rows[detected_row])  # headers reales en row=1
        for dr in range(detected_row + 1, len(rows)):
            clean_rows.append(rows[dr])
        rows = clean_rows
        logger.info(
            "Headers en fila %d del Excel original → reubicados en row=1 "
            "para procesamiento (%d filas de datos)",
            detected_row, len(rows) - 2,
        )

    # Construir hoja liviana con solo los valores crudos
    sheet = _SimpleSheet(rows)

    # Leer headers de la primera fila
    headers = [sheet.cell(row=1, column=col).value for col in range(1, max_col + 1)]

    indices, missing_columns = get_column_indices(headers, required_headers)
    
    try:
        if area == AREA_URGENCIAS:
            problemas_detectados, responsables_map = detect_all_problems_urgencias(
                sheet, indices,
            )
        elif area == AREA_EQUIPOS_BASICOS:
            problemas_detectados, responsables_map = detect_all_problems_equipos_basicos(
                sheet, indices,
                profesional_dias=profesional_dias,
                permitir_todos_centros=permitir_todos_centros,
            )
        else:
            problemas_detectados, responsables_map = detect_all_problems_odontologia(
                sheet, indices,
                profesional_dias=profesional_dias,
                permitir_todos_centros=permitir_todos_centros,
            )
        
        problemas_detectados["missing_columns"] = missing_columns
        
    except Exception as exc:
        logger.exception("Error detectando problemas")
        return {"status": "error", "data": {}, "errors": [str(exc)]}
    finally:
        del sheet
        del rows
    
    return {
        "status": "success",
        "data": {
            "problemas": problemas_detectados,
            "responsables_map": responsables_map,
        },
        "errors": [],
    }
