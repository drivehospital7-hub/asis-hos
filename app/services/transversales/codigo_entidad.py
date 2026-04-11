"""Regla transversal: Comparar Cód Entidad Cobrar vs Entidad Afiliación.

Este módulo contiene la lógica para comparar el código de entidad a cobrar
con la entidad de afiliación del paciente.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Regex para extraer código de entidad desde texto como:
# "EMSSANAR ENTIDAD PROMOTORA DE SALUD S.A.S. - {ESSC18} «Contributivo»"
CODIGO_ENTIDAD_REGEX = re.compile(r'\{([A-Z0-9]+)\}')


def _extraer_codigo_entidad(texto: str) -> str | None:
    """Extrae el código de entidad desde el texto de Entidad Afiliación.
    
    Ejemplo: "EMSSANAR ENTIDAD PROMOTORA DE SALUD S.A.S. - {ESSC18} «Contributivo»"
    Retorna: "ESSC18"
    """
    if not texto:
        return None
    
    match = CODIGO_ENTIDAD_REGEX.search(texto)
    if match:
        return match.group(1)
    return None


def detect_codigo_entidad_vs_entidad_afiliacion(
    data_sheet: Any,
    indices: dict[str, int | None],
    *,
    limit_log: int = 5,
) -> list[dict[str, str]]:
    """
    Compara las columnas 'Cód Entidad Cobrar' vs 'Entidad Afiliación'.
    
    Esta regla transversal detecta discrepancias donde el código de entidad
    a cobrar no corresponde con la entidad de afiliación del paciente.
    
    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Diccionario con índices de columnas
        limit_log: Número de filas a loguear (default: 5)
    
    Returns:
        Lista de problemas detectados con keys: "factura", "cod_entidad_cobrar", "entidad_afiliacion"
    """
    codigo_entidad_cobrar_idx = indices.get("codigo_entidad_cobrar")
    entidad_afiliacion_idx = indices.get("entidad_afiliacion")
    
    if codigo_entidad_cobrar_idx is None or entidad_afiliacion_idx is None:
        logger.warning(
            "Columnas requeridas no encontradas para validar Cód Entidad Cobrar vs Entidad Afiliación. "
            "codigo_entidad_cobrar=%s, entidad_afiliacion=%s",
            codigo_entidad_cobrar_idx,
            entidad_afiliacion_idx,
        )
        return []
    
    problemas = []
    logged_count = 0
    facturas_ya_procesadas = set()  # Para no repetir facturas
    
    # Obtener también el índice de número de factura para mejor identificación
    numero_factura_idx = indices.get("numero_factura")
    
    for row in range(2, data_sheet.max_row + 1):
        # Obtener valores
        codigo_entidad_cobrar = data_sheet.cell(
            row=row, column=codigo_entidad_cobrar_idx + 1
        ).value
        entidad_afiliacion = data_sheet.cell(
            row=row, column=entidad_afiliacion_idx + 1
        ).value
        
        # Normalizar valores
        codigo_str = (
            str(codigo_entidad_cobrar).strip()
            if codigo_entidad_cobrar is not None
            else ""
        )
        entidad_str = (
            str(entidad_afiliacion).strip()
            if entidad_afiliacion is not None
            else ""
        )
        
        # Solo procesar filas con datos en ambas columnas
        if not codigo_str or not entidad_str:
            continue
        
        # Extraer código de entidad desde "Entidad Afiliación"
        codigo_extraido = _extraer_codigo_entidad(entidad_str)
        
        # Obtener número de factura para mejor identificación
        numero_factura = ""
        if numero_factura_idx is not None:
            num_fact = data_sheet.cell(row=row, column=numero_factura_idx + 1).value
            if num_fact is not None:
                numero_factura = str(num_fact).strip()
        
        # VALIDACIÓN: Comparar Cód Entidad Cobrar vs código extraído de Entidad Afiliación
        # Solo validamos si se pudo extraer código de la afiliación
        if codigo_extraido and codigo_str.upper() != codigo_extraido.upper():
            # Los códigos no coinciden - registrar como problema (si no está repetido)
            if numero_factura and numero_factura in facturas_ya_procesadas:
                continue  # Ya procesamos esta factura
            
            if numero_factura:
                facturas_ya_procesadas.add(numero_factura)
            
            problemas.append({
                "factura": numero_factura,
                "codigo_entidad_cobrar": codigo_str,
                "entidad_afiliacion": entidad_str,
                "codigo_extraido_afiliacion": codigo_extraido,
                "problema": "Cód Entidad Cobrar no coincide con código en Entidad Afiliación",
            })
            # Loguear error (todas las no-coincidencias)
            logger.warning(
                "VALIDACIÓN FALSA - Fila %s (Factura: %s): Cód Entidad Cobrar='%s' vs Código Extraído='%s' | Entidad Afiliación: '%s'",
                row,
                numero_factura,
                codigo_str,
                codigo_extraido,
                entidad_str,
            )
        elif logged_count < limit_log:
            # Solo loggear las primeras N filas que coinciden (o no tienen código extraído)
            logger.info(
                "DEBUG Fila %s (Factura: %s) - Cód Entidad Cobrar: '%s' | Entidad Afiliación: '%s' | Código Extraído: '%s' | COINCIDE: ✓",
                row,
                numero_factura,
                codigo_str,
                entidad_str,
                codigo_extraido or "(NO ENCONTRADO)",
            )
            logged_count += 1
    
    logger.info(
        "Total filas procesadas para Cód Entidad Cobrar vs Entidad Afiliación: %d",
        len(problemas),
    )
    
    return problemas


def detect_codigo_entidad_vs_entidad_afiliacion_simple(
    file_path: str,
    sheet_name: str | None = None,
    *,
    limit_rows: int = 5,
) -> dict[str, Any]:
    """
    Versión simple que lee directamente del archivo Excel.
    
    Útil para verificación rápida sin necesidad de pasar el data_sheet.
    
    Args:
        file_path: Ruta al archivo Excel
        sheet_name: Nombre de la hoja (None = primera hoja)
        limit_rows: Número de filas a mostrar en log
    
    Returns:
        Dict con status, data y errors
    """
    import polars as pl
    from pathlib import Path
    
    from app.constants import ALLOWED_EXCEL_SUFFIXES
    
    path = Path(file_path).expanduser().resolve()
    
    if not path.is_file():
        return {
            "status": "error",
            "data": {},
            "errors": [f"Archivo no encontrado: {file_path}"],
        }
    
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        return {
            "status": "error",
            "data": {},
            "errors": [f"Formato no soportado: {suffix}"],
        }
    
    try:
        # Leer Excel
        read_opts: dict[str, Any] = {
            "n_rows": limit_rows + 1,  # +1 para el header
            "header_row": 0,
        }
        read_kwargs: dict[str, Any] = {
            "source": str(path),
            "engine": "calamine",
            "read_options": read_opts,
            "infer_schema_length": None,
        }
        
        if sheet_name is not None:
            read_kwargs["sheet_name"] = sheet_name
        
        df = pl.read_excel(**read_kwargs)
        
        # Buscar columnas
        codigo_col = None
        afiliacion_col = None
        
        for col in df.columns:
            col_normalized = col.strip().lower()
            if "cód entidad cobrar" in col_normalized or "cod entidad cobrar" in col_normalized:
                codigo_col = col
            if "entidad afiliación" in col_normalized or "entidad afiliacion" in col_normalized:
                afiliacion_col = col
        
        if codigo_col is None or afiliacion_col is None:
            return {
                "status": "error",
                "data": {},
                "errors": [
                    f"Columnas no encontradas - Cód Entidad Cobrar: {codigo_col}, Entidad Afiliación: {afiliacion_col}"
                ],
            }
        
        # Mostrar las primeras filas
        results = []
        for i in range(min(limit_rows, len(df))):
            row = df.row(i)
            codigo_idx = df.columns.index(codigo_col)
            afiliacion_idx = df.columns.index(afiliacion_col)
            
            results.append({
                "row": i + 1,
                "codigo_entidad_cobrar": str(row[codigo_idx]) if row[codigo_idx] is not None else "",
                "entidad_afiliacion": str(row[afiliacion_idx]) if row[afiliacion_idx] is not None else "",
            })
            
            logger.info(
                "Fila %d - Cód Entidad Cobrar: '%s' | Entidad Afiliación: '%s'",
                i + 1,
                results[-1]["codigo_entidad_cobrar"],
                results[-1]["entidad_afiliacion"],
            )
        
        return {
            "status": "success",
            "data": {
                "filas_mostradas": len(results),
                "columnas": {
                    "codigo_entidad_cobrar": codigo_col,
                    "entidad_afiliacion": afiliacion_col,
                },
                "resultados": results,
            },
            "errors": [],
        }
        
    except Exception as exc:
        logger.exception("Error procesando archivo Excel")
        return {
            "status": "error",
            "data": {},
            "errors": [str(exc)],
        }