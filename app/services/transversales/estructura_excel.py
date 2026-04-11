"""Detección automática de estructura del Excel.

Este módulo determina si el Excel tiene las filas de encabezado a eliminar
o si ya viene limpio (headers en fila 1).
"""

from __future__ import annotations

import logging
import unicodedata
from pathlib import Path
from typing import Any

import polars as pl

from app.constants import ALLOWED_EXCEL_SUFFIXES

logger = logging.getLogger(__name__)


# Headers esperados cuando el Excel YA tiene headers en fila 1 (limpio)
# Estos son los headers típicos del Excel de MALLAMAS (odontología)
EXPECTED_HEADERS_LIMPIO: set[str] = {
    "XML DIAN",
    "Fecha XML",
    "Fecha Adjunto",
    "Historia Clínica",
    "Cód Entidad Cobrar",
    "Entidad Cobrar",
    "Tipo Entidad Cobrar",
    "Nº Cuenta Cobro",
    "Cuenta Radica",
    "Número Radicado",
    "Fac. Trans.",
    "Número Factura",
    "CUFE",
    "Nº Factura Migración",
    "Tipo Factura Descripción",
    "PyMs",
    "Genera Historia",
    "Mes Factura",
    "Año Factura",
    "Fec. Factura",
    "Fecha Cierre",
    "Fecha Modifica",
    "IDE Contrato",
    "Nº Contrato",
    "Tipo Contrato",
    "Contratado por",
    "Convenio Facturado",
    "Cód. Tarifario",
    "Tarifario",
    "Observación",
    "Nº Reingreso",
    "Fecha Último Reingreso",
    "Código Tipo Procedimiento",
    "Tipo Procedimiento",
    "Nº Solicitud Laboratorio",
    "Laboratorio",
    "Laboratorio Pendiente",
    "Vacuna",
    "Vacuna Pendiente",
    "ID",
    "Alto Riesgo",
    "LASA",
    "Código",
    "Cód. Equivalente CUPS",
    "CUM",
    "Procedimiento",
    "Cantidad",
    "Vlr. Procedimiento",
    "Vlr. Subsidiado",
    "Vlr. Copago",
    "Concentración",
    "Centro Costo",
    "Área Trabajo",
    "Forma Farmacéutica",
    "Principio Activo",
    "Presentación Comercial",
    "Unidad Medida",
    "Fec. Procedimiento",
    "Identificación Profesional",
    "Código Profesional",
    "Profesional Atiende",
    "Responsable Abre Facturar",
    "Responsable Cierra Facturar",
    "Responsable Última Modificación Facturar",
    "Tipo Identificación",
    "Nombre Tipo Identificación",
    "Nº Identificación",
    "Primer Apellido",
    "Segundo Apellido",
    "Primer Nombre",
    "Segundo Nombre",
    "Tipo Entidad Afilicación",
    "Entidad Afiliación",
    "Curso Vida",
    "Edad",
    "Medidad Edad",
    "Edad Completa",
    "Cód. Tipo Usuario",
    "Tipo Usuario",
    "Sexo",
    "Grupo Sisbén IV",
    "Discapacitado",
    "Descripción Discapacidad",
    "Código Etnia",
    "Etnia",
    "Código Grupo Indígena",
    "Grupo Indígena",
    "Nombre Alterno",
    "Fec. Nacimiento",
    "Teléfono",
    "Celular",
    "Cód. Depto.",
    "Departamento",
    "Cód. Municipio",
    "Municipio",
    "Cód. Barrio",
    "Barrio",
    "Zona",
    "Comuna",
    "Codigo",
    "Grupo Especial",
    "Victima Conflicto",
    "RIPS",
    "Veces Consulta",
    "Causa Externa",
    "Nombre Causa Externa",
    "Finalidad",
    "Nombre Finalidad",
    "Cód. Dx Ingreso",
    "Dx Ingreso",
    "Cód. Dx Principal",
    "Dx Principal",
    "Cód. Dx Relacionado 1",
    "Dx Relacionado 1",
    "Cód. Dx Relacionado 2",
    "Dx Relacionado 2",
    "Cód. Dx Relacionado 3",
    "Dx Relacionado 3",
    "Diagnóstico Complicación",
    "Dx Complicación",
    "Diagnóstico Causa Muerte",
    "Dx Causa Muerte",
    "Diagnóstico Muerte Madre",
    "Dx Muerte Madre",
    "Cód. Forma Quirúrgica",
    "Forma Quirúrgica",
    "Cód. Tipo Servicio",
    "Tipo Servicio",
    "RIPS Pendiente",
    "Reporta Rips",
    "Cita",
    "Tipo Cita",
}

# Umbral de coincidencia para considerar que el Excel ya está limpio
# Si al menos el 70% de los headers esperados están en la primera fila, está limpio
UMBRAL_COINCIDENCIA: float = 0.70


