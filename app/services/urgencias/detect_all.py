"""Orquestador de detección de problemas para Urgencias.

Agrupa todos los detectores específicos de urgencias más los
detectores transversales aplicables a esta área.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants import AREA_URGENCIAS
from app.services.transversales import (
    detect_decimales,
    detect_tipo_documento_edad,
    detect_codigo_entidad_vs_entidad_afiliacion,
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
from app.services.urgencias.cantidades_soat_hospitalizacion import (
    detect_cantidades_soat_hospitalizacion,
)
from app.services.urgencias.hospitalizacion import (
    detect_cantidades_hospitalizacion,
    detect_hospitalizacion_codes,
)
from app.services.odontologia.mal_capitado import detect_mal_capitado

logger = logging.getLogger(__name__)


def detect_all_problems_urgencias(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Detecta TODOS los problemas en facturas de urgencias.

    Incluye detectores transversales y específicos de urgencias.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        (resultado_dict, responsables_map)
    """
    # 1. Códigos sin DB (ESS118 + IDE=969)
    from app.services.revision_sheet import _get_codigos_no_en_db_ess118

    problemas_codigos_no_en_db = _get_codigos_no_en_db_ess118(data_sheet, indices)
    codigos_no_en_db_set = {item["codigo"] for item in problemas_codigos_no_en_db}

    if problemas_codigos_no_en_db:
        logger.warning(
            "Procedimientos NO en DB (ESS118 + IDE=969): %d errores, códigos: %s",
            len(problemas_codigos_no_en_db),
            sorted(codigos_no_en_db_set),
        )
    else:
        logger.warning("No hay códigos sin DB con IDE=969 para ESS118")

    # 2. Centro Costo + IDE Contrato + CUPS equivalentes
    problemas_centros = detect_centro_costo_urgencias(data_sheet, indices)
    problemas_ide_contrato = detect_ide_contrato_urgencias(data_sheet, indices)

    problemas_cups_equivalentes: list[dict[str, str]] = []
    problemas_cups_equivalentes.extend(detect_cups_equivalentes(data_sheet, indices))
    problemas_cups_equivalentes.extend(detect_sala_observacion(data_sheet, indices))
    problemas_cups_equivalentes.extend(detect_hospitalizacion_codes(data_sheet, indices))

    # 3. Agregar "Código no en DB" a problemas_ide_contrato
    for problema in problemas_codigos_no_en_db:
        problemas_ide_contrato.append({
            "factura": problema.get("factura", ""),
            "ide_contrato_actual": "N/A",
            "ide_contrato_deberia": "Código no en DB",
            "procedimiento": problema.get("procedimiento", ""),
            "codigo": problema.get("codigo", ""),
            "entidad": problema.get("entidad", ""),
        })

    # 4. Detectores transversales
    decimales = detect_decimales(data_sheet, indices)
    tipo_identificacion_edad = detect_tipo_documento_edad(data_sheet, indices)
    entidad_afiliacion_comparison = detect_codigo_entidad_vs_entidad_afiliacion(
        data_sheet, indices, limit_log=5
    )
    tipo_usuario = detect_tipo_usuario(data_sheet, indices)

    # 5. Detectores específicos de urgencias
    # (import lazy para evitar circular imports con revision_sheet.py)
    from app.services.revision_sheet import (
        _detect_profesionales_urgencias,
        _detect_ide_contrato_reverse_urgencias,
        _detect_revision_entidad_86_urgencias,
        _detect_revision_cantidad_urgencias,
    )

    profesionales = _detect_profesionales_urgencias(data_sheet, indices)
    logger.info(
        "detect_all_problems_urgencias - Profesionales encontrados: %d",
        len(profesionales),
    )

    mal_capitado = detect_mal_capitado(data_sheet, indices)
    logger.info(
        "detect_all_problems_urgencias - MAL CAPITADO encontrados: %d",
        len(mal_capitado),
    )

    cantidades_urgencias = detect_cantidades_urgencias(data_sheet, indices)
    logger.info(
        "detect_all_problems_urgencias - Cantidades Urgencias encontradas: %d",
        len(cantidades_urgencias),
    )

    cantidades_soat_urgencias = detect_cantidades_soat_urgencias(data_sheet, indices)
    logger.info(
        "detect_all_problems_urgencias - Cantidades SOAT Urgencias encontradas: %d",
        len(cantidades_soat_urgencias),
    )

    cantidades_hospitalizacion = detect_cantidades_hospitalizacion(
        data_sheet, indices
    )
    logger.info(
        "detect_all_problems_urgencias - Cantidades Hospitalización encontradas: %d",
        len(cantidades_hospitalizacion),
    )

    cantidades_soat_hospitalizacion = detect_cantidades_soat_hospitalizacion(
        data_sheet, indices
    )
    logger.info(
        "detect_all_problems_urgencias - Cantidades SOAT Hospitalización encontradas: %d",
        len(cantidades_soat_hospitalizacion),
    )

    ide_contrato_reverse = _detect_ide_contrato_reverse_urgencias(
        data_sheet, indices
    )
    logger.info(
        "detect_all_problems_urgencias - IDE Contrato REVERSE encontrados: %d",
        len(ide_contrato_reverse),
    )

    revision_entidad_86 = _detect_revision_entidad_86_urgencias(
        data_sheet, indices
    )
    logger.info(
        "detect_all_problems_urgencias - Revision Entidad 86 encontradas: %d",
        len(revision_entidad_86),
    )

    revision_cantidad = _detect_revision_cantidad_urgencias(data_sheet, indices)
    logger.info(
        "detect_all_problems_urgencias - Revision Cantidad encontradas: %d",
        len(revision_cantidad),
    )

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

    # 9. Build normalized rows
    from app.services.revision_sheet import _build_urgencias_normalized_rows

    normalized_rows = _build_urgencias_normalized_rows(
        problemas_centros=problemas_centros_filtrados,
        problemas_ide_contrato=problemas_ide_contrato,
        problemas_cups_equivalentes=problemas_cups_equivalentes,
        mal_capitado=mal_capitado,
        cantidades_urgencias=cantidades_urgencias,
        cantidades_soat_urgencias=cantidades_soat_urgencias,
        cantidades_hospitalizacion=cantidades_hospitalizacion,
        cantidades_soat_hospitalizacion=cantidades_soat_hospitalizacion,
        responsables_map=responsable_cierra,
        decimales=decimales,
        tipo_identificacion_edad=tipo_identificacion_edad,
        profesionales=profesionales,
        entidad_afiliacion_comparison=entidad_afiliacion_comparison,
        fecha_cierre_vacia_map=fecha_cierre_vacia,
        tipo_usuario=tipo_usuario,
        revision_entidad_86=revision_entidad_86,
        revision_cantidad=revision_cantidad,
    )

    # 10. Build resultado dict
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
                    "centro_actual": item["centro_actual"],
                    "centro_deberia": item["centro_deberia"],
                    "prioridad": item.get("prioridad", 1),
                }
                for item in problemas_centros_filtrados
            ],
            "ide_contrato": [
                {
                    "factura": item["factura"],
                    "ide_contrato_actual": item["ide_contrato_actual"],
                    "ide_contrato_deberia": item["ide_contrato_deberia"],
                    "procedimiento": item.get("procedimiento", ""),
                    "codigo": item.get("codigo", ""),
                    "entidad": item.get("entidad", ""),
                    "nota": item.get("nota", ""),
                }
                for item in problemas_ide_contrato
            ],
            "cups_equivalentes": [
                {
                    "factura": item["factura"],
                    "codigo": item["codigo"],
                    "codigo_equiv": item["codigo_equiv"],
                    "accion": item["accion"],
                }
                for item in problemas_cups_equivalentes
            ],
            # reglas transversales
            "decimales": decimales,
            "tipo_identificacion_edad": tipo_identificacion_edad,
            "codigo_entidad_vs_afiliacion": entidad_afiliacion_comparison,
            "tipo_usuario": tipo_usuario,
            # reglas urgencias
            "profesionales": profesionales,
            "mal_capitado": mal_capitado,
            "cantidades_urgencias": cantidades_urgencias,
            "cantidades_soat_urgencias": cantidades_soat_urgencias,
            "cantidades_hospitalizacion": cantidades_hospitalizacion,
            "cantidades_soat_hospitalizacion": cantidades_soat_hospitalizacion,
            "revision_entidad_86": revision_entidad_86,
            "revision_cantidad": revision_cantidad,
        },
        "totales": {
            "centros_de_costos": len(problemas_centros),
            "ide_contrato": len(problemas_ide_contrato),
            "cups_equivalentes": len(problemas_cups_equivalentes),
            "decimales": len(decimales),
            "tipo_identificacion_edad": len(tipo_identificacion_edad),
            "codigo_entidad_vs_afiliacion": len(entidad_afiliacion_comparison),
            "tipo_usuario": len(tipo_usuario),
            "profesionales": len(profesionales),
            "mal_capitado": len(mal_capitado),
            "cantidades_urgencias": len(cantidades_urgencias),
            "cantidades_soat_urgencias": len(cantidades_soat_urgencias),
            "cantidades_hospitalizacion": len(cantidades_hospitalizacion),
            "cantidades_soat_hospitalizacion": len(cantidades_soat_hospitalizacion),
            "revision_entidad_86": len(revision_entidad_86),
            "revision_cantidad": len(revision_cantidad),
        },
        "missing_columns": [],
        "codigos_sin_db_ide_969": (
            sorted(codigos_no_en_db_set) if problemas_codigos_no_en_db else []
        ),
    }

    # 11. Enrich errors with responsable from mapping
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
