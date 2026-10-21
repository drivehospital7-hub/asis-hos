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

#: Fuente FURIPS (reclamaciones SOAT, headers numerados fila 3).
SOURCE_FURIPS = "furips"

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

#: Mapa canonico FURIPS (102 headers numerados, fila 3).
FURIPS_HEADERS: dict[str, str] = {
    "c01_numero_de_radicado_anterior": "1-Número de radicado anterior",
    "c02_rgo_respuesta_a_glosa_u_objecion": "2-RGO Respuesta a Glosa u objeción",
    "c03_numero_de_factura": "3-Número de factura",
    "c04_numero_consecutivo_de_la_reclamacion": "4-Número consecutivo de la reclamación",
    "c05_codigo_de_habilitacion_del_prestador_de_servicios_de_salud": "5-Código de habilitación del prestador de servicios de salud.",
    "c06_primer_apellido_de_la_victima": "6-Primer apellido de la víctima",
    "c07_segundo_apellido_de_la_victima": "7-Segundo apellido de la víctima",
    "c08_primer_nombre_de_la_victima": "8-Primer nombre de la víctima",
    "c09_segundo_nombre_de_la_victima": "9-Segundo nombre de la víctima",
    "c10_tipo_de_documento_de_identidad_de_la_victima": "10-Tipo de documento de identidad de la víctima",
    "c11_numero_de_documento_de_identidad_de_la_victima": "11-Número de documento de identidad de la víctima",
    "c12_fecha_de_nacimiento_de_la_victima": "12-Fecha de nacimiento de la víctima",
    "c13_fecha_de_fallecimiento": "13-Fecha de fallecimiento",
    "c14_sexo_de_la_victima": "14-Sexo de la víctima",
    "c15_direccion_de_residencia_de_la_victima": "15-Dirección de residencia de la víctima",
    "c16_codigo_del_departamento_de_residencia_de_la_victima": "16-Código del departamento de residencia de la víctima",
    "c17_codigo_del_municipio_de_residencia_de_la_victima": "17-Código del municipio de residencia de la víctima",
    "c18_telefono_de_la_victima": "18-Teléfono de la víctima",
    "c19_condicion_de_la_victima": "19-Condición de la víctima",
    "c20_naturaleza_del_evento": "20-Naturaleza del evento",
    "c21_descripcion_del_otro_evento": "21-Descripción del otro evento",
    "c22_direccion_de_ocurrencia_del_evento": "22-Dirección de ocurrencia del evento",
    "c23_fecha_de_ocurrencia_del_evento": "23-Fecha de ocurrencia del evento",
    "c24_hora_de_ocurrencia_del_evento": "24-Hora de ocurrencia del evento",
    "c25_codigo_del_departamento_de_ocurrencia_del_evento": "25-Código del departamento de ocurrencia del evento",
    "c26_codigo_del_municipio_de_ocurrencia_del_evento": "26-Código del municipio de ocurrencia del evento",
    "c27_zona_de_ocurrencia_del_evento": "27-Zona de ocurrencia del evento",
    "c28_estado_de_aseguramiento": "28-Estado de aseguramiento",
    "c29_marca": "29-Marca",
    "c30_placa": "30-Placa",
    "c31_tipo_de_vehiculo": "31-Tipo de vehículo",
    "c32_codigo_de_la_aseguradora": "32-Código de la aseguradora",
    "c33_numero_de_poliza_soat": "33-Número de póliza SOAT",
    "c34_fecha_de_inicio_de_vigencia_de_la_poliza": "34-Fecha de inicio de vigencia de la póliza",
    "c35_fecha_final_de_vigencia_de_la_poliza": "35-Fecha final de vigencia de la póliza",
    "c36_numero_de_radicado_siras_ide_atencion": "36-Número de radicado SIRAS (ide_atencion)",
    "c37_cobro_por_agotamiento_tope_aseguradora": "37-Cobro por agotamiento tope Aseguradora",
    "c38_codigo_cups_de_servicio_principal_de_hospitalizacion": "38-Código CUPS de servicio principal de hospitalización",
    "c39_complejidad_del_procedimiento_quirurgico": "39-Complejidad del procedimiento quirúrgico",
    "c40_codigo_cups_del_procedimiento_quirurgico_principal": "40-Código CUPS del procedimiento quirúrgico principal",
    "c41_codigo_cups_del_procedimiento_quirurgico_secundario": "41-Código CUPS del procedimiento quirúrgico secundario",
    "c42_se_presto_servicio_uci": "42-Se presto servicio UCI",
    "c43_dias_de_uci_reclamados": "43-Días de UCI reclamados",
    "c44_tipo_de_documento_de_identidad_del_propietario": "44-Tipo de documento de identidad del propietario",
    "c45_numero_de_documento_de_identidad_del_propietario": "45-Número de documento de identidad del propietario",
    "c46_primer_apellido_del_propietario_o_razon_social_en_caso_de_empresa": "46-Primer apellido del propietario o razón social en caso de empresa.",
    "c47_segundo_apellido_del_propietario": "47-Segundo apellido del propietario",
    "c48_primer_nombre_del_propietario": "48-Primer nombre del propietario",
    "c49_segundo_nombre_del_propietario": "49-Segundo nombre del propietario",
    "c50_direccion_de_residencia_del_propietario": "50-Dirección de residencia del propietario",
    "c51_telefono_de_residencia_del_propietario": "51-Teléfono de residencia del propietario",
    "c52_codigo_del_departamento_de_residencia_del_propietario": "52-Código del departamento de residencia del propietario",
    "c53_codigo_del_municipio_de_residencia_del_propietario": "53-Código del municipio de residencia del propietario",
    "c54_primer_apellido_del_conductor": "54-Primer apellido del conductor",
    "c55_segundo_apellido_del_conductor": "55-Segundo apellido del conductor",
    "c56_primer_nombre_del_conductor": "56-Primer nombre del conductor",
    "c57_segundo_nombre_del_conductor": "57-Segundo nombre del conductor",
    "c58_tipo_de_documento_de_identidad_del_conductor": "58-Tipo de documento de identidad del conductor",
    "c59_numero_de_documento_de_identidad_del_conductor": "59-Número de documento de identidad del conductor",
    "c60_direccion_de_residencia_del_conductor": "60-Dirección de residencia del conductor",
    "c61_codigo_del_departamento_de_residencia_del_conductor": "61-Código del departamento de residencia del conductor",
    "c62_codigo_del_municipio_de_residencia_del_conductor": "62-Código del municipio de residencia del conductor",
    "c63_telefono_de_residencia_del_conductor": "63-Teléfono de residencia del conductor",
    "c64_tipo_de_referencia": "64-Tipo de referencia",
    "c65_fecha_de_remision": "65-Fecha de remisión",
    "c66_hora_de_salida": "66-Hora de salida",
    "c67_codigo_de_habilitacion_del_prestador_de_servicios_de_salud_remitente": "67-Código de habilitación del prestador de servicios de salud remitente",
    "c68_profesional_que_remite": "68-Profesional que remite",
    "c69_cargo_de_la_persona_que_remite": "69-Cargo de la persona que remite",
    "c70_fecha_de_aceptacion": "70-Fecha de aceptación",
    "c71_hora_de_aceptacion": "71-Hora de aceptación",
    "c72_codigo_de_habilitacion_del_prestador_de_servicios_de_salud_que_recibe": "72-Código de habilitación del prestador de servicios de salud que recibe",
    "c73_profesional_que_recibe": "73-Profesional que recibe",
    "c74_placa_ambulancia_que_realiza_el_traslado_interinstitucional": "74-Placa ambulancia que realiza el traslado interinstitucional",
    "c75_placa_ambulancia_traslado_primario": "75-Placa ambulancia traslado primario",
    "c76_transporte_de_la_victima_desde_el_sitio_del_evento": "76-Transporte de la víctima desde el sitio del evento",
    "c77_transporte_de_la_victima_hasta_el_fin_del_recorrido": "77-Transporte de la víctima hasta el fin del recorrido",
    "c78_tipo_de_servicio_del_transporte": "78-Tipo de servicio del transporte",
    "c79_zona_donde_recoge_victima": "79-Zona donde recoge víctima",
    "c80_fecha_de_ingreso": "80-Fecha de ingreso",
    "c81_hora_de_ingreso": "81-Hora de ingreso",
    "c82_fecha_de_egreso": "82-Fecha de egreso",
    "c83_hora_de_egreso": "83-Hora de egreso",
    "c84_codigo_de_diagnostico_principal_de_ingreso": "84-Código de diagnóstico principal de ingreso",
    "c85_codigo_de_diagnostico_de_ingreso_asociado_1": "85-Código de diagnóstico de ingreso asociado 1",
    "c86_codigo_de_diagnostico_de_ingreso_asociado_2": "86-Código de diagnóstico de ingreso asociado 2",
    "c87_codigo_diagnostico_principal_de_egreso": "87-Código diagnóstico principal de egreso",
    "c88_codigo_de_diagnostico_de_egreso_asociado_1": "88-Código de diagnóstico de egreso asociado 1",
    "c89_codigo_de_diagnostico_de_egreso_asociado_2": "89-Código de diagnóstico de egreso asociado 2",
    "c90_primer_apellido_del_medico_o_profesional_de_la_salud": "90-Primer apellido del médico o profesional de la salud",
    "c91_segundo_apellido_del_medico_o_profesional_de_la_salud": "91-Segundo apellido del médico o profesional de la salud",
    "c92_primer_nombre_del_medico_o_profesional_de_la_salud": "92-Primer nombre del médico o profesional de la salud",
    "c93_segundo_nombre_del_medico_o_profesional_de_la_salud": "93-Segundo nombre del médico o profesional de la salud",
    "c94_tipo_de_documento_de_identidad_del_medico_o_profesional_de_la_salud": "94-Tipo de documento de identidad del médico o profesional de la salud",
    "c95_numero_de_documento_de_identidad_del_medico_o_profesional_de_la_salud": "95-Número de documento de identidad del médico o profesional de la salud",
    "c96_numero_de_registro_del_medico": "96-Número de registro del médico",
    "c97_total_facturado_por_amparo_de_gastos_medicos_quirurgicos": "97-Total, facturado por amparo de gastos médicos quirúrgicos",
    "c98_total_reclamado_por_amparo_de_gastos_medicos_quirurgicos": "98-Total, reclamado por amparo de gastos médicos quirúrgicos",
    "c99_total_facturado_por_amparo_de_gastos_de_transporte_y_movilizacion_de_la_victima": "99-Total, facturado por amparo de gastos de transporte y movilización de la víctima",
    "c100_total_reclamado_por_amparo_de_gastos_de_transporte_y_movilizacion_de_la_victima": "100-Total, reclamado por amparo de gastos de transporte y movilización de la víctima",
    "c101_manifestacion_de_servicios_habilitados": "101-Manifestación de servicios habilitados",
    "c102_descripcion_del_evento": "102-Descripción del evento",
}

