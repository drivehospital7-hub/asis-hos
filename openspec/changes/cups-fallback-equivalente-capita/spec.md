# Specification: Urgencias Cápita — CUPS Fallback Equivalente

**Change:** cups-fallback-equivalente-capita
**Domain:** urgencias-capita-equivalente-cups
**Type:** Full spec (no existing spec covers this behavior)

## Purpose

Validar códigos CUPS en facturas CAP (cápita) de urgencias, con fallback al código equivalente cuando el principal no está en el listado autorizado.

## Requirements

### Requirement: CUPS en listado → válido

Si el código CUPS principal de una factura CAP está en `URGENCIAS_CAPITA_CUPS_CODES`, la fila SHALL considerarse válida sin consultar el equivalente.

#### Scenario: CUPS principal en listado
- GIVEN una factura con prefijo "CAP" y código CUPS "890101" (presente en `URGENCIAS_CAPITA_CUPS_CODES`)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN no se agrega ningún error a la lista de resultados

### Requirement: CUPS no listado + equivalente válido → válido (NUEVO)

Si el código CUPS principal NO está en el listado, PERO la columna "Cód. Equivalente CUPS" existe, tiene valor, y tras aplicar `.strip().upper()` dicho valor SÍ está en `URGENCIAS_CAPITA_CUPS_CODES`, la fila SHALL considerarse válida.

#### Scenario: Equivalente válido salva el registro
- GIVEN una factura CAP con CUPS "999999" (NO en listado)
- AND la columna "Cód. Equivalente CUPS" contiene "890101" (SÍ en listado)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN no se agrega ningún error

#### Scenario: Normalización de espacios y mayúsculas
- GIVEN una factura CAP con CUPS "999999" (NO en listado)
- AND la columna "Cód. Equivalente CUPS" contiene " 890101 " (con espacios)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN el valor se normaliza a "890101" via `.strip().upper()` y se considera válido

### Requirement: CUPS no listado + sin equivalente → error

Si el código CUPS principal NO está en el listado, y la columna "Cód. Equivalente CUPS" está ausente, vacía, o el equivalente normalizado tampoco está en el listado, SHALL marcarse como error.

#### Scenario: Columna "Cód. Equivalente CUPS" no existe
- GIVEN una factura CAP con CUPS "999999" (NO en listado)
- AND el dict `indices` no contiene la key `"codigo_equiv"` (columna ausente)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN se agrega un error con el mensaje: `"Código 999999 no está en el listado CAPITA. Factura con prefijo CAP solo permite códigos del listado URGENCIAS CAPITA CUPS."`

#### Scenario: Equivalente vacío
- GIVEN una factura CAP con CUPS "999999" (NO en listado)
- AND la columna "Cód. Equivalente CUPS" existe pero está vacía (celda nula o string vacío)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN se agrega un error

#### Scenario: Equivalente no está en listado
- GIVEN una factura CAP con CUPS "999999" (NO en listado)
- AND la columna "Cód. Equivalente CUPS" contiene "111111" (tampoco en listado)
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN se agrega un error

### Requirement: Exclusiones existentes se preservan

La nueva lógica SHALL NOT alter las exclusiones existentes: filas con "Código Tipo Procedimiento" = "09" o "12" se ignoran; filas sin prefijo "CAP" se ignoran; filas con CUPS vacío se ignoran.

#### Scenario: Tipo Procedimiento 09 excluido
- GIVEN una factura CAP con código tipo procedimiento "09"
- WHEN `detect_capita_cups_invalidos` procesa la fila
- THEN la fila se salta sin evaluar CUPS ni equivalente

## Error Messages

| Condición | Mensaje exacto |
|-----------|---------------|
| CUPS no en listado (sin equivalente válido) | `"Código {codigo} no está en el listado CAPITA. Factura con prefijo CAP solo permite códigos del listado URGENCIAS CAPITA CUPS."` |

Sin cambios al mensaje existente. La nueva lógica solo evita que este mensaje se genere cuando el equivalente es válido.
