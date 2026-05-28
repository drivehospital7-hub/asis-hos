"""Normalización de errores de Odontología/Equipos Básicos a filas de 6 columnas.

Extraído de app/services/revision_sheet.py._build_odontologia_normalized_rows
como parte de la Fase 7 (cleanup).
"""

from __future__ import annotations

from typing import Any


def build_odontologia_normalized_rows(
    decimales: list[dict] | list[str],
    doble_tipo: list[dict],
    ruta_dup: list[dict],
    profesionales: list[dict],
    cantidades: list[dict],
    tipo_id_edad: list[dict],
    tipo_id_entidad: list[dict] | None = None,
    centro_costo: list[dict],
    ide_contrato: list[dict],
    responsable_cierra: dict[str, str],
    entidad_afiliacion_comparison: list[dict] | None = None,
    tipo_usuario: list[dict] | None = None,
    fec_factura_map: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Normaliza todos los tipos de error de Odontología/Equipos Básicos en filas de 6 columnas.

    Args:
        decimales: Lista de dicts con "factura", "valores" o lista de strings (solo facturas)
        doble_tipo: Lista de dicts con "factura", "tipos"
        ruta_dup: Lista de dicts con "identificacion", "facturas", "cantidad"
        profesionales: Lista de dicts con "factura", "codigo_profesional", "procedimiento", ...
        cantidades: Lista de dicts con "factura", "tipo_procedimiento", "cantidad", ...
        tipo_id_edad: Lista de dicts con "factura", "tipo_actual", "tipo_deberia", "edad"
        centro_costo: Lista de dicts con "factura", "centro_actual", "centro_deberia", ...
        ide_contrato: Lista de dicts con "factura", "codigo", "cod_entidad", "ide_actual", ...
        responsable_cierra: Dict {factura: responsable}
        fec_factura_map: Dict {factura: fec_factura} (opcional)

    Returns:
        Lista de dicts normalizados con tipo_error, factura, responsable_cierra,
        descripcion, procedimiento (Var1), detalle (Var2), fec_factura
    """
    rows: list[dict[str, str]] = []
    _fec_factura_map = fec_factura_map or {}

    def _get_responsable(factura: str) -> str:
        return responsable_cierra.get(factura, "")

    def _get_fec_factura(factura: str) -> str:
        return _fec_factura_map.get(factura, "")

    def _build_procedimiento(codigo: str, procedimiento: str) -> str:
        codigo = str(codigo).strip() if codigo else ""
        procedimiento = str(procedimiento).strip() if procedimiento else ""
        if codigo and procedimiento:
            return f"{codigo} - {procedimiento}"
        return codigo or procedimiento or ""

    # --- Decimales ---
    for item in decimales:
        if isinstance(item, dict):
            factura = item.get("factura", "")
            valores = item.get("valores", "")
        else:
            factura = str(item) if item else ""
            valores = ""
        rows.append({
            "tipo_error": "Decimales",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Valores con decimales: {valores}" if valores else "Valores con decimales",
            "procedimiento": valores,
            "detalle": "",
        })

    # --- Doble tipo procedimiento ---
    for item in doble_tipo:
        factura = item.get("factura", "")
        tipos = item.get("tipos", "")
        rows.append({
            "tipo_error": "Doble tipo procedimiento",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": "Múltiples tipos de procedimiento",
            "procedimiento": "",
            "detalle": tipos,
        })

    # --- Ruta Duplicada ---
    for item in ruta_dup:
        identificacion = item.get("identificacion", "")
        facturas_list = item.get("facturas", "")
        cantidad = item.get("cantidad", 0)
        rows.append({
            "tipo_error": "Ruta Duplicada",
            "factura": identificacion,
            "fec_factura": _get_fec_factura(identificacion),
            "responsable_cierra": _get_responsable(identificacion),
            "descripcion": f"Paciente con {cantidad} facturas en PyP",
            "procedimiento": facturas_list,
            "detalle": identificacion,
        })

    # --- Profesionales (reemplaza Convenio de procedimiento) ---
    for item in profesionales:
        factura = item.get("factura", "")
        cod_prof = item.get("codigo_profesional", "")
        proc_nombre = item.get("procedimiento", "")
        problema = item.get("problema", "")
        regla = item.get("regla", "")
        rows.append({
            "tipo_error": "Convenio de procedimiento",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": problema or regla,
            "procedimiento": _build_procedimiento(cod_prof, proc_nombre),
            "detalle": problema or "",
        })

    # --- Cantidades ---
    for item in cantidades:
        factura = item.get("factura", "")
        tipo_proc = item.get("tipo_procedimiento", "")
        cantidad_val = item.get("cantidad", "")
        problema = item.get("problema", "")
        rows.append({
            "tipo_error": "Cantidades",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": problema or f"Cantidad anómala: {cantidad_val}",
            "procedimiento": tipo_proc,
            "detalle": str(cantidad_val),
        })

    # --- Tipo Identificación vs Edad ---
    for item in tipo_id_edad:
        factura = item.get("factura", "")
        tipo_actual = item.get("tipo_actual", "")
        tipo_deberia = item.get("tipo_deberia", "")
        edad = item.get("edad", "")
        rows.append({
            "tipo_error": "Tipo Identificación",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"{tipo_actual} debería ser {tipo_deberia}",
            "procedimiento": f"Edad: {edad} años",
            "detalle": "",
        })

    # --- Tipo Identificación vs Cód Entidad Cobrar ---
    if tipo_id_entidad:
        for item in tipo_id_entidad:
            factura = item.get("factura", "")
            tipo_id = item.get("tipo_identificacion", "")
            cod_actual = item.get("cod_entidad_actual", "")
            cod_esperado = item.get("cod_entidad_esperado", "")
            problema = item.get("problema", "")
            if problema == "86000_solo_para_as_ms":
                desc = f"Cód Entidad Cobrar = {cod_esperado} solo válido para AS/MS (actual: {tipo_id})"
            else:
                desc = f"{tipo_id} debe tener Cód Entidad Cobrar = {cod_esperado} (actual: {cod_actual})"
            rows.append({
                "tipo_error": "Tipo Identificación / Entidad",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": desc,
                "procedimiento": "",
                "detalle": f"Cód actual: {cod_actual}",
            })

    # --- Centro Costo ---
    for item in centro_costo:
        factura = item.get("factura", "")
        centro_actual = item.get("centro_actual", "")
        centro_deberia = item.get("centro_deberia", "")
        rows.append({
            "tipo_error": "Centro Costo",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Centro de costo debería ser {centro_deberia}",
            "procedimiento": "",
            "detalle": centro_actual,
        })

    # --- IDE Contrato ---
    for item in ide_contrato:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        ide_actual = item.get("ide_actual", "")
        ide_deberia = item.get("ide_deberia", "")
        nota = item.get("nota", "")
        rows.append({
            "tipo_error": "IDE Contrato",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"IDE Contrato debería ser {ide_deberia} ({nota})" if nota else f"IDE Contrato debería ser {ide_deberia}",
            "procedimiento": _build_procedimiento(codigo, ""),
            "detalle": ide_actual,
        })

    # --- Código Entidad vs Afiliación ---
    if entidad_afiliacion_comparison:
        for item in entidad_afiliacion_comparison:
            factura = item.get("factura", "")
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
            })

    # --- Tipo Usuario ---
    if tipo_usuario:
        for item in tipo_usuario:
            factura = item.get("factura", "")
            tipo_actual = item.get("tipo_actual", "")
            rows.append({
                "tipo_error": "Tipo Usuario",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Revisar tipo usuario en Targetero",
                "procedimiento": "",
                "detalle": tipo_actual,
            })

    return rows
