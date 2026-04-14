"""Verificación de códigos CUPS contra la base de datos.

Para Urgencias - Entidad ESS118:
Busca códigos en la columna "Código" que no existen en la DB (EMSSANAR_CAPITA).

Uso:
    python -m app.services.verificar_codigos_urgencias <ruta_excel>
"""

import sys
import logging
from pathlib import Path

import polars as pl
from openpyxl import load_workbook

from app.services.procedimientos_db import get_procedimiento

logger = logging.getLogger(__name__)

# Constantes
EPS_DB = "EMSSANAR_CAPITA"


def get_indices(sheet) -> dict:
    """Detector índices de columnas."""
    headers = [cell.value for cell in sheet[1]]
    
    indices = {}
    for idx, header in enumerate(headers):
        if header:
            header_lower = str(header).strip().lower()
            indices[header_lower] = idx
    
    return indices


def verificar_excel(excel_path: str | Path) -> dict:
    """Procesa el Excel y verifica códigos contra DB.
    
    Returns:
        Dict con:
        - codigos_no_encontrados: list of codigos
        - codigos_encontrados: list of codigos
        - total ESS118: int
    """
    excel_path = Path(excel_path)
    
    if not excel_path.exists():
        logger.error("Archivo no encontrado: %s", excel_path)
        return {}
    
    # Cargar workbook
    wb = load_workbook(excel_path, data_only=True)
    sheet = wb.active
    
    indices = get_indices(sheet)
    logger.info("Índices detectados: %s", indices)
    
    # Buscar columnas relevantes
    codigo_idx = indices.get("codigo")  # columna Código
    entidad_cobrar_idx = indices.get("entidad cobrar") or indices.get("entidad_cobrar")
    codigo_entidad_idx = indices.get("cód entidad cobrar") or indices.get("cod_entidad_cobrar")
    
    if codigo_idx is None:
        logger.error("Columna 'Código' no encontrada")
        return {}
    
    logger.info("Buscando códigos para ESS118...")
    
    # Collect códigos únicos para ESS118
    codigos_ess118 = set()
    
    for row in range(2, sheet.max_row + 1):
        # Leer valores
        entidad_str = None
        if entidad_cobrar_idx is not None:
            entidad_str = sheet.cell(row=row, column=entidad_cobrar_idx + 1).value
        if codigo_entidad_idx is not None:
            codigo_entidad = sheet.cell(row=row, column=codigo_entidad_idx + 1).value
            if codigo_entidad:
                entidad_str = str(codigo_entidad).strip()
        
        codigo = sheet.cell(row=row, column=codigo_idx + 1).value
        
        # Skip empty
        if not codigo:
            continue
        
        codigo_str = str(codigo).strip()
        
        # Filtrar solo ESS118 (por código entidad o nombre entidad)
        es_ess118 = False
        if entidad_str:
            entidad_normalizada = str(entidad_str).strip().upper()
            if "ESS118" in entidad_normalizada:
                es_ess118 = True
        
        if es_ess118:
            codigos_ess118.add(codigo_str)
    
    logger.info("Total códigos únicos para ESS118: %d", len(codigos_ess118))
    
    # Verificar cada código contra la DB
    codigos_no_encontrados = []
    codigos_encontrados = []
    
    for codigo in sorted(codigos_ess118):
        proc = get_procedimiento(EPS_DB, codigo)
        
        if proc:
            codigos_encontrados.append(codigo)
            logger.debug("Encontrado: %s - %s", codigo, proc.descripcion)
        else:
            codigos_no_encontrados.append(codigo)
            logger.warning("NO ENCONTRADO en DB: %s (EPS=%s)", codigo, EPS_DB)
    
    # Resumen
    logger.info("=" * 60)
    logger.info("RESUMEN - Verificación de Códigos para ESS118")
    logger.info("=" * 60)
    logger.info("Total códigos ESS118 únicos: %d", len(codigos_ess118))
    logger.info("Encontrados en DB (%s): %d", EPS_DB, len(codigos_encontrados))
    logger.info("NO encontrados en DB: %d", len(codigos_no_encontrados))
    
    if codigos_no_encontrados:
        logger.warning("Códigos NO encontrados en la DB:")
        for codigo in codigos_no_encontrados:
            logger.warning("  - %s", codigo)
    
    return {
        "codigos_no_encontrados": codigos_no_encontrados,
        "codigos_encontrados": codigos_encontrados,
        "total_ess118": len(codigos_ess118),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Uso: python -m app.services.verificar_codigos_urgencias <archivo_excel>")
        sys.exit(1)
    
    excel_path = sys.argv[1]
    resultado = verificar_excel(excel_path)