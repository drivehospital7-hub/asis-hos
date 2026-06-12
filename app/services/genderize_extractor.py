"""Servicio para extraer datos del Excel de facturas."""
import logging
from typing import Any

import polars as pl
from dataclasses import dataclass

from app.services.transversales.estructura_excel import get_filas_a_eliminar

logger = logging.getLogger(__name__)

# Nombres EXACTOS de columnas
COL_NUMERO_FACTURA = "Número Factura"
COL_PRIMER_APELLIDO = "Primer Apellido"
COL_SEGUNDO_APELLIDO = "Segundo Apellido"
COL_PRIMER_NOMBRE = "Primer Nombre"
COL_SEGUNDO_NOMBRE = "Segundo Nombre"
COL_SEXO = "Sexo"
COL_NUMERO_IDENTIFICACION = "Nº Identificación"
COL_ENTIDAD_COBRAR = "Entidad Cobrar"


@dataclass
class ExtractResult:
    """Resultado de extracción de relación Factura-Nombre-Sexo."""

    numero_factura: str
    primer_apellido: str
    segundo_apellido: str
    primer_nombre: str
    segundo_nombre: str
    nombre_completo: str  # Apellidos + Nombres (solo display)
    sexo: str  # M o F (del Excel)
    nombre_normalizado: str  # Solo Primer+Segundo Nombre (para API)
    numero_identificacion: str = ""  # Nº Identificación del Excel
    entidad_cobrar: str = ""  # Entidad Cobrar del Excel


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
    num_identificacion_col = cols.get(COL_NUMERO_IDENTIFICACION)
    entidad_cobrar_col = cols.get(COL_ENTIDAD_COBRAR)
    primer_apellido_col = cols.get(COL_PRIMER_APELLIDO)
    segundo_apellido_col = cols.get(COL_SEGUNDO_APELLIDO)
    nombre_col = cols.get(COL_PRIMER_NOMBRE)
    segundo_nombre_col = cols.get(COL_SEGUNDO_NOMBRE)
    sexo_col = cols.get(COL_SEXO)
    
    if num_factura_col is None:
        raise ValueError(f"Columna '{COL_NUMERO_FACTURA}' no encontrada. Columnas: {df.columns}")
    if nombre_col is None:
        raise ValueError(f"Columna '{COL_PRIMER_NOMBRE}' no encontrada. Columnas: {df.columns}")
    if sexo_col is None:
        raise ValueError(f"Columna '{COL_SEXO}' no encontrada. Columnas: {df.columns}")
    
    logger.info("Columnas encontradas: %s, %s, %s",
                COL_NUMERO_FACTURA, COL_PRIMER_NOMBRE, COL_SEXO)
    
    results = []
    for row in df.iter_rows(named=True):
        numero_factura = str(row[COL_NUMERO_FACTURA] or "").strip()
        numero_identificacion = str(row.get(COL_NUMERO_IDENTIFICACION, "") or "").strip() if num_identificacion_col is not None else ""
        entidad_cobrar = str(row.get(COL_ENTIDAD_COBRAR, "") or "").strip() if entidad_cobrar_col is not None else ""
        primer_apellido = str(row.get(COL_PRIMER_APELLIDO, "") or "").strip() if primer_apellido_col is not None else ""
        segundo_apellido = str(row.get(COL_SEGUNDO_APELLIDO, "") or "").strip() if segundo_apellido_col is not None else ""
        primer_nombre = str(row[COL_PRIMER_NOMBRE] or "").strip()
        segundo_nombre = str(row.get(COL_SEGUNDO_NOMBRE, "") or "").strip() if segundo_nombre_col is not None else ""
        sexo = str(row[COL_SEXO] or "").strip().upper()
        
        # Skip empty rows
        if not numero_factura or not primer_nombre:
            continue
        
        # --- Display: nombre completo (Apellidos + Nombres) ---
        partes_display = [p for p in [primer_apellido, segundo_apellido, primer_nombre, segundo_nombre] if p]
        nombre_completo = " ".join(partes_display)
        
        # --- API: compound name solo con Primer + Segundo Nombre ---
        compound_name = f"{primer_nombre} {segundo_nombre}".strip() if segundo_nombre else primer_nombre
        
        import unicodedata
        nfd = unicodedata.normalize("NFD", compound_name)
        sin_tilde = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        nombre_normalizado = sin_tilde.lower().strip()
        
        results.append(ExtractResult(
            numero_factura=numero_factura,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            primer_nombre=primer_nombre,
            segundo_nombre=segundo_nombre,
            nombre_completo=nombre_completo,
            sexo=sexo,
            nombre_normalizado=nombre_normalizado,
            numero_identificacion=numero_identificacion,
            entidad_cobrar=entidad_cobrar,
        ))
    
    logger.info("Extraídos %d registros", len(results))
    return results