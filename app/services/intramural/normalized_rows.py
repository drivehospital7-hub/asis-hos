"""Normalización de errores de Intramural a filas de 6 columnas.

Solo incluye secciones transversales: decimales, tipo identificación/edad,
código entidad vs afiliación, tipo usuario.
"""

from __future__ import annotations

from typing import Any


def build_intramural_normalized_rows(
    responsables_map: dict[str, str],
    decimales: list[str] | None = None,
    tipo_identificacion_edad: list[dict] | None = None,
    tipo_usuario: list[dict] | None = None,
    entidad_afiliacion_comparison: list[dict] | None = None,
    problemas_ide_contrato: list[dict] | None = None,
    copago_entidad: list[dict] | None = None,
    cups_sin_contrato: list[dict] | None = None,
    fec_factura_map: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Normaliza errores de Intramural en filas de 6 columnas.

    Formato de salida: cada dict tiene:
        - tipo_error: str
        - factura: str
        - fec_factura: str
        - responsable_cierra: str
        - descripcion: str
        - procedimiento: str
        - detalle: str

    Args:
        responsables_map: Dict {factura: responsable}
        decimales: Lista de errores de decimales (opcional)
        tipo_identificacion_edad: Lista de errores de tipo ID/edad (opcional)
        tipo_usuario: Lista de errores de tipo usuario (opcional)
        entidad_afiliacion_comparison: Lista de errores de entidad vs afiliación (opcional)
        problemas_ide_contrato: Lista de errores de IDE Contrato (opcional)
        fec_factura_map: Dict {factura: fecha_factura} (opcional)

    Returns:
        Lista de dicts normalizados listos para renderizar
    """
    rows: list[dict[str, str]] = []
    _fec_factura_map = fec_factura_map or {}

    def _get_responsable(factura: str) -> str:
        return responsables_map.get(factura, "")

    def _get_fec_factura(factura: str) -> str:
        return _fec_factura_map.get(factura, "")

    # --- Decimales ---
    if decimales:
        for factura in decimales:
            rows.append({
                "tipo_error": "Decimales",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Valores con decimales",
                "procedimiento": "Vlr. Procedimiento",
                "detalle": "Vlr. Subsidiado",
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
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": f"Tipo actual {tipo_actual} debería ser {tipo_deberia}",
                "procedimiento": num_id,
                "detalle": f"{anios} años {meses} meses",
            })

    # --- Código Entidad vs Afiliación ---
    if entidad_afiliacion_comparison:
        for item in entidad_afiliacion_comparison:
            factura = item.get("factura", "")
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
                rows.append({
                    "tipo_error": "Código Entidad vs Afiliación",
                    "factura": factura,
                    "fec_factura": _get_fec_factura(factura),
                    "responsable_cierra": _get_responsable(factura),
                    "descripcion": desc,
                    "procedimiento": cod_actual,
                    "detalle": detalle,
                })
            else:
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

    # --- IDE Contrato ---
    if problemas_ide_contrato:
        for item in problemas_ide_contrato:
            factura = item.get("factura", "")
            codigo = item.get("codigo", "")
            proc = item.get("procedimiento", "")
            rows.append({
                "tipo_error": "IDE Contrato",
                "factura": factura,
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": f"IDE Contrato debería ser {item.get('ide_contrato_deberia', 'N/A')}",
                "procedimiento": f"{codigo} - {proc}" if codigo and proc else (codigo or proc or ""),
                "detalle": item.get("ide_contrato_actual", ""),
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
                "fec_factura": _get_fec_factura(factura),
                "responsable_cierra": _get_responsable(factura),
                "descripcion": "Vlr. Copago debe ser 0 cuando entidad no es default",
                "procedimiento": f"{codigo} - {proc}" if codigo and proc else (codigo or proc or ""),
                "detalle": f"Ent: {entidad}, Copago: {copago}",
            })

    # --- Cups Sin Contrato ---
    if cups_sin_contrato:
        for item in cups_sin_contrato:
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
                "procedimiento": f"{codigo} - {proc}" if codigo and proc else (codigo or proc or ""),
                "detalle": f"Entidad: {cod_ent}, {entidad}",
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
