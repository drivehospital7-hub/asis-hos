"""Orquestador de detección de problemas para Equipos Básicos.

Agrupa detectores transversales y específicos de equipos básicos.
Reutiliza detectores de odontología cuando aplican (IDE Contrato, Centro Costo).
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_EQUIPOS_BASICOS
from app.constants.base import is_evidence_audit_enabled, is_rule_engine_enabled

# Module-level flag: skip evidence/audit DB writes when testing
_PERSIST = is_evidence_audit_enabled()
from app.services.transversales import normalize_invoice

logger = logging.getLogger(__name__)


def detect_all_problems_equipos_basicos(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    rows: list[dict[str, Any]] | None = None,
    profesional_dias: dict[str, list[int]] | None = None,
    permitir_todos_centros: bool = True,
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Detecta TODOS los problemas en facturas de equipos básicos.

    Incluye detectores transversales y específicos de equipos básicos.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas
        profesional_dias: Dict {identificacion: [dias]} con días seleccionados
        permitir_todos_centros: Si True, solo permite centros válidos

    Returns:
        (resultado_dict, responsables_map)
    """
    # ── Consolidated engine rule evaluation (single session + single collector) ──
    # Descubrimiento dinámico por dominio (sin nombres fijos): las reglas
    # habilitadas (dominio + transversales, solo activo) salen de la DB vía
    # RuleResolver. Ref #1: ide_contrato_odontologia_valido cubre el intent
    # IDE (la variante equipos no existe en DB); cantidades = grupo 'Cantidades'.
    if is_rule_engine_enabled():
        from app.services.engine.session_manager import SessionManager
        from app.services.engine.evidence_collector import EvidenceCollector
        from app.services.engine.domain_detection import (
            detect_domain_rules,
            group_by_grupo,
            split_codigo_entidad,
        )
        from app.models import Regla, ResultadoAuditoria

        with SessionManager("equipos_basicos") as session:
            collector = EvidenceCollector(domain="equipos_basicos")

            batches = detect_domain_rules(
                session, AREA_EQUIPOS_BASICOS, data_sheet, indices,
                persist=_PERSIST, evidence_collector=collector, rows=rows,
            )
            grupos = group_by_grupo(batches)

            decimales = grupos.get("Decimales", [])
            doble_tipo = grupos.get("Doble Tipo Procedimiento", [])
            ruta_dup = grupos.get("Ruta Duplicada", [])
            tipo_id_edad = grupos.get("Tipo Identificacion / Edad", [])
            tipo_id_entidad, entidad_afiliacion_comparison = (
                split_codigo_entidad(grupos, batches)
            )
            cantidades = grupos.get("Cantidades", [])
            tipo_usuario_eb = grupos.get("Tipo Usuario", [])
            logger.info("detect_all_problems_equipos_basicos - Llamando detect_ide_contrato_odontologia")
            ide_contrato = grupos.get("IDE Contrato", [])
            logger.info("detect_all_problems_equipos_basicos - IDE Contrato encontrados: %d", len(ide_contrato))
            logger.info("detect_all_problems_equipos_basicos - Llamando detect_profesionales_equipos_basicos")
            profesionales = grupos.get("Profesionales", [])
            logger.info("detect_all_problems_equipos_basicos - Profesionales encontrados: %d", len(profesionales))
            centro_costo = grupos.get("Centros de Costo", [])
            cups_sin_contrato = grupos.get("Cups Sin Contrato", [])
            logger.info(
                "detect_all_problems_equipos_basicos - Cups Sin Contrato encontrados: %d",
                len(cups_sin_contrato),
            )

            # ── Flush all evidence + create ResultadoAuditoria rows ──
            if _PERSIST:
                evidencias = collector.flush_batch(session)
                if evidencias:
                    regla_ids = {e.regla_id for e in evidencias}
                    reglas_map = {
                        r.id: r
                        for r in session.query(Regla).filter(Regla.id.in_(regla_ids))
                    }
                    for ev in evidencias:
                        if ev.outcome == "MATCH":
                            resultado_str = "FAIL"
                        elif ev.outcome == "ERROR":
                            resultado_str = "ERROR"
                        else:
                            resultado_str = "PASS"
                        rule = reglas_map.get(ev.regla_id)
                        ra = ResultadoAuditoria(
                            evidencia_id=ev.id,
                            regla_id=ev.regla_id,
                            regla_version=ev.regla_version,
                            factura=ev.factura,
                            param_config_id=ev.param_config_id,
                            resultado=resultado_str,
                            severidad=rule.severidad if rule else "error",
                            mensaje=ev.error_mensaje or (rule.descripcion if rule else ""),
                            detalles={"outcome": ev.outcome},
                        )
                        session.add(ra)
                    session.flush()

    # Build responsable_cierra mapping
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

    # Build fecha_cierre_vacia mapping
    fecha_cierre_vacia: dict[str, bool] = {}
    fecha_cierre_idx = indices.get("fecha_cierre")
    if fecha_cierre_idx is not None and num_fact_idx is not None:
        for row in range(2, data_sheet.max_row + 1):
            numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
            factura = normalize_invoice(numero)
            if not factura:
                continue
            fecha_cierre_val = data_sheet.cell(
                row=row, column=fecha_cierre_idx + 1
            ).value
            if not fecha_cierre_val or str(fecha_cierre_val).strip() == "":
                fecha_cierre_vacia[factura] = True
            elif factura not in fecha_cierre_vacia:
                fecha_cierre_vacia[factura] = False

    # Build fec_factura_map
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

    # Build normalized rows for unified 6-column display
    from app.services.odontologia.normalized_rows import build_odontologia_normalized_rows

    normalized_rows_eb = build_odontologia_normalized_rows(
        decimales=decimales,
        doble_tipo=doble_tipo,
        ruta_dup=ruta_dup,
        profesionales=profesionales,
        cantidades=cantidades,
        tipo_id_edad=tipo_id_edad,
        tipo_id_entidad=tipo_id_entidad,
        centro_costo=centro_costo,
        ide_contrato=ide_contrato,
        responsable_cierra=responsable_cierra,
        entidad_afiliacion_comparison=entidad_afiliacion_comparison,
        tipo_usuario=tipo_usuario_eb,
        fec_factura_map=fec_factura_map,
        cups_sin_contrato=cups_sin_contrato,
        fecha_cierre_vacia_map=fecha_cierre_vacia,
    )

    resultado: dict[str, Any] = {
        "area": AREA_EQUIPOS_BASICOS,
        "problemas": {
            "normalizados": normalized_rows_eb,
            "decimales": decimales,
            "doble_tipo_procedimiento": doble_tipo,
            "ruta_duplicada": ruta_dup,
            "profesionales": profesionales,
            "cantidades_anomalas": cantidades,
            "tipo_identificacion_edad": tipo_id_edad,
            "tipo_identificacion_entidad": tipo_id_entidad,
            "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            "tipo_usuario": tipo_usuario_eb,
            "centro_costo": centro_costo,
            "ide_contrato": ide_contrato,
            "cups_sin_contrato": cups_sin_contrato,
        },
        "totales": {
            "decimales": len(decimales),
            "doble_tipo_procedimiento": len(doble_tipo),
            "ruta_duplicada": len(ruta_dup),
            "profesionales": len(profesionales),
            "cantidades_anomalas": len(cantidades),
            "tipo_identificacion_edad": len(tipo_id_edad),
            "tipo_identificacion_entidad": len(tipo_id_entidad),
            "centro_costo": len(centro_costo),
            "ide_contrato": len(ide_contrato),
            "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            "tipo_usuario": len(tipo_usuario_eb),
            "cups_sin_contrato": len(cups_sin_contrato),
        },
        "es_equipos_basicos": True,
        "missing_columns": [],
    }

    # Enrich errors with responsable from mapping
    if responsable_cierra:
        for problem_type, problems in resultado["problemas"].items():
            if not isinstance(problems, list):
                continue
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
            if not isinstance(problems, list):
                continue
            for p in problems:
                if not isinstance(p, dict):
                    continue
                if "responsable" not in p:
                    p["responsable"] = ""

    return resultado, responsable_cierra
