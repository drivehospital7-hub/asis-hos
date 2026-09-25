"""Orquestador de detección de problemas para Extramural.

Agrupa detectores transversales + específicos de Extramural.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_EXTRAMURAL
from app.constants.base import is_evidence_audit_enabled, is_rule_engine_enabled
from app.services.transversales import (
    normalize_invoice,
)
from app.services.normalized_rows import build_normalized_rows

# Module-level flag: skip evidence/audit DB writes when testing
_PERSIST = is_evidence_audit_enabled()
logger = logging.getLogger(__name__)


def detect_all_problems_extramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Detecta TODOS los problemas en facturas de Extramural.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        (resultado_dict, responsables_map)
    """
    # 1. Detección engine: descubrimiento dinámico por dominio (sin nombres fijos).
    # Las reglas habilitadas (dominio + transversales, solo activo) salen de la
    # DB vía RuleResolver; agregar/retirar reglas en la UI no toca código.
    batches: list = []
    if is_rule_engine_enabled():
        from app.database import get_session
        from app.services.engine.domain_detection import (
            detect_domain_rules,
            group_by_grupo,
            split_codigo_entidad,
        )
        session = get_session()
        try:
            batches = detect_domain_rules(
                session, AREA_EXTRAMURAL, data_sheet, indices, persist=_PERSIST,
            )
            grupos = group_by_grupo(batches)
            decimales = grupos.get("Decimales", [])
            tipo_identificacion_edad = grupos.get("Tipo Identificacion / Edad", [])
            tipo_identificacion_entidad, entidad_afiliacion_comparison = (
                split_codigo_entidad(grupos, batches)
            )
            tipo_usuario = grupos.get("Tipo Usuario", [])
            copago_entidad = grupos.get("Copago vs Entidad", [])
            cups_sin_contrato = grupos.get("Cups Sin Contrato", [])
            if _PERSIST:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()
        error_groups = dict(grupos)

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

    # 3. Build fecha_cierre_vacia mapping
    fecha_cierre_vacia: dict[str, bool] = {}
    fecha_cierre_idx = indices.get("fecha_cierre")
    if fecha_cierre_idx is not None and num_fact_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
            factura = normalize_invoice(numero)
            if not factura:
                continue
            fecha_cierre_val = data_sheet.cell(row=row, column=fecha_cierre_idx + 1).value
            if not fecha_cierre_val or str(fecha_cierre_val).strip() == "":
                fecha_cierre_vacia[factura] = True
            elif factura not in fecha_cierre_vacia:
                fecha_cierre_vacia[factura] = False

    # 4. Build fec_factura_map
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

    # 5. Build normalized rows (error_groups ya viene por path: grupo_error
    # con engine ON para el flag GRUPO_ERROR_MAPPING, etiquetas legacy con OFF).
    normalized_rows = build_normalized_rows(
        error_groups=error_groups,
        responsables_map=responsable_cierra,
        fec_factura_map=fec_factura_map,
        fecha_cierre_vacia_map=fecha_cierre_vacia,
    )

    # 6. Build resultado
    resultado: dict[str, Any] = {
        "area": AREA_EXTRAMURAL,
        "problemas": {
            "normalizados": normalized_rows,
            "centros_de_costos": [],
            "ide_contrato": [],
            "cups_equivalentes": [],
            "decimales": decimales,
            "tipo_identificacion_edad": tipo_identificacion_edad,
            "tipo_identificacion_entidad": tipo_identificacion_entidad,
            "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            "tipo_usuario": tipo_usuario,
            "copago_entidad": copago_entidad,
            "cups_sin_contrato": cups_sin_contrato,
        },
        "totales": {
            "centros_de_costos": 0,
            "ide_contrato": 0,
            "cups_equivalentes": 0,
            "decimales": len(decimales),
            "tipo_identificacion_edad": len(tipo_identificacion_edad),
            "tipo_identificacion_entidad": len(tipo_identificacion_entidad),
            "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            "tipo_usuario": len(tipo_usuario),
            "copago_entidad": len(copago_entidad),
            "cups_sin_contrato": len(cups_sin_contrato),
        },
        "missing_columns": [],
    }

    # 7. Enrich errors with responsable
    for problem_type, problems in resultado["problemas"].items():
        for p in problems:
            if not isinstance(p, dict):
                continue
            factura = p.get("factura")
            if factura and factura in responsable_cierra:
                p["responsable"] = responsable_cierra[factura]
            elif "responsable" not in p:
                p["responsable"] = ""

    return resultado, responsable_cierra
