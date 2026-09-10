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
    problemas_cups_equivalentes: list[dict[str, str]] = []
    if is_rule_engine_enabled():
        from app.services.engine.session_manager import SessionManager
        from app.services.engine.evidence_collector import EvidenceCollector
        from app.services.engine.rule_based_detector import RuleBasedDetector
        from app.models import Catalogo, Regla, ResultadoAuditoria

        with SessionManager("urgencias") as session:
            collector = EvidenceCollector(domain="urgencias")

            # Centro Costo + IDE Contrato
            problemas_centros = RuleBasedDetector("centro_costo_urgencias_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            problemas_centros += RuleBasedDetector("centro_costo_urgencias", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Centros Costo encontrados: %d",
                len(problemas_centros),
            )
            problemas_ide_contrato = RuleBasedDetector("ide_contrato_urgencias_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            # Ref #1: the "ide_contrato_simple_urgencias" rule exists in no DB
            # and its intent (codigo+entidad → IDE único) is already covered by
            # ide_contrato_urgencias_valido above ("Cubre reglas simples,
            # multiples y genericas de entidad"). The second evaluation was
            # pure duplication, so it is removed, not renamed.

            # CUPS equivalentes + Sala observación
            problemas_cups_equivalentes.extend(
                RuleBasedDetector("cups_equivalentes", session, dominio=AREA_URGENCIAS).detect(
                    data_sheet, indices, persist=_PERSIST,
                    evidence_collector=collector, rows=rows,
                )
            )
            # Ref #1: "sala_observacion_valido" exists in no DB. The only
            # executable, dev-live rule for the obligatorios slot is
            # sala_obs_check_set (obligatorios 890701+890601 presence when
            # sala codes present; the sala_observacion_entidad rule still runs
            # the deregistered sala_obs_check evaluator and can never fire).
            problemas_cups_equivalentes.extend(
                RuleBasedDetector("sala_obs_check_set", session, dominio=AREA_URGENCIAS).detect(
                    data_sheet, indices, persist=_PERSIST,
                    evidence_collector=collector, rows=rows,
                )
            )
            # Rule 44: estancia > 6h en Urgencias sin código de sala de
            # observación. Explicit tree (gt(date.horas, 6) + eq Urgencias +
            # NOT(in(codigo, sala codes))) — no deregistered operators.
            # Nivel factura: la factura en conjunto debe traer alguno de los
            # códigos de sala. La lista vive en el catálogo 'sala_codes'
            # (misma que el árbol de la regla); si falta, fallback al set
            # del árbol. Uno por factura (la estancia es de la factura).
            _estancia = RuleBasedDetector("sala_observacion_estancia_prolongada", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
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
            for rule_name in [
                "sala_obs_obligatorios",
                "sala_obs_ess_129b02",
                "sala_obs_soat_completo",
                "sala_obs_soat_prohibido",
                "sala_obs_890601h",
                "sala_obs_05dsb01_no_ess",
                "sala_obs_soat_39145_39131",
            ]:
                problemas_cups_equivalentes.extend(
                    RuleBasedDetector(rule_name, session, dominio=AREA_URGENCIAS).detect(
                        data_sheet, indices, persist=_PERSIST,
                        evidence_collector=collector, rows=rows,
                    )
                )

            # Decimales
            decimales = RuleBasedDetector("valores_decimales", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )

            # tipo_documento_edad rules
            r1 = RuleBasedDetector("tipo_documento_edad_menor_7", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r2 = RuleBasedDetector("tipo_documento_edad_mayor_18", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r3 = RuleBasedDetector("tipo_documento_edad_7_17", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r4 = RuleBasedDetector("tipo_documento_edad_as_menor", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r5 = RuleBasedDetector("tipo_documento_edad_ms_mayor", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r6 = RuleBasedDetector("tipo_documento_edad_cn_invalido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r7 = RuleBasedDetector("tipo_documento_edad_ce_invalido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            tipo_identificacion_edad = r1 + r2 + r3 + r4 + r5 + r6 + r7

            # tipo_identificacion_entidad rules
            r1_ent = RuleBasedDetector("tipo_id_requiere_entidad_86000", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            r2_ent = RuleBasedDetector("entidad_86000_requiere_as_ms", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            tipo_identificacion_entidad = r1_ent + r2_ent

            # tipo_usuario
            tipo_usuario = RuleBasedDetector("tipo_usuario_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )

            # codigo_entidad
            codigo_entidad_afiliacion = RuleBasedDetector("codigo_entidad", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )

            # Profesionales urgencias
            profesionales = RuleBasedDetector("profesional_urgencias_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Profesionales encontrados: %d",
                len(profesionales),
            )

            # Mal capitado
            mal_capitado = RuleBasedDetector("mal_capitado", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - MAL CAPITADO encontrados: %d",
                len(mal_capitado),
            )

            # Cantidades urgencias
            cantidades_urgencias = RuleBasedDetector("cantidades_urgencias", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Cantidades Urgencias encontradas: %d",
                len(cantidades_urgencias),
            )

            # Cantidades SOAT urgencias
            cantidades_soat_urgencias = RuleBasedDetector("cantidades_soat_urgencias", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Cantidades SOAT Urgencias encontradas: %d",
                len(cantidades_soat_urgencias),
            )

            # IDE Contrato reverse
            ide_contrato_reverse = RuleBasedDetector("ide_contrato_reverse_urgencias_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - IDE Contrato REVERSE encontrados: %d",
                len(ide_contrato_reverse),
            )

            # Revision entidad 86
            revision_entidad_86 = RuleBasedDetector("revision_entidad_86", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Revision Entidad 86 encontradas: %d",
                len(revision_entidad_86),
            )

            # Revision cantidad (Ref #1: "revision_cantidad_urgencias_valido"
            # exists in no DB; the seeded revision_cantidad_urgencias rule
            # covers the revisión-cantidad intent as group SUM > 1).
            revision_cantidad = RuleBasedDetector("revision_cantidad_urgencias", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Revision Cantidad encontradas: %d",
                len(revision_cantidad),
            )

            # Copago vs entidad
            copago_entidad = RuleBasedDetector("copago_entidad_valido", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Copago vs Entidad encontrados: %d",
                len(copago_entidad),
            )

            # Duplicados farmacia
            duplicados_farmacia = RuleBasedDetector("duplicados_farmacia", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
            logger.info(
                "detect_all_problems_urgencias - Duplicados Farmacia encontrados: %d",
                len(duplicados_farmacia),
            )

            # CUPS sin contrato
            cups_sin_contrato = RuleBasedDetector("cups_sin_contrato", session, dominio=AREA_URGENCIAS).detect(
                data_sheet, indices, persist=_PERSIST,
                evidence_collector=collector, rows=rows,
            )
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

    # 10. Build normalized rows (shared builder)
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
