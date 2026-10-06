"""Mapa canonico de headers Excel por fuente de produccion.

Cada fuente declara {clave_interna: nombre exacto en Excel}.
El match sigue siendo EXACTO (ver
``app.services.transversales.column_indices.get_column_indices``):
hay columnas que conviven y solo se diferencian por tilde
(ej. "Codigo" vs "Código") y cualquier normalizacion automatica
(casefold, strip de diacriticos) las confundiria.

La unica tolerancia permitida son los alias explicitos de
``<FUENTE>_HEADER_ALIASES``: {clave_interna: (alias1, ...)}.
Cada uso de un alias se loguea como alerta: significa que el
productor movio algo y hay que revisar el canonico.

Para agregar una fuente complementaria (triages, autorizaciones):
declarar su mapa + sus alias y registrarlos en SOURCE_HEADERS /
SOURCE_HEADER_ALIASES. Ningun mapa vive en servicios.
"""

from __future__ import annotations

#: Fuente principal: produccion del facturador.
SOURCE_FACTURACION = "facturacion"

#: Mapa canonico facturacion: clave interna -> nombre exacto en Excel.
FACTURACION_HEADERS: dict[str, str] = {
    "numero_factura": "Número Factura",
    "vlr_subsidiado": "Vlr. Subsidiado",
    "vlr_procedimiento": "Vlr. Procedimiento",
    "codigo_tipo_procedimiento": "Código Tipo Procedimiento",
    "tipo_procedimiento": "Tipo Procedimiento",
    "codigo": "Código",
    "codigo_equiv": "Cód. Equivalente CUPS",
    "procedimiento": "Procedimiento",
    "identificacion": "Nº Identificación",
    "convenio_facturado": "Convenio Facturado",
    "cantidad": "Cantidad",
    "laboratorio": "Laboratorio",
    "vacuna": "Vacuna",
    "centro_costo": "Centro Costo",
    "codigo_entidad_cobrar": "Cód Entidad Cobrar",
    "entidad_cobrar": "Entidad Cobrar",
    "entidad_afiliacion": "Entidad Afiliación",
    "tipo_factura_descripcion": "Tipo Factura Descripción",
    "ide_contrato": "IDE Contrato",
    "tipo_identificacion": "Tipo Identificación",
    "fec_nacimiento": "Fec. Nacimiento",
    "fec_factura": "Fec. Factura",
    "fecha_cierre": "Fecha Cierre",
    "profesional_identificacion": "Identificación Profesional",
    "profesional_atiende": "Profesional Atiende",
    "codigo_profesional": "Código Profesional",
    "responsable_cierra": "Responsable Cierra Facturar",
    "tarifario": "Tarifario",
    "tipo_usuario": "Tipo Usuario",
    "vlr_copago": "Vlr. Copago",
    "numero_reingreso": "Nº Reingreso",
    "numero_autorizacion": "N° Autorizacion",
}

#: Alias explicitos facturacion: clave interna -> variantes aceptadas.
#: Vacio = el exacto manda. Agregar un alias solo cuando el productor
#: cambie un header y el canonico aun no se actualice.
FACTURACION_HEADER_ALIASES: dict[str, tuple[str, ...]] = {}

#: Registro por fuente: nombre fuente -> mapa canonico.
SOURCE_HEADERS: dict[str, dict[str, str]] = {
    SOURCE_FACTURACION: FACTURACION_HEADERS,
}

#: Registro por fuente: nombre fuente -> alias explicitos.
SOURCE_HEADER_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    SOURCE_FACTURACION: FACTURACION_HEADER_ALIASES,
}
