"""Normalización de errores a filas de 6 columnas (genérico por tipo_factura).

Reemplaza a urgencias/normalized_rows.py y odontologia/normalized_rows.py
con un builder parametrizado por error_groups: dict que mapea tipo_error -> lista de dicts.
"""

from __future__ import annotations

import calendar
import os
from datetime import datetime
from string import Formatter
from typing import Any

from app.constants.grupo_error import NAMED_FORMATTER_GROUPS


def _parse_fecha_edad(value: Any) -> datetime | None:
    """Parsea fecha de nacimiento/factura en datetime o None.

    Acepta datetime, date y strings ISO o día-primero.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # date (no datetime) -> medianoche, para comparar solo calendario
    try:
        from datetime import date as _date

        if isinstance(value, _date):
            return datetime(value.year, value.month, value.day)
    except (ValueError, TypeError):
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S.%f",
                "%d/%m/%Y", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _add_meses_clamp(nac_day: int, base_y: int, base_m: int, meses: int) -> datetime:
    """Suma meses a (base_y, base_m) clampando el día al fin de mes."""
    total = (base_m - 1) + meses
    y = base_y + total // 12
    m = total % 12 + 1
    d = min(nac_day, calendar.monthrange(y, m)[1])
    return datetime(y, m, d)


def _build_edad_detalle(anios: int, meses_residuales: int,
                        fec_nac_raw: Any, fec_fact_raw: Any) -> str:
    """Construye 'X años Y meses Z días' por diferencia de calendario.

    Recomputa años/meses/días desde las fechas (ignora los valores
    de entrada, que pueden venir residuales o totales según el
    detector/engine). Nunca inventa: si alguna fecha no parsea o
    factura < nacimiento, retorna "".

    Invariantes: 0 <= meses <= 11, 0 <= días <= 30. Omite partes
    en 0 ("7 años 12 días", "5 meses 3 días", "0 días" si iguales).
    Fin de mes con day clamp (nac 31/01 -> anchor 28/02).
    """
    del anios, meses_residuales  # se recomputan desde fechas; firma kept por compat
    fec_nac = _parse_fecha_edad(fec_nac_raw)
    fec_fact = _parse_fecha_edad(fec_fact_raw)
    if fec_nac is None or fec_fact is None:
        return ""
    nac_d = fec_nac.date()
    fact_d = fec_fact.date()
    if fact_d < nac_d:
        return ""

    # Años por aniversario clampado (29/02 -> 28/02 en no bisiestos)
    calc_anios = fact_d.year - nac_d.year
    aniversario = _add_meses_clamp(nac_d.day, nac_d.year, nac_d.month, calc_anios * 12)
    if fact_d < aniversario.date():
        calc_anios -= 1
        aniversario = _add_meses_clamp(nac_d.day, nac_d.year, nac_d.month, calc_anios * 12)

    # Meses completos desde el aniversario
    meses = (fact_d.year - aniversario.year) * 12 + (fact_d.month - aniversario.month)
    anchor = _add_meses_clamp(
        nac_d.day, aniversario.year, aniversario.month, meses)
    if fact_d < anchor.date():
        meses -= 1
        anchor = _add_meses_clamp(
            nac_d.day, aniversario.year, aniversario.month, meses)
    dias = (fact_d - anchor.date()).days
    if dias < 0:
        dias = 0

    partes = []
    if calc_anios > 0:
        partes.append(f"{calc_anios} años")
    if meses > 0:
        partes.append(f"{meses} meses")
    if dias > 0 or not partes:
        partes.append(f"{dias} días")
    return " ".join(partes)


# Legacy generic-fallback group-by key order. The grupo_error generic mapper
# replicates this exact order so sparse-dict groups stay byte-stable.
GENERIC_FALLBACK_KEY_ORDER = (
    "codigo", "vlr_subsidiado", "tipo_identificacion", "cantidad",
    "centro_costo", "codigo_entidad_cobrar", "observacion", "accion",
    "identificacion",
)

# Named-formatter registry keyed by grupo_error (populated with the 5 special
# formatters). Unknown keys fall through to the generic mapper.
GRUPO_FORMATTERS: dict[str, Any] = {}


def _format_tipo_id_edad(item: dict, mapping: dict) -> dict[str, str]:
    """Tipo Identificacion / Edad: edad recompute + identificacion procedimiento."""
    num_id = item.get("identificacion", "") or item.get("numero_identificacion", "")
    tipo_actual = item.get("tipo_actual", "")
    tipo_deberia = item.get("tipo_deberia", "")
    problema = item.get("problema", "")
    edad_anios_raw = item.get("edad_anios") if "edad_anios" in item else item.get("date.edad")
    edad_meses_raw = item.get("edad_meses") if "edad_meses" in item else item.get("date.edad_meses")
    try:
        anios = int(edad_anios_raw) if edad_anios_raw is not None else 0
    except (ValueError, TypeError):
        anios = 0
    try:
        meses_residuales = int(edad_meses_raw) if edad_meses_raw is not None else 0
        meses_residuales %= 12
    except (ValueError, TypeError):
        meses_residuales = 0
    return {
        "descripcion": problema or f"Tipo actual {tipo_actual} debería ser {tipo_deberia}",
        "procedimiento": str(num_id).strip() if num_id else "",
        "detalle": _build_edad_detalle(
            anios, meses_residuales, item.get("fec_nacimiento"), item.get("fec_factura")),
    }


def _format_codigo_entidad(item: dict, mapping: dict) -> dict[str, str]:
    """Codigo-Entidad-vs-Afiliacion: as_ms/86000 branches + legacy branch."""
    if "tipo_identificacion" in item:
        tipo_id = item.get("tipo_identificacion", "")
        cod_actual = item.get("cod_entidad_actual", "")
        cod_esperado = item.get("cod_entidad_esperado", "")
        problema_key = item.get("problema", "")
        if problema_key == "as_ms_requiere_86000":
            desc = f"Tipo ID {tipo_id} requiere Cód Entidad Cobrar = {cod_esperado}"
            detalle = f"Actual: {cod_actual}"
        elif problema_key == "86000_solo_para_as_ms":
            desc = f"Cód Entidad Cobrar = {cod_actual} solo válido para AS/MS"
            detalle = f"Tipo ID actual: {tipo_id}"
        else:
            desc = item.get("problema", "")
            detalle = f"Tipo ID: {tipo_id}, Cód: {cod_actual}"
        return {
            "descripcion": desc, "procedimiento": str(cod_actual),
            "detalle": detalle, "_header_override": "Código Entidad",
        }
    cod = item.get("codigo_entidad_cobrar", "")
    nombre = item.get("entidad_cobrar_nombre", "")
    return {
        "descripcion": item.get("problema", ""),
        "procedimiento": f"{cod} - {nombre}" if cod and nombre else str(cod),
        "detalle": f"Afiliación: {item.get('entidad_afiliacion', '')}",
        "_header_override": "Entidad de factura",
    }


def _format_duplicados_farmacia(item: dict, mapping: dict) -> dict[str, str]:
    """Duplicados-Farmacia: pares-join, tipo remapped to Revision-Necesaria."""
    tipo_proc = item.get("codigo_tipo_procedimiento", "")
    total_pares = item.get("total_pares", 0)
    pares = item.get("pares_duplicados", [])
    problema = item.get("problema", "")
    detalle_pares = "; ".join(
        f"{p.get('codigo', '')} x{p.get('cantidad', '')} ({p.get('count', 0)} veces)"
        for p in pares) if pares else ""
    if problema:
        descripcion = problema
        procedimiento = _combine_procedimiento(
            item.get("codigo", ""), item.get("procedimiento", "")) or (
            f"Grupo {tipo_proc}" if tipo_proc else "")
    elif tipo_proc:
        descripcion = (f"Duplicados Farmacia — Grupo {tipo_proc}: "
                       f"{total_pares} par(es) duplicado(s)")
        procedimiento = f"Grupo {tipo_proc}"
    else:
        descripcion = f"Duplicados Farmacia: {total_pares} par(es) duplicado(s)"
        procedimiento = ""
    return {
        "tipo_error": "Revision-Necesaria",
        "descripcion": descripcion,
        "procedimiento": procedimiento,
        "detalle": detalle_pares or f"{total_pares} pares",
    }


def _format_cups_equivalentes(item: dict, mapping: dict) -> dict[str, str]:
    """Cups-Equivalentes: codigo-list procedimiento + estancia detalle."""
    codigo_raw = item.get("codigo", "")
    proc_raw = item.get("procedimiento", "")
    estancia_str = item.get("estancia_str", "")
    if isinstance(codigo_raw, list):
        codigo_str = ", ".join(str(c) for c in codigo_raw)
    else:
        codigo_str = str(codigo_raw)
    proc_str = str(proc_raw).strip() if proc_raw else ""
    return {
        "descripcion": item.get("problema", "") or item.get("accion", ""),
        "procedimiento": proc_str if proc_str else codigo_str,
        "detalle": f"Estancia: {estancia_str}" if estancia_str else codigo_str,
    }


def _format_revision_necesaria(item: dict, mapping: dict) -> dict[str, str]:
    """Revision-Necesaria: passthrough with descripcion inference."""
    detalle = item.get("detalle", "")
    descripcion = item.get("descripcion", "")
    if not descripcion:
        if "Cant:" in str(detalle):
            descripcion = "Cantidad > 1 con código no exento requiere revisión manual"
        elif detalle == "86":
            descripcion = "Cód Entidad Cobrar = 86 requiere revisión manual"
        else:
            descripcion = item.get("problema", "Revisión necesaria")
    return {
        "descripcion": descripcion,
        "procedimiento": _combine_procedimiento(item.get("codigo", ""), item.get("procedimiento", "")),
        "detalle": str(detalle),
    }


GRUPO_FORMATTERS.update({
    "Tipo Identificacion / Edad": _format_tipo_id_edad,
    "Codigo-Entidad-vs-Afiliacion": _format_codigo_entidad,
    "Duplicados-Farmacia": _format_duplicados_farmacia,
    "Cups-Equivalentes": _format_cups_equivalentes,
    "Revision-Necesaria": _format_revision_necesaria,
})


def is_grupo_error_mapping_enabled() -> bool:
    """Cutover flag: True routes build_normalized_rows through grupo mapping."""
    return os.getenv("GRUPO_ERROR_MAPPING", "false").strip().lower() == "true"


def _combine_procedimiento(codigo: Any, procedimiento: Any) -> str:
    """Combine codigo + procedimiento nombre as 'COD - Nombre' (pure)."""
    codigo = str(codigo).strip() if codigo else ""
    procedimiento = str(procedimiento).strip() if procedimiento else ""
    if codigo and procedimiento:
        return f"{codigo} - {procedimiento}"
    return codigo or procedimiento or ""


def _safe_format(template: str, item: dict) -> str:
    """Format a template with item fields; missing keys render as ''."""
    try:
        return Formatter().vformat(template, (), _DefaultDict(item))
    except (ValueError, IndexError, KeyError):
        return ""


class _DefaultDict(dict):
    """Missing keys render as empty string in _safe_format."""

    def __missing__(self, key: str) -> str:
        return ""


def _resolve_procedimiento(item: dict, a_campo: str | None) -> str:
    """Resolve procedimiento from detalle_a_campo: '=literal', 'f1,f2' pair, field."""
    if not a_campo:
        return ""
    if a_campo.startswith("="):
        return a_campo[1:]
    if "," in a_campo:
        first, second = (p.strip() for p in a_campo.split(",", 1))
        return _combine_procedimiento(item.get(first, ""), item.get(second, ""))
    value = item.get(a_campo, "")
    return str(value).strip() if value is not None else ""


def _resolve_detalle(item: dict, b_campo: str | None) -> str:
    """Resolve detalle from detalle_b_campo: '=literal', template, fallback list, field."""
    if not b_campo:
        return ""
    if b_campo.startswith("="):
        return b_campo[1:]
    if "{" in b_campo:
        return _safe_format(b_campo, item)
    if "," in b_campo:
        for name in (p.strip() for p in b_campo.split(",")):
            value = item.get(name, "")
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""
    value = item.get(b_campo, "")
    return str(value).strip() if value is not None else ""


def _build_grupo_mapped_rows(
    error_groups: dict[str, list],
    responsables_map: dict[str, str],
    fec_factura_map: dict[str, str],
    fecha_cierre_vacia_map: dict[str, bool],
    grupo_mappings: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Build rows from grupo_error-keyed groups via formatters or generic mapper."""
    rows: list[dict[str, str]] = []

    def _row_base(grupo: str, factura: str) -> dict[str, str]:
        return {
            "tipo_error": grupo,
            "factura": factura,
            "fec_factura": fec_factura_map.get(factura, ""),
            "responsable_cierra": responsables_map.get(factura, ""),
            "fecha_cierre_vacia": fecha_cierre_vacia_map.get(factura, False),
        }

    for grupo, group_list in error_groups.items():
        formatter = GRUPO_FORMATTERS.get(grupo)
        mapping = grupo_mappings.get(grupo, {})
        a_campo = mapping.get("detalle_a_campo")
        b_campo = mapping.get("detalle_b_campo")
        template = mapping.get("descripcion_template")
        for raw in group_list or []:
            item = {"factura": str(raw)} if isinstance(raw, str) else dict(raw)
            factura = str(item.get("factura", ""))
            if formatter is not None:
                row = _row_base(grupo, factura)
                row.update(formatter(item, mapping))
                rows.append(row)
                continue
            descripcion = _safe_format(template, item) if template else item.get("problema", "")
            row = _row_base(grupo, factura)
            row["descripcion"] = descripcion
            row["procedimiento"] = _resolve_procedimiento(item, a_campo)
            row["detalle"] = _resolve_detalle(item, b_campo)
            if grupo not in NAMED_FORMATTER_GROUPS and not any([a_campo, b_campo, template]):
                row["mapping_completa"] = False
            rows.append(row)

    _attach_regla_and_fallback(rows, error_groups, {"Duplicados-Farmacia": "Revision-Necesaria"})
    return rows


