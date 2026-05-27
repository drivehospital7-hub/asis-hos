"""Procesador unificado — detecta problemas para todos los tipos de factura presentes.

Lee el Excel una vez, identifica los valores únicos de "Tipo Factura Descripción",
y despacha a cada orquestador por tipo. Los resultados se fusionan en una sola
respuesta con filas normalizadas y totales consolidados.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.services.transversales import (
    normalize_invoice,
)
from app.services.normalized_rows import build_normalized_rows

logger = logging.getLogger(__name__)


def _get_unique_tipo_factura(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[str]:
    """Extrae los valores únicos de Tipo Factura Descripción del Excel.

    Solo retorna los tipos para los que existe un orquestador.
    """
    tipo_factura_idx = indices.get("tipo_factura_descripcion")
    if tipo_factura_idx is None:
        logger.warning("Columna 'Tipo Factura Descripción' no encontrada")
        return []

    tipos: set[str] = set()
    for row in range(2, data_sheet.max_row + 1):
        val = data_sheet.cell(row=row, column=tipo_factura_idx + 1).value
        tipo = str(val).strip() if val else ""
        if tipo:
            tipos.add(tipo)

    # Solo procesar tipos que tienen orquestador implementado
    tipos_con_orquestador = {
        "Urgencias", "Hospitalización", "Intramural", "Ambulatoria",
        "Odontología",
    }
    tipos_presentes = sorted(tipos & tipos_con_orquestador)

    # "Urgencias" primero — es el orquestador base con transversales
    if "Urgencias" in tipos_presentes:
        tipos_presentes.remove("Urgencias")
        tipos_presentes.insert(0, "Urgencias")

    logger.info("Tipos de factura detectados: %s", tipos_presentes)
    return tipos_presentes


def _get_orquestador(tipo_factura: str):
    """Devuelve la función detect_all para un tipo de factura."""
    if tipo_factura == "Urgencias":
        from app.services.urgencias.detect_all import (
            detect_all_problems_urgencias,
        )
        return detect_all_problems_urgencias
    elif tipo_factura == "Hospitalización":
        from app.services.hospitalizacion.detect_all import (
            detect_all_problems_hospitalizacion,
        )
        return detect_all_problems_hospitalizacion
    elif tipo_factura == "Intramural":
        from app.services.intramural.detect_all import (
            detect_all_problems_intramural,
        )
        return detect_all_problems_intramural
    elif tipo_factura == "Ambulatoria":
        from app.services.ambulatoria.detect_all import (
            detect_all_problems_ambulatoria,
        )
        return detect_all_problems_ambulatoria
    elif tipo_factura == "Odontología":
        from app.services.odontologia.detect_all import (
            detect_all_problems_odontologia,
        )
        return detect_all_problems_odontologia
    return None


def _merge_normalized_rows(
    base_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fusiona filas normalizadas deduplicando por (tipo_error, factura, descripcion)."""
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []

    for row in base_rows:
        key = (
            row.get("tipo_error", ""),
            row.get("factura", ""),
            row.get("descripcion", ""),
        )
        if key not in seen:
            seen.add(key)
            merged.append(row)

    for row in new_rows:
        key = (
            row.get("tipo_error", ""),
            row.get("factura", ""),
            row.get("descripcion", ""),
        )
        if key not in seen:
            seen.add(key)
            merged.append(row)

    return merged


def _merge_problem_lists(
    base: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    """Fusiona los diccionarios de problemas por tipo."""
    merged: dict[str, Any] = dict(base)

    for key, value in extra.items():
        if key in ("normalizados", "missing_columns", "totales", "totales_por_tipo"):
            continue
        if isinstance(value, list) and key in merged:
            merged[key] = merged[key] + value
        elif key not in merged:
            merged[key] = value

    return merged


def process_unified(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Procesa el Excel aplicando reglas según Tipo Factura Descripción de cada fila.

    Itera sobre los tipos de factura presentes, ejecuta el orquestador
    correspondiente para cada uno, y fusiona los resultados.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        (resultado_unificado, responsables_map_unificado)
    """
    tipos_presentes = _get_unique_tipo_factura(data_sheet, indices)

    if not tipos_presentes:
        logger.warning("No se encontraron tipos de factura conocidos en el Excel")
        return {
            "area": "unificada",
            "problemas": {
                "normalizados": [],
                "missing_columns": [],
            },
            "totales": {},
            "totales_por_tipo": {},
            "missing_columns": [],
            "codigos_sin_db_ide_969": [],
        }, {}

    all_normalized: list[dict[str, Any]] = []
    all_problemas: dict[str, Any] = {}
    all_totales: dict[str, int] = {}
    all_totales_por_tipo: dict[str, dict[str, int]] = {}
    all_responsables: dict[str, str] = {}
    all_codigos_sin_db: list[dict[str, str]] = []

    for tipo in tipos_presentes:
        orquestador = _get_orquestador(tipo)
        if orquestador is None:
            logger.debug("Sin orquestador para tipo: %s", tipo)
            continue

        logger.info("Ejecutando orquestador para: %s", tipo)
        try:
            resultado, responsables = orquestador(data_sheet, indices)
        except Exception:
            logger.exception("Error en orquestador de %s", tipo)
            continue

        problemas = resultado.get("problemas", {})

        # Fusionar filas normalizadas
        norm = problemas.get("normalizados", [])
        all_normalized = _merge_normalized_rows(all_normalized, norm)

        # Fusionar listas de problemas específicos (no normalizados)
        all_problemas = _merge_problem_lists(all_problemas, problemas)

        # Consolidar totales
        totales = resultado.get("totales", {})
        for k, v in totales.items():
            if isinstance(v, (int, float)):
                all_totales[k] = all_totales.get(k, 0) + int(v)

        # Consolidar totales por tipo
        totales_por_tipo = problemas.get("totales_por_tipo", {})
        if totales_por_tipo:
            all_totales_por_tipo[tipo] = totales_por_tipo

        # Fusionar responsables
        all_responsables.update(responsables)

        # Códigos sin DB (solo Urgencias)
        codigos = resultado.get("codigos_sin_db_ide_969", [])
        all_codigos_sin_db.extend(codigos)

    # Construir resultado unificado
    unified: dict[str, Any] = {
        "area": "unificada",
        "problemas": {
            "normalizados": all_normalized,
            "totales_por_tipo": all_totales_por_tipo,
            **all_problemas,
        },
        "totales": all_totales,
        "tipos_procesados": tipos_presentes,
        "missing_columns": all_problemas.get("missing_columns", []),
    }

    # Pasar también en el nivel superior para compatibilidad con rutas existentes
    unified["codigos_sin_db_ide_969"] = all_codigos_sin_db

    logger.info(
        "Procesamiento unificado completado: %d tipos, %d filas normalizadas, %d responsables",
        len(tipos_presentes),
        len(all_normalized),
        len(all_responsables),
    )

    return unified, all_responsables
