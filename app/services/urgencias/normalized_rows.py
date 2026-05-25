"""Normalización de errores de Urgencias a filas de 6 columnas.

Extraído de app/services/revision_sheet.py._build_urgencias_normalized_rows
como parte de la Fase 7 (cleanup).
"""

from __future__ import annotations

from typing import Any


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
) -> list[dict[str, str]]:
    """
    Normaliza todos los tipos de error de Urgencias en filas de 6 columnas.

    Formato de salida: cada dict tiene:
        - tipo_error: str
        - factura: str
        - responsable_cierra: str
        - descripcion: str
        - procedimiento: str (Var1)
        - detalle: str (Var2)
        - fecha_cierre_vacia: bool

    Args:
        problemas_centros: Lista de errores de centros de costo
        problemas_ide_contrato: Lista de errores de IDE Contrato
        problemas_cups_equivalentes: Lista de errores de CUPS equivalentes
        mal_capitado: Lista de errores MAL CAPITADO
        cantidades_urgencias: Lista de errores de cantidades en Urgencias
        cantidades_soat_urgencias: Lista de errores de cantidades SOAT Urgencias
        cantidades_hospitalizacion: Lista de errores de cantidades en Hospitalización
        cantidades_soat_hospitalizacion: Lista de errores de cantidades SOAT Hospitalización
        responsables_map: Dict {factura: responsable}
        decimales: Lista de errores de decimales (opcional)
        tipo_identificacion_edad: Lista de errores de tipo identificación/edad (opcional)
        profesionales: Lista de errores de profesionales (opcional)
        entidad_afiliacion_comparison: Lista de errores de entidad vs afiliación (opcional)
        fecha_cierre_vacia_map: Dict {factura: True si Fecha Cierre está vacía} (opcional)
        revision_entidad_86: Lista de revisiones necesarias para entidad 86 (opcional)
        revision_cantidad: Lista de revisiones necesarias por cantidad > 1 (opcional)
        duplicados_farmacia: Lista de duplicados de farmacia (opcional)

    Returns:
        Lista de dicts normalizados listos para escribir en Excel o renderizar en HTML
    """
    rows: list[dict[str, str]] = []

    def _get_fecha_cierre_vacia(factura: str) -> bool:
        if fecha_cierre_vacia_map is None:
            return False
        return fecha_cierre_vacia_map.get(factura, False)

    def _get_responsable(factura: str) -> str:
        return responsables_map.get(factura, "")

    def _build_procedimiento(codigo: str, procedimiento: str) -> str:
        """Construye 'Código - Nombre' si ambos existen, sino el que esté presente."""
        codigo = str(codigo).strip() if codigo else ""
        procedimiento = str(procedimiento).strip() if procedimiento else ""
        if codigo and procedimiento:
            return f"{codigo} - {procedimiento}"
        return codigo or procedimiento or ""

    def _build_ide_contrato_descripcion(ide_deberia: str) -> str:
        """Construye descripción de IDE Contrato, omitiendo el prefix para errores de DB."""
        if ide_deberia in ("Código no en DB", "CÓDIGO NO EN DB"):
            return ide_deberia
        return f"IDE Contrato debería ser {ide_deberia}"

    # --- Centros de Costo ---
    for item in problemas_centros:
        factura = item.get("factura", str(item.get("invoice", "")))
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        rows.append({
            "tipo_error": "Centros de Costo",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Centro de costo debería ser {item.get('centro_deberia', 'N/A')}",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": item.get("centro_actual", ""),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- IDE Contrato ---
    for item in problemas_ide_contrato:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        rows.append({
            "tipo_error": "IDE Contrato",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": _build_ide_contrato_descripcion(item.get("ide_contrato_deberia", "N/A")),
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": item.get("ide_contrato_actual", ""),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cups Equivalentes ---
    for item in problemas_cups_equivalentes:
        factura = item.get("factura", "")
        codigo_raw = item.get("codigo", "")
        proc_raw = item.get("procedimiento", "")
        estancia_str = item.get("estancia_str", "")
        # codigo puede ser str o list, normalizar
        if isinstance(codigo_raw, list):
            codigo_str = ", ".join(str(c) for c in codigo_raw)
        else:
            codigo_str = str(codigo_raw)
        proc_str = str(proc_raw).strip() if proc_raw else ""
        proc_final = proc_str if proc_str else codigo_str
        if estancia_str:
            detalle = f"Estancia: {estancia_str}"
        else:
            detalle = codigo_str
        rows.append({
            "tipo_error": "Cups Equivalentes",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": item.get("accion", ""),
            "procedimiento": proc_final,
            "detalle": detalle,
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- MAL CAPITADO ---
    for item in mal_capitado:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        rows.append({
            "tipo_error": "MAL CAPITADO",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": item.get("observacion", ""),
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": item.get("ide_contrato_actual", ""),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cantidades (Urgencias) ---
    for item in cantidades_urgencias:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        cantidad = item.get("cantidad", "")
        rows.append({
            "tipo_error": "Cantidades",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Cantidad {cantidad} debe ser ≤ 1 en Urgencias",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": str(cantidad),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cantidades SOAT Urgencias ---
    for item in cantidades_soat_urgencias:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        cantidad = item.get("cantidad", "")
        rows.append({
            "tipo_error": "Cantidades SOAT",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Cantidad {cantidad} debe ser = 1 (SOAT Urgencias)",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": str(cantidad),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cantidades Hospitalización ---
    for item in cantidades_hospitalizacion:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        cantidad = item.get("cantidad", "")
        cantidad_esperada = item.get("cantidad_esperada", "")
        rows.append({
            "tipo_error": "Cantidades Hospitalización",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Cantidad {cantidad} debería ser {cantidad_esperada}",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": str(cantidad),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Cantidades SOAT Hospitalización ---
    for item in cantidades_soat_hospitalizacion:
        factura = item.get("factura", "")
        codigo = item.get("codigo", "")
        proc = item.get("procedimiento", "")
        cantidad = item.get("cantidad", "")
        cantidad_esperada = item.get("cantidad_esperada", "")
        rows.append({
            "tipo_error": "Cantidades SOAT Hospitalización",
            "factura": factura,
            "responsable_cierra": _get_responsable(factura),
            "descripcion": f"Cantidad {cantidad} debería ser {cantidad_esperada} (SOAT Hospitalización)",
            "procedimiento": _build_procedimiento(codigo, proc),
            "detalle": str(cantidad),
            "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
        })

    # --- Decimales ---
    if decimales:
        for factura in decimales:
            rows.append({
                "tipo_error": "Decimales",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Valores con decimales",
                "procedimiento": "Vlr. Procedimiento",
                "detalle": "Vlr. Subsidiado",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- Tipo Identificación / Edad ---
    if tipo_identificacion_edad:
        for item in tipo_identificacion_edad:
            factura = item.get("factura", "")
            num_id = item.get("numero_identificacion", "")
            anios = item.get("edad_anios", "")
            meses = item.get("edad_meses", "")
            tipo_actual = item.get("tipo_actual", "")
            tipo_deberia = item.get("tipo_deberia", "")
            rows.append({
                "tipo_error": "Tipo Identificación / Edad",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": f"Tipo actual {tipo_actual} debería ser {tipo_deberia}",
                "procedimiento": num_id,
                "detalle": f"{anios} años {meses} meses",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- Profesionales ---
    if profesionales:
        for item in profesionales:
            factura = item.get("factura", "")
            cod_prof = item.get("codigo_profesional", "")
            proc_nombre = item.get("procedimiento", "")
            nombre = item.get("nombre", "")
            rows.append({
                "tipo_error": "Profesionales",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": item.get("problema", item.get("regla", "")),
                "procedimiento": _build_procedimiento(cod_prof, proc_nombre),
                "detalle": f"Cód: {cod_prof}" if cod_prof else "",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
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
                "responsable_cierra": _get_responsable(factura),
                "descripcion": item.get("problema", ""),
                "procedimiento": proc_entidad,
                "detalle": f"Afiliación: {item.get('entidad_afiliacion', '')}",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
                "_header_override": "Entidad de factura",
            })

    # --- Tipo Usuario ---
    if tipo_usuario:
        for item in tipo_usuario:
            factura = item.get("factura", "")
            tipo_actual = item.get("tipo_actual", "")
            rows.append({
                "tipo_error": "Tipo Usuario",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Revisar tipo usuario en Targetero",
                "procedimiento": "",
                "detalle": tipo_actual,
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- ⚠️ Revisión Necesaria: Entidad 86 ---
    if revision_entidad_86:
        for item in revision_entidad_86:
            factura = item.get("factura", "")
            codigo = item.get("codigo", "")
            proc = item.get("procedimiento", "")
            rows.append({
                "tipo_error": "⚠️ Revisión Necesaria",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Cód Entidad Cobrar = 86 requiere revisión manual",
                "procedimiento": _build_procedimiento(codigo, proc),
                "detalle": "86",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    if revision_cantidad:
        for item in revision_cantidad:
            factura = item.get("factura", "")
            codigo = item.get("codigo", "")
            proc = item.get("procedimiento", "")
            cantidad = item.get("cantidad", "")
            rows.append({
                "tipo_error": "⚠️ Revisión Necesaria",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Cantidad > 1 con código no exento requiere revisión manual",
                "procedimiento": _build_procedimiento(codigo, proc),
                "detalle": f"Cant: {cantidad}",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- Copago vs Entidad ---
    if copago_entidad:
        for item in copago_entidad:
            factura = item.get("factura", "")
            codigo = item.get("codigo", "")
            proc = item.get("procedimiento", "")
            entidad = item.get("entidad_cobrar", "")
            copago = item.get("vlr_copago", "")
            rows.append({
                "tipo_error": "Copago vs Entidad",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Vlr. Copago debe ser 0 cuando entidad no es default",
                "procedimiento": _build_procedimiento(codigo, proc),
                "detalle": f"Ent: {entidad}, Copago: {copago}",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    # --- ⚠️ Revisión Necesaria: Duplicados Farmacia ---
    if duplicados_farmacia:
        for item in duplicados_farmacia:
            factura = item.get("factura", "")
            tipo_proc = item.get("codigo_tipo_procedimiento", "")
            total_pares = item.get("total_pares", 0)
            pares = item.get("pares_duplicados", [])
            detalle_pares = "; ".join(
                f"{p.get('codigo', '')} x{p.get('cantidad', '')} ({p.get('count', 0)} veces)"
                for p in pares
            )
            rows.append({
                "tipo_error": "⚠️ Revisión Necesaria",
                "factura": factura,
                "responsable_cierra": _get_responsable(factura),
                "descripcion": (
                    f"Duplicados Farmacia — Grupo {tipo_proc}: "
                    f"{total_pares} par(es) duplicado(s)"
                ),
                "procedimiento": f"Grupo {tipo_proc}",
                "detalle": detalle_pares or f"{total_pares} pares",
                "fecha_cierre_vacia": _get_fecha_cierre_vacia(factura),
            })

    return rows
