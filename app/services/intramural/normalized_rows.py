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
    fec_factura_map: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """
    Normaliza errores transversales de Intramural en filas de 6 columnas.

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
