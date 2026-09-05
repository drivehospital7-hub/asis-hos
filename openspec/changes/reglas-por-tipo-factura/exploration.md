# Exploration: reglas-por-tipo-factura — Reorganización de Reglas por "Tipo Factura Descripción"

## Current State

El sistema actual agrupa detectores por área de ruta HTTP (`urgencias`, `odontologia`, `equipos_basicos`) en lugar de por el valor real de la columna `"Tipo Factura Descripción"` del Excel. La columna ya se lee en `exporter.py` (índice `tipo_factura_descripcion`) y varios detectores internos ya la usan para filtrar filas, pero el orquestador `detect_all_problems_urgencias` ejecuta TODOS los detectores contra TODAS las filas del Excel, sin diferenciar por tipo de factura.

## Affected Areas

- **`app/services/urgencias/detect_all.py`** — Orquestador central: 16 detectores + transversales llamados sin filtro por tipo_factura
- **`app/services/urgencias/*.py`** — 13 detectores específicos de urgencias, algunos ya filtran internamente, otros no
- **`app/services/exporter.py`** — Punto de entrada que despacha por área (`AREA_URGENCIAS` / `AREA_ODONTOLOGIA` / `AREA_EQUIPOS_BASICOS`)
- **`app/services/transversales/*.py`** — 7 detectores transversales (correctamente aplican a todos los tipos)
- **`app/services/odontologia/mal_capitado.py`** — Referenciado desde el orquestador de urgencias (mal ubicado)
- **`app/routes/urgencias.py`** — Ruta POST que usa `AREA_URGENCIAS` para todo
- **`app/constants/urgencias.py`** — ~794 líneas de constantes que mezclan reglas de Urgencias, Hospitalización, Intramural, Ambulatoria

## Mapeo de Detectores

### Detectores en `urgencias/` que YA filtran por tipo_factura_descripcion:

| Detector | Tipo Factura | Estado |
|---|---|---|
| `cantidades_urgencias.py` | Urgencias | ✅ Filtra: `if tipo_factura_str != "Urgencias": continue` |
| `cantidades_soat_urgencias.py` | Urgencias + SOAT | ✅ Filtra |
| `hospitalizacion.py:detect_cantidades_hospitalizacion` | Hospitalización | ✅ Filtra: `if tipo_factura_str != "Hospitalización": continue` |
| `hospitalizacion.py:detect_hospitalizacion_codes` | Hospitalización | ✅ Filtra |
| `cantidades_soat_hospitalizacion.py` | Hospitalización + SOAT | ✅ Filtra |
| `sala_observacion.py` | Urgencias | ✅ Filtra: `if tipo_factura_str != "Urgencias": continue` |
| `cups_equivalentes.py` | Hospitalización (2 reglas) | ⚠️ Parcial: solo 2 de 5 reglas usan tipo_factura |
| `centro_costo_urgencias.py` | Urgencias/Hospitalización/Intramural/Ambulatoria | ⚠️ Usa tipo_factura en reglas condicionales específicas |

### Detectores en `urgencias/` que NO filtran por tipo_factura_descripcion:

| Detector | ¿Debe filtrar? | Tipo(s) al que aplica |
|---|---|---|
| `profesionales_urgencias.py` | ✅ Sí | Urgencias (profesionales específicos de urgencias) |
| `ide_contrato_urgencias.py` | ✅ Sí | Urgencias (IDE contrato específico de Urgencias) |
| `ide_contrato_reverse.py` | ✅ Sí | Urgencias (REVERSE sin entidad) |
| `codigos_sin_db.py` | ⚠️ Parcial | IDE=969, aplica a Urgencias |
| `detect_copago_entidad.py` | ❌ Parece transversal | Podría aplicar a todos los tipos |
| `revision_cantidad.py` | ⚠️ Parcial | Varios tipos |
| `revision_entidad_86.py` | ⚠️ Parcial | Varios tipos |
| `duplicados_farmacia.py` | ⚠️ Parcial | Tarifario farmacia, sin filtro de tipo |

### Transversales (aplican a TODOS los tipos — correcto):

| Detector | Es transversal |
|---|---|
| `decimales.py` | ✅ Sí |
| `tipo_documento_edad.py` | ✅ Sí |
| `codigo_entidad.py` | ✅ Sí |
| `tipo_usuario.py` | ✅ Sí |
| `ruta_duplicada.py` | ✅ Sí (parametrizado) |
| `cantidades_anomalas.py` | ✅ Sí (parametrizado) |
| `doble_tipo_procedimiento.py` | ✅ Sí |

### Code Smells detectados:

