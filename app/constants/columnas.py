"""Constantes de columnas Excel, headers y centros de costo."""

from __future__ import annotations

# =============================================================================
# COLUMNS - Columnas a mostrar (las demás se ocultan)
# =============================================================================

# Columnas para ODONTOLOGÍA
COLUMNS_TO_KEEP = frozenset({
    "Entidad Cobrar",
    "Profesional Atiende",
    "Fec. Factura",
    "Número Factura",
    "Tipo Entidad Cobrar",
    "Convenio Facturado",
    "Procedimiento",
    "Tipo Identificación",
    "Edad Completa",
    "Nº Identificación",
    "Primer Apellido",
    "Responsable Cierra Facturar",
    "Vlr. Procedimiento",
    "Vlr. Subsidiado",
    "Cantidad",
    "Segundo Apellido",
    "Primer Nombre",
    "Segundo Nombre",
    "Sexo",
    "Fec. Nacimiento",
    "Cita",
    "Tipo Cita",
    "Centro Costo",
})

# Columnas para URGENCIAS (incluye las necesarias para reglas)
URGENCIA_COLUMNS_TO_KEEP = frozenset({
    "Entidad Cobrar",
    "Profesional Atiende",
    "Fec. Factura",
    "Número Factura",
    "Tipo Entidad Cobrar",
    "Convenio Facturado",
    "Procedimiento",
    "Tipo Identificación",
    "Edad Completa",
    "Nº Identificación",
    "Primer Apellido",
    "Responsable Cierra Facturar",
    "Vlr. Procedimiento",
    "Vlr. Subsidiado",
    "Cantidad",
    "Segundo Apellido",
    "Primer Nombre",
    "Segundo Nombre",
    "Sexo",
    "Fec. Nacimiento",
    "Cita",
    "Tipo Cita",
    "Centro Costo",
    "Código Tipo Procedimiento",
    "Laboratorio",
    "Vlr. Copago",
})

# =============================================================================
# CENTROS DE COSTO
# =============================================================================

CENTRO_COSTO_ODONTOLOGIA = "ODONTOLOGIA"
CENTRO_COSTO_EXTRAMURAL = "SERVICIOS ODONTOLOGIA -EXTRAMURALES"


# =============================================================================
# HEADERS - Headers de hojas especiales
# =============================================================================

# Headers para hoja Revision ODONTOLOGIA (formato normalizado - 6 columnas fijas)
REVISION_HEADERS: dict[int, str] = {
    1: "Tipo de error",
    2: "Número Factura",
    3: "Responsable Cierra",
    4: "Descripción",
    5: "Procedimiento",
    6: "Detalle",
}

# Headers para hoja Revision URGENCIAS (formato normalizado - 6 columnas fijas)
URGENCIA_REVISION_HEADERS: dict[int, str] = {
    1: "Tipo de error",
    2: "Número Factura",
    3: "Responsable Cierra",
    4: "Descripción",
    5: "Procedimiento",
    6: "Detalle",
}


