"""Orquestador de detección de problemas para Urgencias.

Agrupa detectores transversales + específicos de Urgencias.
Usa el builder compartido de normalized_rows.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_URGENCIAS
from app.constants.base import is_evidence_audit_enabled, is_rule_engine_enabled

# Module-level flag: skip evidence/audit DB writes when testing
_PERSIST = is_evidence_audit_enabled()
from app.services.transversales import (
    detect_decimales,
    detect_tipo_documento_edad,
    detect_tipo_identificacion_entidad,
    detect_tipo_usuario,
    normalize_invoice,
)
from app.services.urgencias.centro_costo_urgencias import (
    detect_centro_costo_urgencias,
)
from app.services.urgencias.ide_contrato_urgencias import (
    detect_ide_contrato_urgencias,
)
from app.services.urgencias.cups_equivalentes import detect_cups_equivalentes
from app.services.urgencias.sala_observacion import detect_sala_observacion
from app.services.urgencias.cantidades_urgencias import (
    detect_cantidades_urgencias,
)
from app.services.urgencias.cantidades_soat_urgencias import (
    detect_cantidades_soat_urgencias,
)
from app.services.urgencias.mal_capitado import detect_mal_capitado
from app.services.urgencias.ide_contrato_reverse import detect_ide_contrato_reverse_urgencias
from app.services.urgencias.profesionales_urgencias import detect_profesionales_urgencias
from app.services.transversales.detect_copago_entidad import (
    detect_copago_entidad_urgencias,
)
from app.services.transversales.procedimiento_contratado import detect_cups_sin_contrato
from app.services.urgencias.revision_cantidad import detect_revision_cantidad_urgencias
from app.services.urgencias.revision_entidad_86 import detect_revision_entidad_86_urgencias
from app.services.urgencias.duplicados_farmacia import detect_duplicados_farmacia
from app.services.normalized_rows import build_normalized_rows

logger = logging.getLogger(__name__)


def detect_all_problems_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
    rows: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Detecta TODOS los problemas en facturas de urgencias.

    Incluye detectores transversales y específicos de urgencias.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        (resultado_dict, responsables_map)
    """
    # ── Consolidated engine rule evaluation (single session + single collector) ──
    # Descubrimiento dinámico por dominio (sin nombres fijos): las reglas
    # habilitadas (dominio + transversales, solo activo) salen de la DB vía
    # RuleResolver; transversales aplican a todos. Ref #1: ide_contrato_simple /
    # simple_urgencias / sala_observacion_valido no existen en DB — el resolver
    # nunca los sirve (adiós "Rule not found" silenciosos).
    #
    # Excepciones de presentación legacy (buckets, no descubrimiento):
    # - IDE reverse y revision entidad/cantidad separan su grupo en 2 buckets.
    # - Estancia: post-procesado bespoke sobre su regla (deduplin + catálogo).
    # - Familia sala_obs_ sin grupo declarado: alimenta cups_equivalentes
    #   (cuando el admin declare su grupo_error, entra por grupo).
    problemas_cups_equivalentes: list[dict[str, str]] = []
    if is_rule_engine_enabled():
        from app.services.engine.session_manager import SessionManager
        from app.services.engine.evidence_collector import EvidenceCollector
        from app.services.engine.domain_detection import (
            detect_domain_rules,
            group_by_grupo,
            items_by_nombre,
            split_codigo_entidad,
        )
        from app.models import Catalogo, Regla, ResultadoAuditoria

        _IDE_REVERSE_RULE = "ide_contrato_reverse_urgencias_valido"
        _REVISION_ENTIDAD_RULE = "revision_entidad_86"
        _ESTANCIA_RULE = "sala_observacion_estancia_prolongada"
        _SALA_OBS_PREFIX = "sala_obs_"

        with SessionManager("urgencias") as session:
            collector = EvidenceCollector(domain="urgencias")

            batches = detect_domain_rules(
                session, AREA_URGENCIAS, data_sheet, indices,
                persist=_PERSIST, evidence_collector=collector, rows=rows,
            )
            grupos = group_by_grupo(batches)
            por_nombre = items_by_nombre(batches)

            # Centro Costo + IDE Contrato (IDE reverse va a su propio bucket).
            problemas_centros = grupos.get("Centros de Costo", [])
            logger.info(
                "detect_all_problems_urgencias - Centros Costo encontrados: %d",
                len(problemas_centros),
            )
            problemas_ide_contrato = [
                item
                for batch in batches
                if batch.grupo == "IDE Contrato" and batch.nombre != _IDE_REVERSE_RULE
                for item in batch.items
            ]
            ide_contrato_reverse = list(por_nombre.get(_IDE_REVERSE_RULE, []))
            logger.info(
                "detect_all_problems_urgencias - IDE Contrato REVERSE encontrados: %d",
                len(ide_contrato_reverse),
            )
            # Ref #1: ide_contrato_simple_urgencias no existe en DB y su intent
            # ya lo cubre ide_contrato_urgencias_valido (evaluado exactamente
            # una vez vía el batch de arriba).

            # CUPS equivalentes + Sala observación (grupo + familia pre-taxonomía).
            problemas_cups_equivalentes = [
                item
                for batch in batches
                if (
                    (batch.grupo == "Cups-Equivalentes" and batch.nombre != _ESTANCIA_RULE)
                    or (batch.grupo == batch.nombre and batch.nombre.startswith(_SALA_OBS_PREFIX))
                )
                for item in batch.items
            ]
            # Ref #1: "sala_observacion_valido" no existe en DB; la regla
            # ejecutable del slot es sala_obs_check_set (viene por grupo).
            # Rule 44: estancia > 6h en Urgencias sin código de sala de
            # observación. Explicit tree (gt(date.horas, 6) + eq Urgencias +
            # NOT(in(codigo, sala codes))) — no deregistered operators.
            # Nivel factura: la factura en conjunto debe traer alguno de los
            # códigos de sala. La lista vive en el catálogo 'sala_codes'
            # (misma que el árbol de la regla); si falta, fallback al set
            # del árbol. Uno por factura (la estancia es de la factura).
            _estancia = por_nombre.get(_ESTANCIA_RULE, [])
            _sala_codes: set[str] = {"5DSB01", "05DSB01", "129B02", "38114", "38915"}
            try:
                _cat = session.query(Catalogo).filter(Catalogo.key == "sala_codes").first()
                if _cat is not None and _cat.value:
                    _sala_codes = {str(v).strip().upper() for v in _cat.value}
            except Exception:
                logger.warning("Estancia: no se pudo leer catálogo sala_codes, uso fallback")
            _facturas_con_sala: set[str] = set()
            from datetime import datetime as _dt

            def _parse_fecha(_v: object) -> "_dt | None":
                if _v is None or _v == "":
                    return None
                if isinstance(_v, _dt):
                    return _v
                _s = str(_v).strip().split(".")[0]
                for _fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
                    try:
                        return _dt.strptime(_s, _fmt)
                    except ValueError:
                        continue
                try:
                    return _dt.fromisoformat(_s)
                except ValueError:
                    return None

            def _fmt_estancia(_d0: "_dt", _d1: "_dt") -> str:
                _delta = _d1 - _d0
                _hs = int(_delta.total_seconds() // 3600)
                if _hs < 0:
                    return ""
                _dd, _hh = divmod(_hs, 24)
                if _dd:
                    return f"{_dd} días {_hh} horas"
                return f"{_hh} horas"

            _estancia_por_factura: dict[str, str] = {}
            _fec_idx = indices.get("fec_factura")
            _cierre_idx = indices.get("fecha_cierre")
            _codigo_idx = indices.get("codigo")
            _num_fact_est_idx = indices.get("numero_factura")
            if _codigo_idx is not None and _num_fact_est_idx is not None:
                if rows is not None:
                    for _rd in rows:
                        _f = normalize_invoice(_rd.get("numero_factura"))
                        _c = str(_rd.get("codigo", "")).strip().upper() if _rd.get("codigo") is not None else ""
                        if _f and _c in _sala_codes:
                            _facturas_con_sala.add(_f)
                        if _f and _f not in _estancia_por_factura and _fec_idx is not None and _cierre_idx is not None:
                            _d0 = _parse_fecha(_rd.get("fec_factura"))
                            _d1 = _parse_fecha(_rd.get("fecha_cierre"))
                            if _d0 is not None and _d1 is not None:
                                _estancia_por_factura[_f] = _fmt_estancia(_d0, _d1)
                elif data_sheet is not None:
                    for _row in range(2, data_sheet.max_row + 1):
                        _f = normalize_invoice(data_sheet.cell(row=_row, column=_num_fact_est_idx + 1).value)
                        _cv = data_sheet.cell(row=_row, column=_codigo_idx + 1).value
                        _c = str(_cv).strip().upper() if _cv is not None else ""
                        if _f and _c in _sala_codes:
                            _facturas_con_sala.add(_f)
                        if _f and _f not in _estancia_por_factura and _fec_idx is not None and _cierre_idx is not None:
                            _d0 = _parse_fecha(data_sheet.cell(row=_row, column=_fec_idx + 1).value)
                            _d1 = _parse_fecha(data_sheet.cell(row=_row, column=_cierre_idx + 1).value)
                            if _d0 is not None and _d1 is not None:
                                _estancia_por_factura[_f] = _fmt_estancia(_d0, _d1)
            _estancia_vistas: set[str] = set()
            for _item in _estancia:
                _fact = _item.get("factura", "")
                if not _fact or _fact in _estancia_vistas:
                    continue
                if _fact in _facturas_con_sala:
                    continue
                _estancia_vistas.add(_fact)
                _est = _estancia_por_factura.get(_fact, "")
                if _est:
                    _item["estancia_str"] = _est
                problemas_cups_equivalentes.append(_item)
            # (Loop de 7 sala_obs_* eliminado: esas reglas — si existen en DB —
            # entran por grupo o por familia pre-taxonomía en el bloque de arriba.)

            # Transversales por grupo (transversales aplican a todos los dominios).
            decimales = grupos.get("Decimales", [])
            tipo_identificacion_edad = grupos.get("Tipo Identificacion / Edad", [])
            tipo_identificacion_entidad, codigo_entidad_afiliacion = (
                split_codigo_entidad(grupos, batches)
            )
            tipo_usuario = grupos.get("Tipo Usuario", [])

            # Profesionales urgencias
            profesionales = grupos.get("Profesionales", [])
            logger.info(
                "detect_all_problems_urgencias - Profesionales encontrados: %d",
                len(profesionales),
            )

            # Mal capitado
            # Mal capitado (grupo incluye transversales si el admin las habilita).
            mal_capitado = grupos.get("MAL CAPITADO", [])
            logger.info(
                "detect_all_problems_urgencias - MAL CAPITADO encontrados: %d",
                len(mal_capitado),
            )

            # Cantidades (grupo 'Cantidades': urgencias + transversales).
            cantidades_urgencias = grupos.get("Cantidades", [])
            logger.info(
                "detect_all_problems_urgencias - Cantidades Urgencias encontradas: %d",
                len(cantidades_urgencias),
            )

            # Cantidades SOAT urgencias.
            cantidades_soat_urgencias = grupos.get("Cantidades SOAT", [])
            logger.info(
                "detect_all_problems_urgencias - Cantidades SOAT Urgencias encontradas: %d",
                len(cantidades_soat_urgencias),
            )

            # Revision-Necesaria separada en sus 2 buckets legacy (Ref #1:
            # "revision_cantidad_urgencias_valido" no existe en DB; la regla
            # sembrada revision_cantidad_urgencias + v2 van al bucket cantidad).
            revision_entidad_86 = []
            revision_cantidad = []
            for batch in batches:
                if batch.grupo != "Revision-Necesaria":
                    continue
                if batch.nombre == _REVISION_ENTIDAD_RULE:
                    revision_entidad_86.extend(batch.items)
                else:
                    revision_cantidad.extend(batch.items)
            logger.info(
                "detect_all_problems_urgencias - Revision Entidad 86 encontradas: %d",
                len(revision_entidad_86),
            )
            logger.info(
                "detect_all_problems_urgencias - Revision Cantidad encontradas: %d",
                len(revision_cantidad),
            )

            # Copago vs entidad + Duplicados farmacia (grupos, merge total).
            copago_entidad = grupos.get("Copago vs Entidad", [])
            logger.info(
                "detect_all_problems_urgencias - Copago vs Entidad encontrados: %d",
                len(copago_entidad),
            )
            duplicados_farmacia = grupos.get("Duplicados-Farmacia", [])
            logger.info(
                "detect_all_problems_urgencias - Duplicados Farmacia encontrados: %d",
                len(duplicados_farmacia),
            )

            # CUPS sin contrato.
            cups_sin_contrato = grupos.get("Cups Sin Contrato", [])
            logger.info(
                "detect_all_problems_urgencias - Cups Sin Contrato encontrados: %d",
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
    else:
        problemas_centros = []
        problemas_ide_contrato = []
        decimales = detect_decimales(data_sheet, indices)
        tipo_identificacion_edad = []
        tipo_identificacion_entidad = detect_tipo_identificacion_entidad(data_sheet, indices)
        tipo_usuario = detect_tipo_usuario(data_sheet, indices)
        codigo_entidad_afiliacion = []
        profesionales = []
        mal_capitado = []
        cantidades_urgencias = []
        cantidades_soat_urgencias = []
        ide_contrato_reverse = []
        revision_entidad_86 = []
        revision_cantidad = detect_revision_cantidad_urgencias(data_sheet, indices)
        copago_entidad = detect_copago_entidad_urgencias(data_sheet, indices)
        duplicados_farmacia = detect_duplicados_farmacia(data_sheet, indices)
        cups_sin_contrato = detect_cups_sin_contrato(data_sheet, indices)

    # 6. Filtrar centros de costo por prioridad
    errores_por_factura_codigo: dict[tuple[str, str], list[tuple[dict, int]]] = {}
    for item in problemas_centros:
        key = (item.get("factura", ""), item.get("codigo", ""))
        prioridad = item.get("prioridad", 1)
        if key not in errores_por_factura_codigo:
            errores_por_factura_codigo[key] = []
        errores_por_factura_codigo[key].append((item, prioridad))

    problemas_centros_filtrados = []
    for key, items in errores_por_factura_codigo.items():
        prioridades = [p for _, p in items]
        if 1 in prioridades:
            for item, p in items:
                if p == 1:
                    problemas_centros_filtrados.append(item)
        else:
            for item, _ in items:
                problemas_centros_filtrados.append(item)

    logger.info(
        "FILTRO centros_de_costos: %d -> %d",
        len(problemas_centros),
        len(problemas_centros_filtrados),
    )

    # 7. Build responsable_cierra mapping
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

    # 8. Build fecha_cierre_vacia mapping
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

    # 9. Build fec_factura_map
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

    # 10. Build normalized rows (shared builder). Engine: grupos por
    # grupo_error (flag GRUPO_ERROR_MAPPING) con los merges legacy
    # conservados (IDE base+reverse, revisión 86+cantidad, centros filtrados).
    if is_rule_engine_enabled():
        error_groups = dict(grupos)
        error_groups["Centros de Costo"] = problemas_centros_filtrados
        error_groups["IDE Contrato"] = (
            problemas_ide_contrato + ide_contrato_reverse
        )
        error_groups["Cups-Equivalentes"] = problemas_cups_equivalentes
        error_groups["Revision-Necesaria"] = (
            revision_entidad_86 + revision_cantidad
        )
    else:
        error_groups = {
            "Centros de Costo": problemas_centros_filtrados,
            "IDE Contrato": problemas_ide_contrato + ide_contrato_reverse,
            "Cups Equivalentes": problemas_cups_equivalentes,
            "MAL CAPITADO": mal_capitado,
            "Cantidades": cantidades_urgencias,
            "Cantidades SOAT": cantidades_soat_urgencias,
            "Decimales": decimales,
            "Tipo Identificación / Edad": tipo_identificacion_edad,
            "Profesionales": profesionales,
            "Código Entidad vs Afiliación": tipo_identificacion_entidad,
            "Tipo Usuario": tipo_usuario,
            "⚠️ Revisión Necesaria": revision_entidad_86 + revision_cantidad,
            "Copago vs Entidad": copago_entidad,
            "Duplicados Farmacia": duplicados_farmacia,
            "Cups Sin Contrato": cups_sin_contrato,
        }
    normalized_rows = build_normalized_rows(
        error_groups=error_groups,
        responsables_map=responsable_cierra,
        fec_factura_map=fec_factura_map,
        fecha_cierre_vacia_map=fecha_cierre_vacia,
    )

    # 11. Build resultado dict
    resultado: dict[str, Any] = {
        "area": AREA_URGENCIAS,
        "problemas": {
            "normalizados": normalized_rows,
            "centros_de_costos": [
                {
                    "tipo_factura": item.get("tipo_factura") or "-",
                    "factura": item["factura"],
                    "codigo": item.get("codigo", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "centro_actual": item.get("centro_actual", item.get("centro_costo", "")),
                    "centro_deberia": item.get("centro_deberia", ""),
                    "prioridad": item.get("prioridad", 1),
                }
                for item in problemas_centros_filtrados
            ],
            "ide_contrato": [
                {
                    "factura": item["factura"],
                    "ide_contrato_actual": item.get("ide_contrato_actual", item.get("ide_contrato", "")),
                    "ide_contrato_deberia": item.get("ide_contrato_deberia", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "codigo": item.get("codigo", ""),
                    "entidad": item.get("entidad", ""),
                    "nota": item.get("nota", ""),
                }
                for item in (problemas_ide_contrato + ide_contrato_reverse)
            ],
            "ide_contrato_reverse": [
                {
                    "factura": item["factura"],
                    "ide_contrato_actual": item.get("ide_contrato_actual", item.get("ide_contrato", "")),
                    "ide_contrato_deberia": item.get("ide_contrato_deberia", ""),
                    "procedimiento": item.get("procedimiento", ""),
                    "codigo": item.get("codigo", ""),
                    "entidad": item.get("entidad", ""),
                    "nota": item.get("nota", ""),
                }
                for item in ide_contrato_reverse
            ],
            "cups_equivalentes": [
                {
                    "factura": item["factura"],
                    # .get: engine items never carry codigo_equiv (row data has
                    # no such column) and group-shape items carry no scalar
                    # codigo; legacy items always have both keys, so legacy
                    # output is unchanged (same pattern as hospitalizacion).
                    "codigo": item.get("codigo", ""),
                    "codigo_equiv": item.get("codigo_equiv", ""),
                    "accion": item.get("accion", item.get("problema", "")),
                }
                for item in problemas_cups_equivalentes
            ],
            # reglas transversales
            "decimales": decimales,
            "tipo_identificacion_edad": tipo_identificacion_edad,
            "tipo_identificacion_entidad": tipo_identificacion_entidad,
            "codigo_entidad_vs_afiliacion": codigo_entidad_afiliacion,
            "tipo_usuario": tipo_usuario,
            # reglas urgencias
            "profesionales": profesionales,
            "mal_capitado": mal_capitado,
            "cantidades_urgencias": cantidades_urgencias,
            "cantidades_soat_urgencias": cantidades_soat_urgencias,
            "revision_entidad_86": revision_entidad_86,
            "revision_cantidad": revision_cantidad,
            "copago_entidad": copago_entidad,
            "duplicados_farmacia": duplicados_farmacia,
            "cups_sin_contrato": cups_sin_contrato,
        },
        "totales": {
            "centros_de_costos": len(problemas_centros),
            "ide_contrato": len(problemas_ide_contrato) + len(ide_contrato_reverse),
            "ide_contrato_reverse": len(ide_contrato_reverse),
            "cups_equivalentes": len(problemas_cups_equivalentes),
            "decimales": len(decimales),
            "tipo_identificacion_edad": len(tipo_identificacion_edad),
            "tipo_identificacion_entidad": len(tipo_identificacion_entidad),
            "codigo_entidad_vs_afiliacion": len(codigo_entidad_afiliacion),
            "tipo_usuario": len(tipo_usuario),
            "profesionales": len(profesionales),
            "mal_capitado": len(mal_capitado),
            "cantidades_urgencias": len(cantidades_urgencias),
            "cantidades_soat_urgencias": len(cantidades_soat_urgencias),
            "revision_entidad_86": len(revision_entidad_86),
            "revision_cantidad": len(revision_cantidad),
            "copago_entidad": len(copago_entidad),
            "duplicados_farmacia": len(duplicados_farmacia),
            "cups_sin_contrato": len(cups_sin_contrato),
        },
        "missing_columns": [],
    }

    # 12. Enrich errors with responsable from mapping
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