1. **`odontologia/mal_capitado.py`** es importado y usado desde `urgencias/detect_all.py` — está en el package equivocado
2. **`detect_copago_entidad.py`** está en `urgencias/` pero no filtra por tipo_factura — parece una regla transversal
3. **`centro_costo_urgencias.py` (448 líneas)** es el archivo más grande — mezcla reglas de Urgencias, Hospitalización, Intramural y Ambulatoria en un solo archivo

## Data Pipeline

```
Excel Upload → Route (POST /urgencias)
  → exporter.detect_problems_only(area="urgencias")
    → Polars read_excel → _SimpleSheet (sin overhead openpyxl)
    → get_column_indices(headers, required_headers) [27 columnas, incluye tipo_factura_descripcion]
    → detect_all_problems_urgencias(sheet, indices)
      → 16 detectores llamados secuencialmente (SIN filtro por tipo_factura a nivel orquestador)
      → build_urgencias_normalized_rows(...) → 6 columnas unificadas
      → resultado {area, problemas, totales, missing_columns}
    → enrich con responsable_cierra
  → JSON response al frontend React
```

## "Tipo Factura Descripción" en el sistema

- **Columna Excel**: `"Tipo Factura Descripción"` (nombre exacto)
- **Nombre interno**: `tipo_factura_descripcion`
- **Se lee en**: `exporter.py` línea 233 dentro de `required_headers`
- **Valores conocidos**: `Urgencias`, `Hospitalización`, `Intramural`, `Extramural`, `Odontología`, `Ambulatoria`, `Farmacia`
- **Uso actual**: Varios detectores acceden a `indices.get("tipo_factura_descripcion")` para filtrar internamente, pero NO hay filtro a nivel de orquestador

## Proposed Reorganization (First Step)

### Arquitectura objetivo:

```
app/services/
├── transversales/           # Sin cambios — reglas transversales
├── odontologia/             # Sin cambios
├── equipos_basicos/         # Sin cambios
├── urgencias/               # REDUCIDO: solo detectores de Urgencias puras
│   ├── detect_all.py
│   ├── cantidades_urgencias.py
│   ├── cantidades_soat_urgencias.py
│   ├── sala_observacion.py
│   ├── profesionales_urgencias.py      # + filtro por tipo
│   └── cups_equivalentes.py           # solo reglas Urgencias
├── hospitalizacion/         # NUEVO
│   ├── detect_all.py
│   ├── cantidades_hospitalizacion.py
│   ├── cantidades_soat_hospitalizacion.py
│   └── hospitalizacion_codes.py
├── intramural/              # NUEVO (vacío inicial)
│   └── detect_all.py
├── ambulatoria/             # NUEVO (vacío inicial)
│   └── detect_all.py
└── tipo_factura_registry.py # NUEVO: mapea valor columna → lista detectores
```

### Estrategia de migración: 2 PRs incrementales

**PR 1 — Filtros internos (riesgo bajo, sin cambio estructural):**
1. Agregar `if tipo_factura_str != "Urgencias": continue` en detectores que no lo tienen:
   - `profesionales_urgencias.py`
   - `ide_contrato_urgencias.py`
   - `ide_contrato_reverse.py`
2. Mover `detect_copago_entidad.py` a `transversales/`
3. Mover `mal_capitado.py` a `urgencias/` (o duplicar lógica)
4. Actualizar imports en `detect_all.py`

**PR 2 — Reorganización estructural (riesgo medio):**
1. Crear packages `hospitalizacion/`, `intramural/`, `ambulatoria/`
2. Mover detectores específicos a sus nuevos packages
3. Crear `tipo_factura_registry.py`
4. Actualizar `exporter.py` para dispatch por tipo_factura
5. Nuevos orquestadores por tipo

## Risks

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Romper tests existentes (~40 archivos) | Alto | PR incremental, correr tests en cada paso |
| `build_urgencias_normalized_rows` acoplado a estructura actual | Medio | Refactorizar o crear builders por tipo |
| Frontend React espera estructura de respuesta específica | Medio | Mantener formato JSON compatible |
| `centro_costo_urgencias.py` mezcla reglas de 4 tipos | Alto | Dividir en detectores por tipo (más trabajo) |
| Constantes en `urgencias.py` mezcladas | Bajo | Separar en archivos por tipo en el PR 2 |

## Ready for Proposal

**Sí.** La exploración es completa: se mapearon todos los detectores, se identificó qué tipo_factura aplica a cada uno, se detectaron code smells, y se propusieron dos enfoques de migración con riesgos y dependencias identificados.

**Próximo paso**: `sdd-propose` para crear la propuesta formal con el alcance del PR 1 y PR 2.
