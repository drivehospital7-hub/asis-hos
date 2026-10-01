"""Match producción vs carpetas por código FEV/CAP.

Reusa FEV_REGEX/CAP_REGEX de app.constants.monitoreo_carpetas (NO duplicar).
Solo faltantes: códigos de producción sin carpeta. Filas sin código
extraíble van a la lista aparte `revisar`.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from app.constants.monitoreo_carpetas import FEV_REGEX

logger = logging.getLogger(__name__)

# Semántica UI (app/templates/control_errores.html): estado "S" = Pendiente,
# cualquier otro valor = Resuelto. No hay constante compartida.
ESTADO_PENDIENTE = "S"

MOTIVO_PENDIENTE = "Novedad pendiente"
MOTIVO_RESUELTA_POSTERIOR = "Resuelta después de modificar carpeta"

_CORE_FEV = re.compile(FEV_REGEX, re.IGNORECASE)
_CORE_CAP = re.compile(r"CAP\d+", re.IGNORECASE)
"""Núcleo numérico del código para comparar.

OJO: CAP_REGEX (en constantes) define el formato *válido* de carpeta
CAP (`CAP001_CC123`) y NO se toca. Acá se extrae el núcleo (`CAP001`)
porque producción suele traer el número pelado (`CAP541133`) y las
carpetas el nombre completo: la identidad estable es el número.
"""


def extract_code(cell: Any) -> str | None:
    """Extrae el núcleo FEV\\d+ o CAP\\d+ de una celda.

    `FEV123 FALTA` → `FEV123`; `CAP541133` → `CAP541133`;
    `CAP001_CC123` → `CAP001`. Retorna en upper o None.
    """
    if cell is None:
        return None
    text = str(cell).strip()
    if not text:
        return None
    fev = _CORE_FEV.search(text)
    if fev:
        return fev.group(0).upper()
    cap = _CORE_CAP.search(text)
    if cap:
        return cap.group(0).upper()
    return None


def _folder_codes(facturas: list[Any]) -> set[str]:
    """Normaliza invoice_code de carpetas a núcleo upper para comparar."""
    codes: set[str] = set()
    for inv in facturas:
        code = extract_code(getattr(inv, "invoice_code", None))
        if code:
            codes.add(code)
    return codes


def _novedad_index(novedades: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    """Indexa la primera novedad por núcleo de código."""
    index: dict[str, dict[str, Any]] = {}
    for novedad in novedades or []:
        code = extract_code(novedad.get("factura"))
        if code and code not in index:
            index[code] = novedad
    return index


def _estado_novedad_flag(novedad: dict[str, Any] | None) -> str | None:
    """Normaliza el estado crudo a S/N sin etiquetar; None sin novedad."""
    if novedad is None:
        return None
    estado = novedad.get("estado")
    if estado == ESTADO_PENDIENTE:
        return "S"
    if estado:
        return "N"
    return None


def find_faltantes(
    rows: list[dict[str, Any]],
    facturas: list[Any],
    novedades: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cruza filas de producción contra facturas de carpetas.

    Args:
        rows: dicts {"numero_factura", "responsable", "fec_factura"} de reader.
        facturas: InvoiceRecord de monitoreo (invoice_code, ...).
        novedades: registros crudos de control de errores (``factura``,
            ``estado``). None = sin novedades.

    Returns:
        {"faltantes": [...], "revisar": [...], "resumen": {...}}.
        Cada faltante: {"codigo", "numero_factura_original",
        "responsable", "fec_factura", "estado_novedad" (S/N/None),
        "facturador" ("" : sin carpeta no hay facturador)}.
    """
    carpetas = _folder_codes(facturas)
    novedades_por_codigo = _novedad_index(novedades)
    faltantes: list[dict[str, Any]] = []
    revisar: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        original = row.get("numero_factura")
        code = extract_code(original)
        if code is None:
            revisar.append(
                {
                    "numero_factura_original": original,
                    "responsable": row.get("responsable"),
                    "fec_factura": row.get("fec_factura"),
                }
            )
            continue
        if code in carpetas or code in seen:
            continue
        seen.add(code)
        faltantes.append(
            {
                "codigo": code,
                "numero_factura_original": original,
                "responsable": row.get("responsable"),
                "fec_factura": row.get("fec_factura"),
                "estado_novedad": _estado_novedad_flag(novedades_por_codigo.get(code)),
                "facturador": "",
            }
        )
    resumen = {
        "total_produccion": len(rows),
        "total_carpetas": len(carpetas),
        "total_faltantes": len(faltantes),
        "total_revisar": len(revisar),
    }
    logger.info("Cruce: %d faltantes, %d a revisar", len(faltantes), len(revisar))
    return {"faltantes": faltantes, "revisar": revisar, "resumen": resumen}


