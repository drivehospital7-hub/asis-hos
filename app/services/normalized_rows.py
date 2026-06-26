"""Normalización de errores a filas de 6 columnas (genérico por tipo_factura).

Reemplaza a urgencias/normalized_rows.py y odontologia/normalized_rows.py
con un builder parametrizado por error_groups: dict que mapea tipo_error -> lista de dicts.
"""

from __future__ import annotations

from typing import Any


def build_normalized_rows(
    error_groups: dict[str, list],
    responsables_map: dict[str, str],
    fec_factura_map: dict[str, str] | None = None,
    fecha_cierre_vacia_map: dict[str, bool] | None = None,
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
        codigo = str(codigo).strip() if codigo else ""
        procedimiento = str(procedimiento).strip() if procedimiento else ""
        if codigo and procedimiento:
            return f"{codigo} - {procedimiento}"
        return codigo or procedimiento or ""

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
            "detalle": item.get("ide_contrato_actual", ""),
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
    for factura in error_groups.get("Decimales", []):
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
        num_id = item.get("numero_identificacion", "")
        anios = item.get("edad_anios", "")
        meses = item.get("edad_meses", "")
        tipo_actual = item.get("tipo_actual", "")
        tipo_deberia = item.get("tipo_deberia", "")
        problema = item.get("problema", "")
        descripcion = problema or f"Tipo actual {tipo_actual} debería ser {tipo_deberia}"
        rows.append({
            "tipo_error": "Tipo Identificación / Edad",
            "factura": factura,
            "fec_factura": _get_fec_factura(factura),
            "responsable_cierra": _get_responsable(factura),
            "descripcion": descripcion,
            "procedimiento": num_id,
            "detalle": f"{anios} años {meses} meses",
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

    # Generic fallback: if procedimiento AND detalle are both empty,
    # find the original item by factura and use its first matching key.
    # This handles group-by rules (sparse dicts with only factura + problema).
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
                    for key in ("codigo", "vlr_subsidiado", "tipo_identificacion",
                                "cantidad", "centro_costo", "codigo_entidad_cobrar",
                                "observacion", "accion", "identificacion"):
                        val = item.get(key, "")
                        if val:
                            row["procedimiento"] = str(val)
                            break

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
