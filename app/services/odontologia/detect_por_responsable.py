"""Orquestador híbrido que rutea facturas odontológicas por responsable.

Cuando el Responsable Cierra Facturar es "Lopez Andrade Claudia Lorena"
se aplican reglas de odontología. Caso contrario, reglas de equipos básicos.

Uso
---
    detect_all_problems_odontologia_por_responsable(sheet, indices, ...)

Retorna la misma estructura que detect_all_problems_odontologia()
para que sea un reemplazo directo en exporter.py.
"""

from __future__ import annotations

import logging
from typing import Any

from app.constants import AREA_ODONTOLOGIA
from app.services.equipos_basicos.detect_all import detect_all_problems_equipos_basicos
from app.services.odontologia.detect_all import detect_all_problems_odontologia

logger = logging.getLogger(__name__)

FACTURADOR_ODONTOLOGIA = "LOPEZ ANDRADE CLAUDIA LORENA"

# Facturadores de urgencias que aparecen como Odontología en tipo_factura
# Para estos, centro de costo debe ser URGENCIAS
FACTURADORES_URGENCIAS: set[str] = {
    "ARIAS CULCHA ANGIE CAROLINA",
    "ESPAÑA DIAZ LORENY ALEJANDRA",
    "MEZA FERNANDEZ CARLOS OMAR",
    "PAEZ YULIETH DANIELA",
}


class _SimpleSheet:
    """Lightweight wrapper que expone solo las filas indicadas de un sheet existente.

    Interface duck-compatible con openpyxl Worksheet y con la clase
    ``_SimpleSheet`` de exporter.py (soporta ``.cell(row, column)``,
    ``.max_row`` y opcionalmente ``.title``).

    Row 1 es siempre la fila de encabezados original. Las filas de datos
    siguen en el orden proporcionado.
    """

    def __init__(self, original, row_numbers: list[int]) -> None:
        self._sheet = original
        self._rows = row_numbers  # 1-indexed, [1, data_row_1, data_row_2, ...]
        self.max_row = len(row_numbers)
        # .title es opcional — algunos wrappers (exporter._SimpleSheet) no lo tienen
        self.title: str = ""
        if hasattr(original, "title"):
            self.title = original.title

    def cell(self, row: int, column: int):
        """Retorna la celda en la fila virtual *row*, columna virtual *column*.

        Ambos índices son 1-based, igual que openpyxl.
        """
        actual_row = self._rows[row - 1]
        return self._sheet.cell(actual_row, column)


# ──────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────


def _partition_rows(
    data_sheet,
    indices: dict[str, int | None],
) -> tuple[list[int], list[int], list[int]] | None:
    """Escanea filas 2..N y particiona las de Odontología por responsable.

    Pasos:
        1. Si la columna ``responsable_cierra`` no existe → retorna ``None``
        2. Si ``tipo_factura_descripcion`` existe, filtra solo filas
           cuyo valor normalizado contenga ``"ODONTOLOG"``
        3. Para cada fila de Odontología, normaliza el responsable:
           - ``FACTURADOR_ODONTOLOGIA`` → odontología (lopez_rows)
           - ``FACTURADORES_URGENCIAS``  → odontología con centro costo URGENCIAS (urgencias_rows)
           - Cualquier otro             → equipos básicos (eb_rows)

    Returns:
        ``(lopez_rows, urgencias_rows, eb_rows)`` — listas de números de fila,
        o ``None`` si no se puede particionar.
    """
    responsable_cierra_idx = indices.get("responsable_cierra")
    if responsable_cierra_idx is None:
        return None

    tipo_factura_idx = indices.get("tipo_factura_descripcion")

    lopez_rows: list[int] = []
    urgencias_rows: list[int] = []
    eb_rows: list[int] = []

    for row in range(2, data_sheet.max_row + 1):
        # ── Filtrar solo filas con Tipo Factura = Odontología ──
        if tipo_factura_idx is not None:
            tipo_val = data_sheet.cell(
                row=row, column=tipo_factura_idx + 1
            ).value
            tipo_str = str(tipo_val).strip().upper() if tipo_val else ""
            if "ODONTOLOG" not in tipo_str:
                continue

        # ── Obtener responsable ──
        raw = data_sheet.cell(
            row=row, column=responsable_cierra_idx + 1
        ).value
        resp = str(raw).strip().upper() if raw else ""

        if resp == FACTURADOR_ODONTOLOGIA:
            lopez_rows.append(row)
        elif resp in FACTURADORES_URGENCIAS:
            urgencias_rows.append(row)
        else:
            eb_rows.append(row)

    return lopez_rows, urgencias_rows, eb_rows