def _normalize_header(header: str) -> str:
    """Normaliza un header para comparación flexible."""
    if header is None:
        return ""
    header = str(header).strip().lower()
    # Eliminar acentos
    normalized = unicodedata.normalize("NFD", header)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _read_headers_from_excel(
    file_path: str | Path,
    *,
    sheet_name: str | None = None,
    sheet_id: int | None = None,
    header_row: int = 0,
) -> list[str] | None:
    """
    Lee los headers de la primera fila del Excel usando Polars.
    
    Returns:
        Lista de headers o None si hay error.
    """
    path = Path(file_path).expanduser().resolve()
    
    if not path.is_file():
        logger.error("Archivo no encontrado: %s", path)
        return None
    
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXCEL_SUFFIXES:
        logger.error("Formato no soportado: %s", suffix)
        return None
    
    read_opts: dict[str, Any] = {"n_rows": 0, "header_row": header_row}
    read_kwargs: dict[str, Any] = {
        "source": str(path),
        "engine": "calamine",
        "read_options": read_opts,
        "infer_schema_length": 0,
        "drop_empty_rows": False,
        "drop_empty_cols": False,
        "raise_if_empty": False,
    }
    
    if sheet_name is not None:
        read_kwargs["sheet_name"] = sheet_name
    elif sheet_id is not None:
        read_kwargs["sheet_id"] = sheet_id
    
    try:
        df = pl.read_excel(**read_kwargs)
        if df.width == 0:
            logger.warning("No hay columnas en la hoja")
            return None
        
        headers = []
        for name in df.columns:
            if isinstance(name, str):
                headers.append(name.strip())
            else:
                headers.append(str(name).strip())
        
        return headers
    except Exception as exc:
        logger.exception("Error leyendo headers del Excel")
        return None


def detectar_estructura_excel(
    file_path: str | Path,
    *,
    sheet_name: str | None = None,
    sheet_id: int | None = None,
    rows_to_eliminar_default: int = 2,
    umbral: float = UMBRAL_COINCIDENCIA,
) -> dict[str, Any]:
    """
    Detecta la estructura del Excel para determinar si hay filas de encabezado a eliminar.
    
    Lógica:
    - Lee los headers de la primera fila
    - Compara con los headers esperados de un Excel limpio
    - Si coinciden en al menos 'umbral'% → los headers ya están en fila 1 → NO eliminar
    - Si no coinciden → probably hay filas de encabezado → SÍ eliminar
    
    Args:
        file_path: Ruta al archivo Excel
        sheet_name: Nombre de la hoja (None = hoja activa)
        sheet_id: ID de la hoja (None = hoja activa)
        rows_to_eliminar_default: Filas a eliminar si se detecta estructura con encabezados (default: 2)
        umbral: Porcentaje de coincidencia para considerar Excel limpio (default: 0.70)
    
    Returns:
        Dict con estructura:
        {
            "status": "success",
            "data": {
                "estructura": "limpia" | "con_encabezados",
                "filas_a_eliminar": 0 | 2,
                "headers_encontrados": [...],
                "coincidencia": 0.75,
            },
            "errors": []
        }
    """
    logger.info("Detectando estructura Excel: %s", Path(file_path).name)
    
    headers = _read_headers_from_excel(
        file_path,
        sheet_name=sheet_name,
        sheet_id=sheet_id,
        header_row=0,
    )
    
    if headers is None:
        return {
            "status": "error",
            "data": {},
            "errors": ["No se pudieron leer los headers del Excel"],
        }
    
    if not headers:
        return {
            "status": "error",
            "data": {},
            "errors": ["El Excel no tiene headers en la primera fila"],
        }
    
    # Normalizar headers esperados y encontrados
    normalized_expected = {_normalize_header(h) for h in EXPECTED_HEADERS_LIMPIO}
    normalized_found = {_normalize_header(h) for h in headers}
    
    # Calcular intersección
    interseccion = normalized_expected & normalized_found
    coincidencia = len(interseccion) / len(normalized_expected) if normalized_expected else 0
    
    logger.info(
        "Coincidencia de headers: %.1f%% (%d/%d headers esperados)",
        coincidencia * 100,
        len(interseccion),
        len(normalized_expected),
    )
    
    # Determinar estructura
    if coincidencia >= umbral:
        estructura = "limpia"
        filas_a_eliminar = 0
        logger.info("Estructura detectada: LIMPIA - No se eliminan filas")
    else:
        estructura = "con_encabezados"
        filas_a_eliminar = rows_to_eliminar_default
        logger.info("Estructura detectada: CON ENCABEZADOS - Se eliminarán %d filas", filas_a_eliminar)
    
    return {
        "status": "success",
        "data": {
            "estructura": estructura,
            "filas_a_eliminar": filas_a_eliminar,
            "headers_encontrados": headers[:10],  # Primeros 10 para debug
            "headers_coincidentes": list(interseccion)[:20],  # Primeros 20 para debug
            "coincidencia": round(coincidencia, 3),
        },
        "errors": [],
    }


def get_filas_a_eliminar(
    file_path: str | Path,
    *,
    sheet_name: str | None = None,
    sheet_id: int | None = None,
    rows_to_eliminar_default: int = 2,
    umbral: float = UMBRAL_COINCIDENCIA,
) -> int:
    """
    Wrapper simple que retorna directamente el número de filas a eliminar.
    
    Args:
        file_path: Ruta al archivo Excel
        sheet_name: Nombre de la hoja
        sheet_id: ID de la hoja
        rows_to_eliminar_default: Filas a eliminar por defecto si hay encabezados
        umbral: Umbral de coincidencia
    
    Returns:
        Número de filas a eliminar (0 o rows_to_eliminar_default)
    """
    result = detectar_estructura_excel(
        file_path,
        sheet_name=sheet_name,
        sheet_id=sheet_id,
        rows_to_eliminar_default=rows_to_eliminar_default,
        umbral=umbral,
    )
    
    if result["status"] == "success":
        return result["data"]["filas_a_eliminar"]
    
    # Si hay error, retornar默认值 (asumir que tiene encabezados)
    logger.warning("Error detectando estructura, usando默认值: %d", rows_to_eliminar_default)
    return rows_to_eliminar_default