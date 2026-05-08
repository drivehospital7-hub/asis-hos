"""Servicio para extraer datos del Excel de facturas."""
import logging
from typing import Any

import polars as pl
from dataclasses import dataclass

from app.services.transversales.estructura_excel import get_filas_a_eliminar

logger = logging.getLogger(__name__)

# Nombres EXACTOS de columnas
COL_NUMERO_FACTURA = "Número Factura"
COL_PRIMER_NOMBRE = "Primer Nombre"
COL_SEXO = "Sexo"


@dataclass
class ExtractResult:
    """Resultado de extracción de relación Factura-Nombre-Sexo."""

    numero_factura: str
    primer_nombre: str
    sexo: str  # M o F (del Excel)
    nombre_normalizado: str


def extract_factura_nombre_sexo(excel_path: str) -> list[ExtractResult]:
    """Extrae relación Numero Factura - Primer Nombre - Sexo del Excel.
    
    Args:
        excel_path: Path al archivo Excel.
        
    Returns:
        Lista de ExtractResult con los datos.
    """
    logger.info("Extrayendo datos de: %s", excel_path)
    
    # Detectar estructura del Excel (filas de encabezado a saltar)
    filas_skip = get_filas_a_eliminar(excel_path)
    logger.info("Filas a saltar según estructura detectada: %d", filas_skip)

    # Leer Excel indicando cuál fila contiene los headers
    # Polars usa esa fila como headers y lee los datos después
    read_opts: dict[str, Any] = {"header_row": filas_skip}
    df = pl.read_excel(excel_path, engine="calamine", read_options=read_opts)
    
    # Buscar columnas exactas (case-sensitive)
    cols = {c: i for i, c in enumerate(df.columns)}
    
    num_factura_col = cols.get(COL_NUMERO_FACTURA)
    nombre_col = cols.get(COL_PRIMER_NOMBRE)
    sexo_col = cols.get(COL_SEXO)
    
    if num_factura_col is None:
        raise ValueError(f"Columna '{COL_NUMERO_FACTURA}' no encontrada. Columnas: {df.columns}")
    if nombre_col is None:
        raise ValueError(f"Columna '{COL_PRIMER_NOMBRE}' no encontrada. Columnas: {df.columns}")
    if sexo_col is None:
        raise ValueError(f"Columna '{COL_SEXO}' no encontrada. Columnas: {df.columns}")
    
    logger.info("Columnas encontradas: %s, %s, %s", COL_NUMERO_FACTURA, COL_PRIMER_NOMBRE, COL_SEXO)
    
    results = []
    for row in df.iter_rows(named=True):
        numero_factura = str(row[COL_NUMERO_FACTURA] or "").strip()
        primer_nombre = str(row[COL_PRIMER_NOMBRE] or "").strip()
        sexo = str(row[COL_SEXO] or "").strip().upper()
        
        # Skip empty rows
        if not numero_factura or not primer_nombre:
            continue
        
        # Normalizar (minúsculas, sin tildes)
        import unicodedata
        nfd = unicodedata.normalize("NFD", primer_nombre)
        sin_tilde = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        nombre_normalizado = sin_tilde.lower().strip()
        
        results.append(ExtractResult(
            numero_factura=numero_factura,
            primer_nombre=primer_nombre,
            sexo=sexo,
            nombre_normalizado=nombre_normalizado,
        ))
    
    logger.info("Extraídos %d registros", len(results))
    return results