def _attach_regla_and_fallback(
    rows: list[dict],
    error_groups: dict[str, list],
    key_to_tipo_remap: dict[str, str],
) -> None:
    """Enrich rows with regla ids and fill empty procedimiento via key order."""
    _item_reglas: dict[tuple[str, str], str] = {}
    for grupo_key, group_list in error_groups.items():
        tipo = key_to_tipo_remap.get(grupo_key, grupo_key)
        if isinstance(group_list, list):
            for item in group_list:
                if isinstance(item, dict):
                    r = item.get("regla", "")
                    f = item.get("factura", "")
                    if r and f:
                        key = (f, tipo)
                        if key not in _item_reglas:
                            _item_reglas[key] = r
    for row in rows:
        f = row.get("factura", "")
        t = row.get("tipo_error", "")
        r = _item_reglas.get((f, t))
        row["regla"] = r if r else ""

    if rows:
        all_items: list[dict] = []
        for group_list in error_groups.values():
            if isinstance(group_list, list):
                for item in group_list:
                    if isinstance(item, dict):
                        all_items.append(item)
        factura_to_item = {}
        for item in all_items:
            f = item.get("factura", "")
            if f:
                factura_to_item[f] = item
        for row in rows:
            if not row.get("procedimiento") and not row.get("detalle"):
                item = factura_to_item.get(row.get("factura", ""))
                if item:
                    for key in GENERIC_FALLBACK_KEY_ORDER:
                        val = item.get(key, "")
                        if val:
                            row["procedimiento"] = str(val)
                            break


