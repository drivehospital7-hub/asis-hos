"""Detector de duplicados en facturas de farmacia para Urgencias.

Agrupa filas con tarifario "Suminstros, Medicamentos" por
(factura, codigo_tipo_procedimiento). Dentro de cada grupo, verifica
que TODOS los pares (código, cantidad) aparezcan al menos 2 veces.
Solo aplica para codigo_tipo_procedimiento = "09" o "12".
"""

from __future__ import annotations

import logging
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.constants.urgencias import (
    CODIGOS_TIPO_PROC_09_12,
    VALOR_TARIFARIO_FARMACIA,
)
from app.services.transversales.normalize import normalize_invoice

logger = logging.getLogger(__name__)


def detect_duplicados_farmacia(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> list[dict[str, Any]]:
    """Detecta grupos de farmacia donde todos los pares están duplicados.

    Filtra filas con tarifario = VALOR_TARIFARIO_FARMACIA y
    codigo_tipo_procedimiento en CODIGOS_TIPO_PROC_09_12.
    Agrupa por (factura, codigo_tipo_procedimiento). Dentro de cada
    grupo, cuenta ocurrencias de cada par (codigo, cantidad). Si TODOS
    los pares tienen count >= 2, el grupo completo se marca.

    Args:
        data_sheet: Hoja de Excel con los datos.
        indices: Índices de columnas.

    Returns:
        Lista de dicts con keys: factura, codigo_tipo_procedimiento,
        pares_duplicados, total_pares.
    """
    tipo_factura_idx = indices.get("tipo_factura_descripcion")
    num_fact_idx = indices.get("numero_factura")
    codigo_idx = indices.get("codigo")
    cantidad_idx = indices.get("cantidad")
    tarifario_idx = indices.get("tarifario")
    tipo_proc_idx = indices.get("codigo_tipo_procedimiento")

    # Guard: columnas requeridas faltantes
    if None in (tipo_factura_idx, num_fact_idx, tarifario_idx, tipo_proc_idx):
        logger.warning(
            "Duplicados Farmacia - Columnas necesarias no encontradas: "
            "tipo_factura_descripcion=%s, numero_factura=%s, tarifario=%s, "
            "codigo_tipo_procedimiento=%s",
            tipo_factura_idx,
            num_fact_idx,
            tarifario_idx,
            tipo_proc_idx,
        )
        return []

    # Nivel 1: agrupar filas filtradas por (factura, codigo_tipo_procedimiento)
    # Dentro de cada grupo, contar ocurrencias de cada (codigo, cantidad)
    grupos: dict[tuple[str, str], dict[tuple[str, int], int]] = {}

    for row in range(2, data_sheet.max_row + 1):
        # Filtrar por tipo_factura_descripcion = "Urgencias"
        tipo_factura = data_sheet.cell(row=row, column=tipo_factura_idx + 1).value
        tipo_factura_str = str(tipo_factura).strip() if tipo_factura else ""
        if tipo_factura_str != "Urgencias":
            continue

        numero_factura = data_sheet.cell(row=row, column=num_fact_idx + 1).value
        factura_str = normalize_invoice(numero_factura)
        if not factura_str:
            continue

        # Leer tarifario
        tarifario_val = data_sheet.cell(row=row, column=tarifario_idx + 1).value
        tarifario_str = str(tarifario_val).strip() if tarifario_val else ""
        if tarifario_str != VALOR_TARIFARIO_FARMACIA:
            continue

        # Leer codigo_tipo_procedimiento
        tipo_proc_val = data_sheet.cell(row=row, column=tipo_proc_idx + 1).value
        tipo_proc_str = str(tipo_proc_val).strip() if tipo_proc_val else ""
        if tipo_proc_str not in CODIGOS_TIPO_PROC_09_12:
            continue

        # Leer código (saltar si no hay)
        codigo = None
        if codigo_idx is not None:
            codigo_val = data_sheet.cell(row=row, column=codigo_idx + 1).value
            codigo = str(codigo_val).strip() if codigo_val else ""
        if not codigo:
            continue

        # Leer cantidad (None → 0)
        cantidad = 0
        if cantidad_idx is not None:
            cantidad_val = data_sheet.cell(row=row, column=cantidad_idx + 1).value
            if cantidad_val is not None:
                try:
                    cantidad = int(cantidad_val)
                except (ValueError, TypeError):
                    cantidad = 0

        # Agrupar
        grupo_key = (factura_str, tipo_proc_str)
        par_key = (codigo, cantidad)
        par_counts = grupos.setdefault(grupo_key, {})
        par_counts[par_key] = par_counts.get(par_key, 0) + 1

    # Segundo pase: emitir un item por grupo donde TODOS los pares tengan count >= 2
    resultados: list[dict[str, Any]] = []
    for (factura, tipo_proc), par_counts in grupos.items():
        total_pares = len(par_counts)
        pares_duplicados = [
            {"codigo": codigo, "cantidad": cantidad, "count": count}
            for (codigo, cantidad), count in par_counts.items()
            if count >= 2
        ]
        # Flag solo si todos los pares tienen count >= 2
        if len(pares_duplicados) == total_pares:
            resultados.append({
                "factura": factura,
                "codigo_tipo_procedimiento": tipo_proc,
                "pares_duplicados": pares_duplicados,
                "total_pares": total_pares,
            })

    if resultados:
        logger.info(
            "Duplicados Farmacia - %d grupos con duplicidad total encontrados",
            len(resultados),
        )
    else:
        logger.info("Duplicados Farmacia - No se encontraron grupos duplicados")

    return resultados