#: Registro por fuente: nombre fuente -> mapa canonico.
SOURCE_HEADERS: dict[str, dict[str, str]] = {
    SOURCE_FACTURACION: FACTURACION_HEADERS,
    SOURCE_FURIPS: FURIPS_HEADERS,
}

#: Fila (1-based) donde cada fuente trae sus headers. El exporter
#: auto-detecta por best-match; si detecta otra fila, lo advierte.
SOURCE_HEADER_ROWS: dict[str, int] = {
    SOURCE_FACTURACION: 1,
    # FURIPS se ve en fila 3 del Excel, pero el lector Polars/calamine
    # no materializa la fila 2 vacia: ahi los headers llegan en fila 2.
    SOURCE_FURIPS: 2,
}

#: Alias explicitos FURIPS (vacio: el exacto numerado manda).
FURIPS_HEADER_ALIASES: dict[str, tuple[str, ...]] = {}

#: Clave de identidad factura dentro de FURIPS (pega con numero_factura
#: del principal y con la factura que el motor extrae por defecto).
FURIPS_FACTURA_KEY = "c03_numero_de_factura"

#: Fuente -> clave interna que identifica la factura en esa fuente.
#: El exporter la expone tambien como `numero_factura` para que el motor
#: (extraccion de factura, group_by por defecto) funcione sin cambios.
SOURCE_FACTURA_KEYS: dict[str, str] = {
    SOURCE_FACTURACION: "numero_factura",
    SOURCE_FURIPS: FURIPS_FACTURA_KEY,
}