def build_normalized_rows(
    error_groups: dict[str, list],
    responsables_map: dict[str, str],
    fec_factura_map: dict[str, str] | None = None,
    fecha_cierre_vacia_map: dict[str, bool] | None = None,
    *,
    use_grupo_mapping: bool | None = None,
    grupo_mappings: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """Normaliza todos los tipos de error en filas de 6 columnas.

    Args:
        error_groups: dict {tipo_error_label: [detector_result_dict, ...]}
        responsables_map: dict {factura: responsable}
        fec_factura_map: dict {factura: fecha_factura} (opcional)
        fecha_cierre_vacia_map: dict {factura: True si Fecha Cierre está vacía} (opcional)

    Returns:
        Lista de dicts con keys: tipo_error, factura, fec_factura,
        responsable_cierra, descripcion, procedimiento, detalle, fecha_cierre_vacia
    """
    enabled = use_grupo_mapping if use_grupo_mapping is not None else is_grupo_error_mapping_enabled()
    if enabled:
        return _build_grupo_mapped_rows(
            error_groups,
            responsables_map,
            fec_factura_map or {},
            fecha_cierre_vacia_map or {},
            grupo_mappings or {},
        )

    rows: list[dict[str, str]] = []
    _fec_factura_map = fec_factura_map or {}
    _fecha_cierre_vacia_map = fecha_cierre_vacia_map or {}

    def _get_fecha_cierre_vacia(factura: str) -> bool:
        return _fecha_cierre_vacia_map.get(factura, False)

    def _get_responsable(factura: str) -> str:
        return responsables_map.get(factura, "")

    def _get_fec_factura(factura: str) -> str:
        return _fec_factura_map.get(factura, "")

    def _build_procedimiento(codigo: str, procedimiento: str) -> str:
        return _combine_procedimiento(codigo, procedimiento)

    # --- Centros de Costo ---
    for item in error_groups.get("Centros de Costo", []):
        factura = item.get("factura", str(item.get("invoice", "")))
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        problema = item.get("problema", "")
        descripcion = problema or f"Centro de costo debería ser {item.get('centro_deberia', 'N/A')}"
        detalle = item.get("centro_actual", "") or item.get("centro_costo", "")
        rows.append({
            "tipo_error": "Centros de Costo",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- IDE Contrato ---
    for item in error_groups.get("IDE Contrato", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        ide_deberia = item.get("ide_contrato_deberia", "N/A")
        problema = item.get("problema", "")
        if problema:
            descripcion = problema
        elif ide_deberia in ("Código no en DB", "CÓDIGO NO EN DB"):
            descripcion = ide_deberia
        else:
            descripcion = f"IDE Contrato debería ser {ide_deberia}"
        rows.append({
            "tipo_error": "IDE Contrato",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": item.get("ide_contrato_actual", "") or item.get("ide_contrato", ""),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cups Equivalentes ---
    for item in error_groups.get("Cups Equivalentes", []):
        factura = item.get("factura", "")
        codigo_raw = item.get("codigo", "")
        proc_raw = item.get("procedimiento", "")
        estancia_str = item.get("estancia_str", "")
        if isinstance(codigo_raw, list):
            codigo_str = ", ".join(str(c) for c in codigo_raw)
        else:
            codigo_str = str(codigo_raw)
        proc_str = str(proc_raw).strip() if proc_raw else ""
        proc_final = proc_str if proc_str else codigo_str
        detalle = f"Estancia: {estancia_str}" if estancia_str else codigo_str
        problema = item.get("problema", "")
        rows.append({
            "tipo_error": "Cups Equivalentes",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": problema or item.get("accion", ""),
            "procedimiento": proc_final,
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- MAL CAPITADO ---
    for item in error_groups.get("MAL CAPITADO", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        problema = item.get("problema", "")
        descripcion = problema or item.get("observacion", "")
        detalle = item.get("ide_contrato", "") or item.get("ide_contrato_actual", "")
        rows.append({
            "tipo_error": "MAL CAPITADO",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cantidades (genérico — Urgencias, SOAT Urgencias, Hospitalización, SOAT Hospitalización) ---
    for tipo_error, desc_template in [
        ("Cantidades", "Cantidad {cantidad} debe ser ≤ 1 en Urgencias"),
        ("Cantidades SOAT", "Cantidad {cantidad} debe ser = 1 (SOAT Urgencias)"),
        ("Cantidades Hospitalización", "Cantidad {cantidad} debería ser {cantidad_esperada}"),
        ("Cantidades SOAT Hospitalización", "Cantidad {cantidad} debería ser {cantidad_esperada} (SOAT Hospitalización)"),
    ]:
        for item in error_groups.get(tipo_error, []):
            factura = item.get("factura", "")
            codigo = item.get("codigo", "")
            proc = item.get("procedimiento", "")
            cantidad = item.get("cantidad", "")
            cantidad_esperada = item.get("cantidad_esperada", "")
            problema = item.get("problema", "")
            if problema:
                descripcion = problema
            else:
                descripcion = desc_template.format(
                    cantidad=cantidad,
                    cantidad_esperada=cantidad_esperada,
                )
            rows.append({
                "tipo_error": tipo_error,
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": descripcion,
                "procedimiento": _build_procedimiento(codigo, proc),
                "detalle": str(cantidad),
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- Decimales ---
    # Compatibilidad: legacy retorna list[str], engine retorna list[dict]
    for item in error_groups.get("Decimales", []):
        factura = item if isinstance(item, str) else item.get("factura", "")
        rows.append({
            "tipo_error": "Decimales",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": "Valores con decimales",
            "procedimiento": "Vlr. Procedimiento",
            "detalle": "Vlr. Subsidiado",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Tipo Identificación / Edad ---
    for item in error_groups.get("Tipo Identificación / Edad", []):
        factura = item.get("factura", "")
        # Engine usa key "identificacion" (row_store); detector Python
        # usa "numero_identificacion". Fallback en ese orden.
        num_id = item.get("identificacion", "") or item.get("numero_identificacion", "")
        tipo_actual = item.get("tipo_actual", "")
        tipo_deberia = item.get("tipo_deberia", "")
        problema = item.get("problema", "")

        # Compatibilidad: Python detector ↔ rule engine
        # Python detector: edad_anios (años), edad_meses (residual %12)
        # Rule engine:     date.edad (años), date.edad_meses (total, no residual)
        edad_anios_raw = item.get("edad_anios") if "edad_anios" in item else item.get("date.edad")
        edad_meses_raw = item.get("edad_meses") if "edad_meses" in item else item.get("date.edad_meses")
        try:
            anios = int(edad_anios_raw) if edad_anios_raw is not None else 0
        except (ValueError, TypeError):
            anios = 0
        try:
            meses_residuales = int(edad_meses_raw) if edad_meses_raw is not None else 0
            # date.edad_meses es total (ej: 89), necesitamos residual %12
            meses_residuales %= 12
        except (ValueError, TypeError):
            meses_residuales = 0

        detalle = _build_edad_detalle(
            anios, meses_residuales,
            item.get("fec_nacimiento"), item.get("fec_factura"),
        )

        descripcion = problema or f"Tipo actual {tipo_actual} debería ser {tipo_deberia}"
        rows.append({
            "tipo_error": "Tipo Identificación / Edad",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": num_id,
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Profesionales ---
    for item in error_groups.get("Profesionales", []):
        factura = item.get("factura", "")
        cod_prof = item.get("codigo_profesional", "")
        proc_nombre = item.get("procedimiento", "")
        rows.append({
            "tipo_error": "Profesionales",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": item.get("problema", item.get("regla", "")),
            "procedimiento": _build_procedimiento(cod_prof, proc_nombre),
            "detalle": f"Cód: {cod_prof}" if cod_prof else "",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Código Entidad vs Afiliación ---
    for item in error_groups.get("Código Entidad vs Afiliación", []):
        factura = item.get("factura", "")
        # Detectar si es del detector nuevo (tipo_identificacion_entidad) o viejo
        if "tipo_identificacion" in item:
            # Nuevo detector: tipo_identificacion_entidad (AS/MS ↔ 86000)
            tipo_id = item.get("tipo_identificacion", "")
            cod_actual = item.get("cod_entidad_actual", "")
            cod_esperado = item.get("cod_entidad_esperado", "")
            problema_key = item.get("problema", "")
            if problema_key == "as_ms_requiere_86000":
                desc = f"Tipo ID {tipo_id} requiere Cód Entidad Cobrar = {cod_esperado}"
                detalle = f"Actual: {cod_actual}"
            elif problema_key == "86000_solo_para_as_ms":
                desc = f"Cód Entidad Cobrar = {cod_actual} solo válido para AS/MS"
                detalle = f"Tipo ID actual: {tipo_id}"
            else:
                desc = item.get("problema", "")
                detalle = f"Tipo ID: {tipo_id}, Cód: {cod_actual}"
            rows.append({
                "tipo_error": "Código Entidad vs Afiliación",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": desc,
                "procedimiento": cod_actual,
                "detalle": detalle,
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
                "_header_override": "Código Entidad",
            })
        else:
            # Viejo detector: codigo_entidad_vs_entidad_afiliacion
            cod = item.get("codigo_entidad_cobrar", "")
            nombre = item.get("entidad_cobrar_nombre", "")
            proc_entidad = f"{cod} - {nombre}" if cod and nombre else cod
            rows.append({
                "tipo_error": "Código Entidad vs Afiliación",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": item.get("problema", ""),
                "procedimiento": proc_entidad,
                "detalle": f"Afiliación: {item.get('entidad_afiliacion', '')}",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
                "_header_override": "Entidad de factura",
            })

    # --- Tipo Usuario ---
    for item in error_groups.get("Tipo Usuario", []):
        factura = item.get("factura", "")
        tipo_actual = item.get("tipo_actual", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        problema = item.get("problema", "")
        descripcion = problema or "Revisar tipo usuario en Targetero"
        rows.append({
            "tipo_error": "Tipo Usuario",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": tipo_actual,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- ⚠️ Revisión Necesaria: Entidad 86 ---
    for item in error_groups.get("⚠️ Revisión Necesaria", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        detalle = item.get("detalle", "")
        descripcion = item.get("descripcion", "")
        if not descripcion:
            # Fallback: infer from item structure
            if "Cant:" in str(detalle):
                descripcion = "Cantidad > 1 con código no exento requiere revisión manual"
            elif detalle == "86":
                descripcion = "Cód Entidad Cobrar = 86 requiere revisión manual"
            else:
                descripcion = item.get("problema", "Revisión necesaria")
        rows.append({
            "tipo_error": "⚠️ Revisión Necesaria",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Copago vs Entidad ---
    for item in error_groups.get("Copago vs Entidad", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        entidad = item.get("entidad_cobrar", "")
        copago = item.get("vlr_copago", "")
        rows.append({
            "tipo_error": "Copago vs Entidad",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": "Vlr. Copago debe ser 0 cuando entidad no es default",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": f"Ent: {entidad}, Copago: {copago}",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- ⚠️ Revisión Necesaria: Duplicados Farmacia (via separate key to avoid collision) ---
    for item in error_groups.get("Duplicados Farmacia", []):
        factura = item.get("factura", "")
        tipo_proc = item.get("codigo_tipo_procedimiento", "")
        total_pares = item.get("total_pares", 0)
        pares = item.get("pares_duplicados", [])
        problema = item.get("problema", "")
        detalle_pares = "; ".join(
            f"{p.get('codigo', '')} x{p.get('cantidad', '')} ({p.get('count', 0)} veces)"
            for p in pares
        ) if pares else ""
        if problema:
            descripcion = problema
            procedimiento = _build_procedimiento(
                item.get("codigo", ""), item.get("procedimiento", "")
            ) or (f"Grupo {tipo_proc}" if tipo_proc else "")
        elif tipo_proc:
            descripcion = (
                f"Duplicados Farmacia — Grupo {tipo_proc}: "
                f"{total_pares} par(es) duplicado(s)"
            )
            procedimiento = f"Grupo {tipo_proc}"
        else:
            descripcion = (
                f"Duplicados Farmacia: "
                f"{total_pares} par(es) duplicado(s)"
            )
            procedimiento = ""
        rows.append({
            "tipo_error": "⚠️ Revisión Necesaria",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": procedimiento,
            "detalle": detalle_pares or f"{total_pares} pares",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cups Sin Contrato ---
    for item in error_groups.get("Cups Sin Contrato", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        entidad = item.get("entidad", "")
        cod_ent = item.get("codigo_entidad_cobrar", "")
        rows.append({
            "tipo_error": "Cups Sin Contrato",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": item.get("problema", ""),
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": f"Entidad: {cod_ent}, {entidad}",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cups No CAPITA ---
    for item in error_groups.get("Cups No CAPITA", []):
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        problema = item.get("problema", "")
        rows.append({
            "tipo_error": "Cups No CAPITA",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": problema or item.get("observacion", ""),
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": "",
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Duplicado ID+Código ---
    for item in error_groups.get("Duplicado ID+Código", []):
        identificacion = item.get("identificacion", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        repeticiones = item.get("cantidad_repeticiones", 0)
        facturas_list = item.get("facturas", [])
        primer_factura = facturas_list[0] if facturas_list else ""
        problema = item.get("problema", "")

        detalle_parts = [f"ID: {identificacion}", f"Cód: {codigo}"]
        if facturas_list:
            detalle_parts.append(f"Facturas: {', '.join(facturas_list)}")

        descripcion = problema or f"Procedimiento duplicado x{repeticiones}"
        rows.append({
            "tipo_error": "Duplicado ID+Código",
            "factura": primer_factura,
            "fec_factura": _get_fec_factura(primer_factura),
            "responsable_cierra": _get_responsable(primer_factura),
            "descripcion": descripcion,
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": " | ".join(detalle_parts),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(primer_factura),
        })

    # Enrich rows with rule identifier (regla) from original detection items.
    # Some error_groups keys get remapped to a different tipo_error in the row
    # (e.g. "Duplicados Farmacia" → "⚠️ Revisión Necesaria"). Map them explicitly.
    _attach_regla_and_fallback(
        rows, error_groups, {"Duplicados Farmacia": "⚠️ Revisión Necesaria"}
    )

    return rows


# ---------------------------------------------------------------------------
# Backward-compatible wrapper for old callers that use named parameters
# ---------------------------------------------------------------------------


def build_urgencias_normalized_rows(
    problemas_centros: list[dict],
    problemas_ide_contrato: list[dict],
    problemas_cups_equivalentes: list[dict],
    mal_capitado: list[dict],
    cantidades_urgencias: list[dict],
    cantidades_soat_urgencias: list[dict],
    cantidades_hospitalizacion: list[dict],
    cantidades_soat_hospitalizacion: list[dict],
    responsables_map: dict[str, str],
    decimales: list[str] | None = None,
    tipo_identificacion_edad: list[dict] | None = None,
    profesionales: list[dict] | None = None,
    entidad_afiliacion_comparison: list[dict] | None = None,
    fecha_cierre_vacia_map: dict[str, bool] | None = None,
    tipo_usuario: list[dict] | None = None,
    revision_entidad_86: list[dict] | None = None,
    revision_cantidad: list[dict] | None = None,
    copago_entidad: list[dict] | None = None,
    duplicados_farmacia: list[dict] | None = None,
    fec_factura_map: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Backward-compatible wrapper. Converts old named params to error_groups dict."""
    error_groups: dict[str, list] = {
        "Centros de Costo": problemas_centros,
        "IDE Contrato": problemas_ide_contrato,
        "Cups Equivalentes": problemas_cups_equivalentes,
        "MAL CAPITADO": mal_capitado,
        "Cantidades": cantidades_urgencias,
        "Cantidades SOAT": cantidades_soat_urgencias,
        "Cantidades Hospitalización": cantidades_hospitalizacion,
        "Cantidades SOAT Hospitalización": cantidades_soat_hospitalizacion,
    }
    if decimales:
        error_groups["Decimales"] = decimales
    if tipo_identificacion_edad:
        error_groups["Tipo Identificación / Edad"] = tipo_identificacion_edad
    if profesionales:
        error_groups["Profesionales"] = profesionales
    if entidad_afiliacion_comparison:
        error_groups["Código Entidad vs Afiliación"] = entidad_afiliacion_comparison
    if tipo_usuario:
        error_groups["Tipo Usuario"] = tipo_usuario

    revision_items: list[dict] = []
    if revision_entidad_86:
        for item in revision_entidad_86:
            item["detalle"] = item.get("detalle", "86")
            item["descripcion"] = item.get("descripcion", "Cód Entidad Cobrar = 86 requiere revisión manual")
        revision_items.extend(revision_entidad_86)
    if revision_cantidad:
        for item in revision_cantidad:
            item["detalle"] = item.get("detalle", "")
            if "Cant:" not in str(item.get("detalle", "")):
                cantidad = item.get("cantidad", "")
                item["detalle"] = f"Cant: {cantidad}"
            item["descripcion"] = item.get("descripcion", "Cantidad > 1 con código no exento requiere revisión manual")
        revision_items.extend(revision_cantidad)
    if revision_items:
        error_groups["⚠️ Revisión Necesaria"] = revision_items

    if copago_entidad:
        error_groups["Copago vs Entidad"] = copago_entidad
    if duplicados_farmacia:
        error_groups["Duplicados Farmacia"] = duplicados_farmacia

    return build_normalized_rows(
        error_groups=error_groups,
        responsables_map=responsables_map,
        fec_factura_map=fec_factura_map,
        fecha_cierre_vacia_map=fecha_cierre_vacia_map,
    )
