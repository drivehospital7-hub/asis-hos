"""Canonical grupo_error labels for rule-declared /procesar grouping.

Single source of truth shared by migration 017 backfill, seed INSERTs,
the normalized_rows generic mapper + GRUPO_FORMATTERS registry, and the
admin-reglas UI datalist. Values are stable identifiers — do not rename
without a data migration.
"""

from __future__ import annotations

# --- Named-formatter groups (GRUPO_FORMATTERS keys) ---
GRUPO_TIPO_ID_EDAD = "Tipo Identificacion / Edad"
GRUPO_CODIGO_ENTIDAD = "Codigo-Entidad-vs-Afiliacion"
GRUPO_DUPLICADOS_FARMACIA = "Duplicados-Farmacia"
GRUPO_CUPS_EQUIVALENTES = "Cups-Equivalentes"
GRUPO_REVISION_NECESARIA = "Revision-Necesaria"

NAMED_FORMATTER_GROUPS = frozenset({
    GRUPO_TIPO_ID_EDAD,
    GRUPO_CODIGO_ENTIDAD,
    GRUPO_DUPLICADOS_FARMACIA,
    GRUPO_CUPS_EQUIVALENTES,
    GRUPO_REVISION_NECESARIA,
})

# --- Plain groups (generic mapper, no custom code) ---
GRUPO_CENTROS_COSTO = "Centros de Costo"
GRUPO_IDE_CONTRATO = "IDE Contrato"
GRUPO_PROFESIONALES = "Profesionales"
GRUPO_CANTIDADES = "Cantidades"
GRUPO_CANTIDADES_SOAT = "Cantidades SOAT"
GRUPO_CANTIDADES_HOSP = "Cantidades Hospitalización"
GRUPO_CANTIDADES_SOAT_HOSP = "Cantidades SOAT Hospitalización"
GRUPO_DECIMALES = "Decimales"
GRUPO_TIPO_USUARIO = "Tipo Usuario"
GRUPO_COPAGO_ENTIDAD = "Copago vs Entidad"
GRUPO_CUPS_SIN_CONTRATO = "Cups Sin Contrato"
GRUPO_MAL_CAPITADO = "MAL CAPITADO"
GRUPO_RUTA_DUPLICADA = "Ruta Duplicada"
GRUPO_DOBLE_TIPO = "Doble Tipo Procedimiento"
GRUPO_CODIGOS_HOSP = "Codigos Hospitalizacion"
GRUPO_CRONOGRAMA = "Cronograma Bacteriologas"
GRUPO_DUPLICADO_ID_CODIGO = "Duplicado ID-Codigo"

ALL_GRUPO_ERROR_LABELS = frozenset({
    GRUPO_TIPO_ID_EDAD,
    GRUPO_CODIGO_ENTIDAD,
    GRUPO_DUPLICADOS_FARMACIA,
    GRUPO_CUPS_EQUIVALENTES,
    GRUPO_REVISION_NECESARIA,
    GRUPO_CENTROS_COSTO,
    GRUPO_IDE_CONTRATO,
    GRUPO_PROFESIONALES,
    GRUPO_CANTIDADES,
    GRUPO_CANTIDADES_SOAT,
    GRUPO_CANTIDADES_HOSP,
    GRUPO_CANTIDADES_SOAT_HOSP,
    GRUPO_DECIMALES,
    GRUPO_TIPO_USUARIO,
    GRUPO_COPAGO_ENTIDAD,
    GRUPO_CUPS_SIN_CONTRATO,
    GRUPO_MAL_CAPITADO,
    GRUPO_RUTA_DUPLICADA,
    GRUPO_DOBLE_TIPO,
    GRUPO_CODIGOS_HOSP,
    GRUPO_CRONOGRAMA,
    GRUPO_DUPLICADO_ID_CODIGO,
})