def _parse_fecha_estado(value: Any) -> datetime | None:
    """Parsea una fecha ISO a datetime naive (local) o None si inválida/ausente."""
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _fecha_novedad(novedad: dict[str, Any]) -> tuple[datetime | None, str | None]:
    """Fecha-estado de una novedad con fallback, o (None, None)."""
    raw = (
        novedad.get("ultima_modificacion_estado")
        or novedad.get("actualizado_en")
        or novedad.get("creado_en")
    )
    parsed = _parse_fecha_estado(raw)
    return (parsed, parsed.isoformat() if parsed is not None else None)


def find_desactualizados(
    facturas: list[Any],
    novedades: list[dict[str, Any]],
    solo_codigos: set[str] | None = None,
) -> dict[str, Any]:
    """Cruza mtime de carpetas contra novedades con mismo código.

    Args:
        facturas: InvoiceRecord de monitoreo (invoice_code, mtime, ...).
        novedades: registros crudos de control de errores
            (``factura``, ``estado``, ``ultima_modificacion_estado``
            con fallback ``actualizado_en``/``creado_en``).
        solo_codigos: si se provee, solo se evalúan carpetas cuyo núcleo
            esté en el set (ej. facturas del Excel en proceso).
            None = todas las carpetas escaneadas.

    Returns:
        {"desactualizados": [...], "resumen": {"total_desactualizados": n}}.
        Cada entry: {"codigo", "facturador", "full_path",
        "mtime_carpeta" (ISO o None), "estado_novedad", "motivo",
        "fecha_estado" (ISO o None)}. Dedup por código (primera
        novedad relevante).
    """
    por_codigo: dict[str, list[dict[str, Any]]] = {}
    for novedad in novedades:
        code = extract_code(novedad.get("factura"))
        if code:
            por_codigo.setdefault(code, []).append(novedad)

    # Dedup por código: la primera factura decide (facturador/ruta/mtime).
    primera_factura: dict[str, Any] = {}
    for inv in facturas:
        code = extract_code(getattr(inv, "invoice_code", None))
        if code and code not in primera_factura:
            primera_factura[code] = inv

    desactualizados: list[dict[str, Any]] = []
    for code, inv in primera_factura.items():
        if solo_codigos is not None and code not in solo_codigos:
            continue
        lista = por_codigo.get(code)
        if not lista:
            continue
        mtime = getattr(inv, "mtime", None)
        mtime_dt = datetime.fromtimestamp(mtime) if mtime is not None else None
        mtime_iso = mtime_dt.isoformat() if mtime_dt is not None else None

        pendiente = next(
            (n for n in lista if n.get("estado") == ESTADO_PENDIENTE), None
        )
        if pendiente is not None:
            _, fecha_iso = _fecha_novedad(pendiente)
            desactualizados.append({
                "codigo": code,
                "facturador": getattr(inv, "facturador", ""),
                "full_path": getattr(inv, "full_path", ""),
                "mtime_carpeta": mtime_iso,
                "estado_novedad": pendiente.get("estado"),
                "motivo": MOTIVO_PENDIENTE,
                "fecha_estado": fecha_iso,
            })
            continue

        # Sin mtime no hay regla de resuelta (no comparable).
        if mtime_dt is None:
            continue
        posterior: dict[str, Any] | None = None
        posterior_iso: str | None = None
        for novedad in lista:
            fecha, fecha_iso = _fecha_novedad(novedad)
            if fecha is not None and fecha > mtime_dt:
                posterior = novedad
                posterior_iso = fecha_iso
                break
        if posterior is None:
            continue
        desactualizados.append({
            "codigo": code,
            "facturador": getattr(inv, "facturador", ""),
            "full_path": getattr(inv, "full_path", ""),
            "mtime_carpeta": mtime_iso,
            "estado_novedad": posterior.get("estado"),
            "motivo": MOTIVO_RESUELTA_POSTERIOR,
            "fecha_estado": posterior_iso,
        })

    logger.info("Cruce desactualizados: %d", len(desactualizados))
    return {
        "desactualizados": desactualizados,
        "resumen": {"total_desactualizados": len(desactualizados)},
    }
