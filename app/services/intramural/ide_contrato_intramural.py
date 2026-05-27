"""Detector de problemas de IDE Contrato en facturas de Intramural.

Solo aplica cuando Tipo Factura Descripción = "Intramural".
Reglas definidas en ide_contrato_rules.py y constantes de intramural.
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants.intramural import (
    TIPO_FACTURA_INTRAMURAL,
    CODIGOS_PYM_RUTAS,
    CODIGOS_PYM_NECESITAN_DX,
)
from app.services.transversales.normalize import normalize_invoice
from app.services.intramural.ide_contrato_rules import (
    IDE_SIMPLE_RULES,
    IDE_INSERTION_RULES,
    IDE_MULTIPLE_RULES,
    IDE_ESSC62_890405_RULES,
)

logger = logging.getLogger(__name__)

# PYM_RUTAS + Dx: según prefijo factura
_PYM_RUTAS_IDE_MAP: dict[str, set[str]] = {
    "EPSI05": {"977", "978"},
}
_PYM_RUTAS_EXCLUIDOS: frozenset[str] = frozenset()


def _check_pym_ruta_con_dx_ides(
    codigo: str,
    entidad: str,
    dx_principal: str,
    factura: str,
) -> set[str] | None:
    """Si código está en PYM_RUTAS, entidad tiene mapeo y Dx está en
    NECESITAN_DX, retorna el SET de IDEs válidos. Sino None."""
    if entidad not in _PYM_RUTAS_IDE_MAP:
        return None
    if codigo in _PYM_RUTAS_EXCLUIDOS:
        return None
    if codigo not in CODIGOS_PYM_RUTAS:
        return None
    if not dx_principal or dx_principal not in CODIGOS_PYM_NECESITAN_DX:
        return None

    return _PYM_RUTAS_IDE_MAP[entidad]


def detect_ide_contrato_intramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """
    Detecta facturas con problemas de IDE Contrato en Intramural.

    Args:
        data_sheet: Hoja de Excel con los datos
        indices: Índices de columnas

    Returns:
        Lista de dicts con: factura, codigo, entidad,
        ide_contrato_actual, ide_contrato_deberia
    """
    num_fact_idx = indices.get("numero_factura")
    codigo_idx = indices.get("codigo")
    ide_contrato_idx = indices.get("ide_contrato")
    entidad_idx = indices.get("codigo_entidad_cobrar")
    tipo_fact_desc_idx = indices.get("tipo_factura_descripcion")
    dx_principal_idx = indices.get("codigo_dx_principal")
    tarifario_idx = indices.get("tarifario")

    if any(idx is None for idx in (num_fact_idx, codigo_idx, ide_contrato_idx, entidad_idx)):
        logger.warning(
            "IDE Contrato Intramural - Columnas necesarias no encontradas"
        )
        return []

    problemas: list[dict[str, Any]] = []

    for row in range(2, data_sheet.max_row + 1):
        # Solo aplicar si Tipo Factura Descripción = "Intramural"
        if tipo_fact_desc_idx is not None:
            tipo_fact_val = data_sheet.cell(row=row, column=tipo_fact_desc_idx + 1).value
            if str(tipo_fact_val or "").strip().upper() != TIPO_FACTURA_INTRAMURAL.upper():
                continue

        numero = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura = normalize_invoice(numero)
        if not factura:
            continue

        codigo = str(data_sheet.cell(row=row, column=codigo_idx + 1).value or "").strip()
        ide_actual_raw = data_sheet.cell(row=row, column=ide_contrato_idx + 1).value
        entidad = str(data_sheet.cell(row=row, column=entidad_idx + 1).value or "").strip()
        ide_actual = str(ide_actual_raw or "").strip()

        if not codigo or not entidad:
            continue

        procedimiento = str(
            data_sheet.cell(row=row, column=indices.get("procedimiento", 0) + 1).value or ""
        ).strip()

        # --- Reglas exactas (codigo + entidad → IDE esperado) ---
        matched = False
        for rule in IDE_SIMPLE_RULES:
            if codigo == rule["codigo"] and entidad == rule["entidad"]:
                if ide_actual != rule["expected"]:
                    problemas.append({
                        "factura": factura,
                        "codigo": codigo,
                        "entidad": entidad,
                        "procedimiento": procedimiento,
                        "ide_contrato_actual": ide_actual,
                        "ide_contrato_deberia": rule["expected"],
                    })
                matched = True
                break

        if matched:
            continue

        # --- Regla: PYM_RUTAS + Dx Principal en NECESITAN_DX ---
        dx_principal = ""
        if dx_principal_idx is not None:
            dx_principal = str(
                data_sheet.cell(row=row, column=dx_principal_idx + 1).value or ""
            ).strip().upper()

        ides_validos = _check_pym_ruta_con_dx_ides(codigo, entidad, dx_principal, factura)
        if ides_validos is not None and ide_actual not in ides_validos:
            problemas.append({
                "factura": factura,
                "codigo": codigo,
                "entidad": entidad,
                "procedimiento": procedimiento,
                "ide_contrato_actual": ide_actual,
                "ide_contrato_deberia": "/".join(sorted(ides_validos)),
            })

        # --- Regla: Tarifario (COMENTADO - era ESS118) ---
        # if entidad == "ESS118" and tarifario_idx is not None:
        #     ...

        # --- Regla: IDE 971/972 (COMENTADO - era ESS118) ---
        # if entidad == "ESS118" and ide_actual in ("971", "972"):
        #     ...

    logger.info("IDE Contrato Intramural: %d problemas", len(problemas))
    return problemas
