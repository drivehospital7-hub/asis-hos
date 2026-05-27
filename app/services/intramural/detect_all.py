"""Orquestador de detección de problemas para Intramural.

Solo invoca detectores transversales — sin reglas de negocio propias del área.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_INTRAMURAL
from app.services.transversales import (
    detect_decimales,
    detect_tipo_documento_edad,
    detect_codigo_entidad_vs_entidad_afiliacion,
    detect_tipo_usuario,
    normalize_invoice,
)
from app.services.intramural.normalized_rows import (
    build_intramural_normalized_rows,
)
from app.services.intramural.ide_contrato_intramural import (
    detect_ide_contrato_intramural,
)

logger = logging.getLogger(__name__)


def detect_all_problems_intramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Detecta problemas en facturas intramural usando solo detectores transversales.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        (resultado_dict, responsables_map)
    """
    # 1. Detectores transversales
    decimales = detect_decimales(data_sheet, indices)
    tipo_identificacion_edad = detect_tipo_documento_edad(data_sheet, indices)
    entidad_afiliacion_comparison = detect_codigo_entidad_vs_entidad_afiliacion(
        data_sheet, indices, limit_log=5
    )
    tipo_usuario = detect_tipo_usuario(data_sheet, indices)

    # 1b. Detectores específicos de intramural
    problemas_ide_contrato = detect_ide_contrato_intramural(data_sheet, indices)

    # 2. Build responsable_cierra mapping
    responsable_cierra: dict[str, str] = {}
    responsable_cierra_idx = indices.get("responsable_cierra")
    num_fact_idx = indices.get("numero_factura")
    if responsable_cierra_idx is not None and num_fact_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
            factura = normalize_invoice(numero)
            if not factura:
                continue
            raw = data_sheet.cell(row=row, column=responsable_cierra_idx + 1).value
            resp = str(raw).strip() if raw else ""
            if resp and factura not in responsable_cierra:
                responsable_cierra[factura] = resp

    # 3. Build fec_factura_map
    fec_factura_map: dict[str, str] = {}
    fec_factura_idx = indices.get("fec_factura")
    if fec_factura_idx is not None and num_fact_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
            factura = normalize_invoice(numero)
            if not factura:
                continue
            raw = data_sheet.cell(row=row, column=fec_factura_idx + 1).value
            val = str(raw).strip() if raw else ""
            if val and factura not in fec_factura_map:
                fec_factura_map[factura] = val

    # 4. Build normalized rows
    normalized_rows = build_intramural_normalized_rows(
        responsables_map=responsable_cierra,
        decimales=decimales,
        tipo_identificacion_edad=tipo_identificacion_edad,
        tipo_usuario=tipo_usuario,
        entidad_afiliacion_comparison=entidad_afiliacion_comparison,
        problemas_ide_contrato=problemas_ide_contrato,
        fec_factura_map=fec_factura_map,
    )

    # 5. Build resultado dict
    resultado: dict[str, Any] = {
        "area": AREA_INTRAMURAL,
        "problemas": {
            "normalizados": normalized_rows,
            "decimales": decimales,
            "tipo_identificacion_edad": tipo_identificacion_edad,
            "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            "tipo_usuario": tipo_usuario,
            "ide_contrato": problemas_ide_contrato,
            "totales_por_tipo": _build_totales_por_tipo(normalized_rows),
        },
        "totales": {
            "decimales": len(decimales),
            "tipo_identificacion_edad": len(tipo_identificacion_edad),
            "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            "tipo_usuario": len(tipo_usuario),
            "ide_contrato": len(problemas_ide_contrato),
            "problemas": len(normalized_rows),
        },
        "missing_columns": [],
    }

    # 6. Enrich errors with responsable from mapping
    if responsable_cierra:
        for problem_type, problems in resultado["problemas"].items():
            for p in problems:
                if not isinstance(p, dict):
                    continue
                factura = p.get("factura")
                if factura and factura in responsable_cierra:
                    p["responsable"] = responsable_cierra[factura]
                elif "responsable" not in p:
                    p["responsable"] = ""
    else:
        for problem_type, problems in resultado["problemas"].items():
            for p in problems:
                if not isinstance(p, dict):
                    continue
                if "responsable" not in p:
                    p["responsable"] = ""

    return resultado, responsable_cierra


def _build_totales_por_tipo(
    normalized_rows: list[dict[str, Any]],
) -> dict[str, int]:
    """Construye dict con conteo de errores por tipo."""
    totales: dict[str, int] = {}
    for row in normalized_rows:
        tipo = row.get("tipo_error", "Otros")
        totales[tipo] = totales.get(tipo, 0) + 1
    return totales
