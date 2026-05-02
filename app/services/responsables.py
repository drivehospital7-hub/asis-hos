"""Servicio para obtener el responsable de una factura."""

from typing import Dict


def obtener_responsable(factura: str, mapping: Dict[str, str]) -> str:
    """
    Obtiene el responsable desde un mapping de factura -> responsable.
    
    Args:
        factura: Número de factura
        mapping: Dict {factura: responsable}
    
    Returns:
        Nombre del responsable o string vacío si no existe
    """
    if not factura or not mapping:
        return ""
    return mapping.get(factura, "")


def crear_mapping(facturas_y_responsables: list[tuple[str, str]]) -> Dict[str, str]:
    """
    Crea un mapping de factura -> responsable.
    
    Args:
        facturas_y_responsables: Lista de tuplas (factura, responsable)
    
    Returns:
        Dict {factura: responsable} sin duplicados
    """
    mapping: Dict[str, str] = {}
    for factura, responsable in facturas_y_responsables:
        if factura and responsable and factura not in mapping:
            mapping[factura] = responsable
    return mapping