def required_headers_for(source: str) -> dict[str, str]:
    """Mapa efectivo {clave: header exacto} para una fuente.

    Incluye el alias `numero_factura` apuntando a la columna identidad
    de la fuente (misma columna, dos claves). Patron a reusar por cada
    fuente nueva: mapa + fila + factura_key, todo en este modulo.
    """
    canonico = dict(SOURCE_HEADERS[source])
    factura_key = SOURCE_FACTURA_KEYS[source]
    canonico.setdefault("numero_factura", canonico[factura_key])
    return canonico

#: Registro por fuente: nombre fuente -> alias explicitos.
SOURCE_HEADER_ALIASES: dict[str, dict[str, tuple[str, ...]]] = {
    SOURCE_FACTURACION: FACTURACION_HEADER_ALIASES,
    SOURCE_FURIPS: FURIPS_HEADER_ALIASES,
}

#: Etiqueta humana por fuente (para el selector de campos en admin-reglas).
SOURCE_LABELS: dict[str, str] = {
    SOURCE_FACTURACION: "Facturación",
    SOURCE_FURIPS: "FURIPS",
}


def describe_fuentes() -> list[dict[str, object]]:
    """Contrato fuente -> campos para el builder de reglas (admin-reglas).

    Una sola fuente de verdad: lo que se agrega a SOURCE_HEADERS aparece
    en el selector sin tocar el frontend. `clave` es la parte tras
    `invoice.`; `header` es el texto exacto del Excel (para diferenciar
    en la UI, ej. `FURIPS · 3-Número de factura`).
    """
    return [
        {
            "fuente": fuente,
            "label": SOURCE_LABELS.get(fuente, fuente),
            "campos": [
                {"clave": clave, "header": header}
                for clave, header in SOURCE_HEADERS[fuente].items()
            ],
        }
        for fuente in SOURCE_HEADERS
    ]