def _merge_results(
    results: list[tuple[dict[str, Any], dict[str, str]]],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Fusiona múltiples resultados de detect_all en uno solo.

    Reglas de merge:
        - ``problemas.*`` listas → concatenación
        - ``totales.*`` → suma de enteros
        - ``normalizados`` → dedup por ``(tipo_error, factura, descripcion)``
        - ``responsables`` → merge de dicts
        - ``area`` se fija en ``AREA_ODONTOLOGIA``
    """
    merged_problems: dict[str, list] = {}
    merged_totales: dict[str, int] = {}
    merged_responsables: dict[str, str] = {}

    for resultado, rmap in results:
        merged_responsables.update(rmap)

        problemas = resultado.get("problemas", {})
        for key, items in problemas.items():
            if key not in merged_problems:
                merged_problems[key] = []
            if isinstance(items, list):
                merged_problems[key].extend(items)

        totales = resultado.get("totales", {})
        for key, value in totales.items():
            merged_totales[key] = merged_totales.get(key, 0) + (value or 0)

    # Dedup normalizados por (tipo_error, factura, descripcion)
    normalizados = merged_problems.get("normalizados", [])
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in normalizados:
        dedup_key = (
            str(item.get("tipo_error", "")),
            str(item.get("factura", "")),
            str(item.get("descripcion", "")),
        )
        if dedup_key not in seen:
            seen.add(dedup_key)
            unique.append(item)
    if unique:
        merged_problems["normalizados"] = unique

    merged: dict[str, Any] = {
        "area": AREA_ODONTOLOGIA,
        "problemas": merged_problems,
        "totales": merged_totales,
        "missing_columns": [],
    }

    return merged, merged_responsables


# ──────────────────────────────────────────────────────────────────────
# Función pública (reemplazo directo de detect_all_problems_odontologia)
# ──────────────────────────────────────────────────────────────────────


def detect_all_problems_odontologia_por_responsable(
    data_sheet,
    indices: dict[str, int | None],
    profesional_dias: dict[str, list[int]] | None = None,
    permitir_todos_centros: bool = True,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Detecta problemas routeando cada fila según su Responsable Cierra Facturar.

    * ``"LOPEZ ANDRADE CLAUDIA LORENA"`` → reglas de odontología
    * Cualquier otro valor (o vacío)       → reglas de equipos básicos

    Args:
        data_sheet: Sheet-like con interface ``.cell(row, column)`` y ``.max_row``
        indices: Diccionario {nombre_columna: índice 0-based}
        profesional_dias: Mapa {identificación: [días]} para validar centro costo
        permitir_todos_centros: Si True, permite todos los centros de costo

    Returns:
        Tupla ``(resultado_dict, responsables_map)`` con la misma estructura
        que ``detect_all_problems_odontologia``.
    """
    # ── 1. Particionar filas por responsable ──
    partition = _partition_rows(data_sheet, indices)

    if partition is None:
        logger.warning(
            "detect_por_responsable: columna 'responsable_cierra' no encontrada "
            "— usando detect_all_problems_odontologia como fallback"
        )
        return detect_all_problems_odontologia(
            data_sheet,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )

    lopez_rows, urgencias_rows, eb_rows = partition

    # ── 2. Si solo un grupo tiene filas, llamar directamente ──
    if lopez_rows and not urgencias_rows and not eb_rows:
        logger.info(
            "detect_por_responsable: %d filas → todas son odontología (Lopez Andrade), "
            "llamando detect_all_problems_odontologia directamente",
            len(lopez_rows),
        )
        return detect_all_problems_odontologia(
            data_sheet,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )

    if urgencias_rows and not lopez_rows and not eb_rows:
        logger.info(
            "detect_por_responsable: %d filas → todas son urgencias (facturadores URGENCIAS), "
            "llamando detect_all_problems_odontologia con centros_validos=['URGENCIAS']",
            len(urgencias_rows),
        )
        return detect_all_problems_odontologia(
            data_sheet,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
            centros_validos=["URGENCIAS"],
        )

    if eb_rows and not lopez_rows and not urgencias_rows:
        logger.info(
            "detect_por_responsable: %d filas → todas son equipos básicos, "
            "llamando detect_all_problems_equipos_basicos directamente",
            len(eb_rows),
        )
        return detect_all_problems_equipos_basicos(
            data_sheet,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )

    # ── 3. Múltiples grupos tienen filas → subsets + dispatch ──
    logger.info(
        "detect_por_responsable: %d filas odontología (Lopez), "
        "%d filas urgencias (Arias/España/Meza/Paez), "
        "%d filas equipos básicos, "
        "creando subsets",
        len(lopez_rows),
        len(urgencias_rows),
        len(eb_rows),
    )

    results: list[tuple[dict[str, Any], dict[str, str]]] = []

    if lopez_rows:
        sheet_lopez = _SimpleSheet(data_sheet, [1] + lopez_rows)
        logger.debug(
            "detect_por_responsable: subset odontología con %d filas",
            sheet_lopez.max_row - 1,
        )
        res_lopez, rmap_lopez = detect_all_problems_odontologia(
            sheet_lopez,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )
        results.append((res_lopez, rmap_lopez))

    if urgencias_rows:
        sheet_urg = _SimpleSheet(data_sheet, [1] + urgencias_rows)
        logger.debug(
            "detect_por_responsable: subset urgencias con %d filas",
            sheet_urg.max_row - 1,
        )
        res_urg, rmap_urg = detect_all_problems_odontologia(
            sheet_urg,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
            centros_validos=["URGENCIAS"],
        )
        results.append((res_urg, rmap_urg))

    if eb_rows:
        sheet_eb = _SimpleSheet(data_sheet, [1] + eb_rows)
        logger.debug(
            "detect_por_responsable: subset equipos básicos con %d filas",
            sheet_eb.max_row - 1,
        )
        res_eb, rmap_eb = detect_all_problems_equipos_basicos(
            sheet_eb,
            indices,
            profesional_dias=profesional_dias,
            permitir_todos_centros=permitir_todos_centros,
        )
        results.append((res_eb, rmap_eb))

    return _merge_results(results)
