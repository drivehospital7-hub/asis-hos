# Exploration: Reorganización de Módulos del Control System

## Current State

### Vista General

El sistema procesa archivos Excel de facturación médica para EPS MALLAMAS, con tres áreas funcionales: **Odontología**, **Urgencias** y **Equipos Básicos**. La lógica de detección de problemas vive predominantemente en un solo archivo monolítico (`revision_sheet.py`, ~6267 líneas), con reglas transversales parcialmente extraídas a `services/transversales/`. Las constantes están en un archivo único de 1346 líneas sin separación por dominio. El orquestador (`exporter.py`) es limpio pero maneja las tres áreas con condicionales internos.

### Estructura Actual de Archivos

```
app/services/
├── revision_sheet.py          ← ~6267 líneas, MONOLITO
├── exporter.py                ← 242 líneas, orquestador limpio
├── cruce_sheet.py             ← hoja CruceFacturas
├── transversales/             ← reglas compartidas (5 archivos, ~820 líneas total)
│   ├── __init__.py
│   ├── decimales.py
│   ├── tipo_documento_edad.py
│   ├── codigo_entidad.py
│   ├── tipo_usuario.py
│   └── estructura_excel.py
├── (bien separados:)          ← control_errores, abiertas_urgencias, genderize, derechos, notas
└── app/constants.py           ← 1346 líneas, TODO mezclado
```

---

## 1. Diagnóstico de `revision_sheet.py`

### Funciones por Área y Duplicación

| # | Función | Línea | Área | ¿Duplica transversales? | Observación |
|---|---------|-------|------|------------------------|-------------|
| 1 | `_normalize_header` | 302 | Transversal | No | Helper simple |
| 2 | `_normalize_invoice` | 307 | Transversal | No | Helper simple |
| 3 | `_get_column_indices` | 316 | Transversal | No | Mapea 27 columnas a índices |
| 4 | `_detect_decimals` | 423 | **Transversal** | **SÍ → `transversales/decimales.py`** | Duplicada. Diferencia: retorna `list[dict]` vs `list[str]` |
| 5 | `_detect_doble_tipo_procedimiento` | 468 | **Odontología** | No | Detecta >1 tipo en misma factura |
| 6 | `_detect_ruta_duplicada` | 503 | **Odontología** | No | Usa `RUTA_DUPLICADA_THRESHOLD` (3) |
| 7 | `_detect_ruta_duplicada_equipos_basicos` | 542 | **Equipos Básicos** | No → pero es **casi idéntica** a #6 | Solo difiere en la constante de threshold |
| 8 | `_detect_tipo_identificacion_edad` | 581 | **Transversal** | **SÍ → `transversales/tipo_documento_edad.py`** | Duplicada. Versión propia con misma lógica |
| 9 | `_detect_cantidades_anomalas` | 687 | **Odontología** | No | Usa constantes de odontología |
| 10 | `_detect_cantidades_anomalas_equipos_basicos` | 745 | **Equipos Básicos** | No → pero es **casi idéntica** a #9 | Solo difiere en constantes y agrega `procedimiento_idx` |
| 11 | `_detect_profesionales_odontologia` | 802 | **Odontología** | No | Valida HIGIENISTA/ODONTOLOGO vs códigos PYP |
| 12 | `_detect_mal_capitado` | 896 | **Urgencias** | No | Prefijo FEV/CAP en Número Factura |
| 13 | `_detect_cantidades_urgencias` | 1010 | **Urgencias** | No | Códigos con cantidad ≤ 1 |
| 14 | `_detect_cantidades_soat_urgencias` | 1096 | **Urgencias** | No | SOAT Urgencias cantidad = 1 |
| 15 | `_detect_cantidades_soat_hospitalizacion` | 1184 | **Urgencias** | No | SOAT Hospitalización cantidades por estancia |
| 16 | `_detect_cantidades_hospitalizacion` | 1326 | **Urgencias** | No | 129B02/890601/890601H cantidades |
| 17 | `_detect_profesionales_urgencias` | 1479 | **Urgencias** | No | 7 tipos de profesional con reglas distintas |
| 18 | `_detect_profesionales_equipos_basicos` | 1821 | **Equipos Básicos** | No | Similar a #11 pero con diferentes constantes |
| 19 | `_detect_ide_contrato_odontologia` | 1904 | **Odontología** | No | 15+ entidades con reglas PyP vs No-PyP |
| 20 | `_detect_centro_costo_odontologia` | 2106 | **Odontología** | No | Modo simple y modo con días |
| 21 | `_get_codigos_no_en_db_ess118` | 2292 | **Urgencias** | No | Consulta DB PostgreSQL |
| 22 | `_detect_centro_costo_urgencias` | 2393 | **Urgencias** | No → pero **enorme** (~1800 líneas) | Maneja: centro_costo + ide_contrato + cups_equivalentes + sala_observacion + hospitalización. **Mal nombrada.** |
| 23 | `_detect_ide_contrato_reverse_urgencias` | 4201 | **Urgencias** | No | IDE → código esperado (sin entidad) |
| 24 | `_detect_revision_entidad_86_urgencias` | ~4409+ | **Urgencias** | No | Revisión específica |
| 25 | `_detect_revision_cantidad_urgencias` | ~ | **Urgencias** | No | Códigos exentos de cantidad |
| 26 | `_build_urgencias_normalized_rows` | ~ | **Urgencias** | No | Formatea a 6 columnas |
| 27 | `_build_odontologia_normalized_rows` | ~ | **Odontología** | No | Formatea a 6 columnas |
| 28 | `detect_all_problems` | 5718 | **Orquestador** | No | Dispatcher con 3 ramas gigantes |

### Hallazgos Críticos

1. **`_detect_decimals` (línea 423) duplica `transversales/decimales.py`**: La versión transversales retorna `list[str]` (solo números de factura), la versión en revision_sheet retorna `list[dict]` con `"factura"` y `"valores"`. La transversales se usa desde `detect_all_problems` para Urgencias, pero para Odontología y Equipos Básicos se usa la inline. **Solo una debe existir.**

2. **`_detect_tipo_identificacion_edad` (línea 581) duplica `transversales/tipo_documento_edad.py`**: La transversales es más completa (incluye `numero_identificacion`, `edad_anios`, `edad_meses`, mejor parsing de fechas, tipos adicionales NIP/NIT/PAS/PE/SC). La versión inline de revision_sheet es una versión más antigua y menos robusta. **La versión transversales debe ser la única.**

3. **Funciones casi idénticas con diferente threshold**:
   - `_detect_ruta_duplicada` vs `_detect_ruta_duplicada_equipos_basicos` → solo difieren en `RUTA_DUPLICADA_THRESHOLD` vs `EQUIPOS_BASICOS_RUTA_DUPLICADA_THRESHOLD`
   - `_detect_cantidades_anomalas` vs `_detect_cantidades_anomalas_equipos_basicos` → solo difieren en constantes
   - Podrían ser **una sola función parametrizada**.

4. **`_detect_centro_costo_urgencias` está MAL NOMBRADA**: Esta función de ~1800 líneas maneja:
   - Centro de costo (Reglas 1-9 + REVERSE)
   - IDE Contrato (~30 reglas)
   - Cups equivalentes (890201→890701, 129B01→129B02, 890205→890405)
   - Sala de observación (estancia >6h/≤6h, SOAT/no-SOAT)
   - Hospitalización (códigos obligatorios, códigos prohibidos, SOAT)
   - Códigos prohibidos (939402, 12333, 890601H)
   Debería dividirse en **al menos 4 funciones** independientes.

5. **`detect_all_problems` tiene 3 ramas gigantes** (Urgencias ~336 líneas, Equipos Básicos ~104 líneas, Odontología ~108 líneas). La rama de Urgencias llama 16+ detectores distintos.

---

## 2. Diagnóstico de `exporter.py`

### Lógica Condicional por Área

El archivo es limpio (242 líneas) pero tiene **dos puntos de bifurcación por área**:

| Línea | Condición | Qué hace |
|-------|-----------|----------|
| 94 | `area_effective = AREA_EQUIPOS_BASICOS if equipos_basicos else area` | Determina área efectiva |
| 101-130 | `if area_effective == AREA_ODONTOLOGIA or AREA_EQUIPOS_BASICOS` | Configura `profesional_dias` y `permitir_todos_centros` para validación de centro de costo |
| 187-191 | `if area_effective == AREA_URGENCIAS` → `columns_to_keep = None` (todas) | Urgencias no filtra columnas; Odontología/EB usan `COLUMNS_TO_KEEP` |
| 201-206 | `detect_all_problems(data_sheet, area=area_effective, ...)` | El área se pasa al orquestador de problemas; parámetros adicionales solo para Odontología/EB |

**Conclusión**: `exporter.py` es un orquestador limpio que delega correctamente. La bifurcación por área es mínima y necesaria. No requiere refactor urgente.

### Funciones llamadas

- `detectar_estructura_excel()` → transversales
- `filter_columns()` → utils
- `detect_all_problems()` → `revision_sheet.py` (el monolito)
- `create_cruce_facturas_sheet()` → `cruce_sheet.py`
- `apply_all_conditional_formatting()` → utils

---

## 3. Mapeo de Reglas Transversales

### Lo que está en `services/transversales/`

| Módulo | Función exportada | Propósito |
|--------|-------------------|-----------|
| `decimales.py` | `detect_decimales(data_sheet, indices) → list[str]` | Detecta valores decimales en Vlr. Subsidiado/Procedimiento |
| `tipo_documento_edad.py` | `detect_tipo_documento_edad(data_sheet, indices) → list[TipoDocumentoEdadProblema]` | Valida tipo ID vs edad del paciente |
| `codigo_entidad.py` | `detect_codigo_entidad_vs_entidad_afiliacion(data_sheet, indices) → list[dict]` | Compara Cód Entidad Cobrar vs Entidad Afiliación |
| `codigo_entidad.py` | `detect_codigo_entidad_vs_entidad_afiliacion_simple(file_path) → dict` | Versión standalone para verificación rápida |
| `tipo_usuario.py` | `detect_tipo_usuario(data_sheet, indices) → list[TipoUsuarioProblema]` | Valida Tipo Usuario contra lista permitida |
| `estructura_excel.py` | `detectar_estructura_excel(file_path) → dict` | Detecta si el Excel tiene filas de encabezado |
| `estructura_excel.py` | `get_filas_a_eliminar(file_path) → int` | Wrapper simple |

### Lo que se DUPLICA en `revision_sheet.py`

| Regla | En `transversales/` | En `revision_sheet.py` | ¿Cuál es mejor? |
|-------|---------------------|------------------------|-----------------|
| **Decimales** | `decimales.py::detect_decimales` → `list[str]` | `_detect_decimals` (línea 423) → `list[dict]` | La transversales es más limpia, pero retorna menos info. La de revision incluye los valores con decimal. **Unificar en transversales con ambos formatos.** |
| **Tipo ID vs Edad** | `tipo_documento_edad.py::detect_tipo_documento_edad` → `list[TipoDocumentoEdadProblema]` | `_detect_tipo_identificacion_edad` (línea 581) → `list[dict]` | **La transversales es superior** (mejor parsing, más campos, tipos adicionales). |
| **Cód Entidad vs Afiliación** | `codigo_entidad.py` | NO duplicada (se usa la transversales) | ✅ |
| **Tipo Usuario** | `tipo_usuario.py` | NO duplicada (se usa la transversales) | ✅ |

### Lo que DEBERÍA estar en transversales y no está

| Regla | Dónde está ahora | Por qué debería ser transversal |
|-------|-----------------|-------------------------------|
| **Normalización de headers** | `revision_sheet.py::_normalize_header` + `_normalize_invoice` | Usadas por TODAS las áreas |
| **Mapeo de columnas** | `revision_sheet.py::_get_column_indices` | Lo usa `detect_all_problems` para todas las áreas |
| **Ruta duplicada** | `revision_sheet.py::_detect_ruta_duplicada` + versión equipos_basicos | Misma lógica, solo cambia el threshold → parametrizar |
| **Cantidades anómalas** | `revision_sheet.py::_detect_cantidades_anomalas` + versión equipos_basicos | Misma lógica, solo cambian constantes → parametrizar |
| **Doble tipo procedimiento** | `revision_sheet.py::_detect_doble_tipo_procedimiento` | Se usa en Odontología y Equipos Básicos |

---

## 4. Clasificación de `constants.py`

1346 líneas. Agrupables así:

| Grupo Lógico | Líneas aprox. | Contenido |
|-------------|---------------|-----------|
| **Excel / Sheets** | ~15 | Sufijos permitidos, nombres de hojas |
| **Columnas** | ~55 | `COLUMNS_TO_KEEP`, `URGENCIA_COLUMNS_TO_KEEP` |
| **Colores UI** | ~30 | `COLOR_*`, `HEADER_BACKGROUND_COLOR`, `URGENCIA_*_COLOR` |
| **Convenios / Entidades** | ~15 | `CONVENIO_ASISTENCIAL`, `CONVENIO_PYP`, `ENTIDAD_MALLAMAS`, centros de costo base |
| **PyP / Códigos CUPS Odontología** | ~110 | `PYP_CUPS_CODES`, `PYP_CODES_ONLY_ODONTOLOGO`, `PYP_CODES_HIGIENISTA`, `TARGET_PROCEDURES` |
| **IDE Contrato — Odontología (PyP)** | ~120 | 16 entidades con reglas PyP vs No-PyP |
| **IDE Contrato — Urgencias** | ~250 | 30+ bloques de constantes para combinaciones código+entidad→IDE |
| **IDE Contrato — Reverse** | ~90 | `IDE_CONTRATO_REVERSE_*` |
| **Profesionales** | ~215 | 4 diccionarios: odontología, odontología validación, equipos básicos, urgencias |
| **Urgencias — Reglas de Centro Costo** | ~95 | Códigos PYP, Quirófano, Laboratorio, Farmacia |
| **Urgencias — Sala Observación / Cups Equivalentes** | ~60 | Estancia, SOAT, códigos equivalentes |
| **Urgencias — Cantidades / Hospitalización / SOAT** | ~100 | Códigos con límites de cantidad, reglas SOAT |
| **Urgencias — Capita** | ~70 | `URGENCIAS_CAPITA_CUPS_CODES` (100+ códigos) |
| **Urgencias — Control Errores** | ~60 | `ERROR_TIPO_URGENCIAS`, `ERROR_ESTADO_URGENCIAS`, responsables |
| **Equipos Básicos** | ~35 | Thresholds, headers, columns (mayormente duplica odontología) |
| **Revisión Necesaria** | ~50 | Códigos exentos de cantidad, límites específicos |
| **Umbrales Genéricos** | ~15 | `RUTA_DUPLICADA_THRESHOLD`, `CANTIDAD_CONSULTAS_MIN`, etc. |
| **Headers de Hojas** | ~20 | `REVISION_HEADERS`, `URGENCIA_REVISION_HEADERS`, `CRUCE_HEADERS` |
| **MAL CAPITADO** | ~15 | Códigos y prefijos FEV/CAP |

**Problema**: Constantes de IDE Contrato para Urgencias representan ~250 líneas con nombres extremadamente largos (ej: `CODIGO_IDE_CONTRATO_906340_ESSC18`). Muchas constantes solo se usan en UNA función de `revision_sheet.py`. Sería más mantenible como diccionarios anidados en módulos específicos de área.

---

## 5. Resumen de CONVENTIONS.md

### Reglas Documentadas por Área

| Área | Reglas Documentadas |
|------|---------------------|
| **Transversal** | Tipo ID vs Edad, Decimales, Cód Entidad vs Afiliación, Tipo Usuario |
| **Odontología** | Doble tipo, Ruta duplicada (≥3 PyP), Convenio incorrecto, Cantidades anómalas |
| **Urgencias** | Centros de costo, IDE Contrato (por código+entidad), Cantidades urgencias, Cantidades hospitalización, Sala Observación, SOAT, Cups equivalentes |
| **Equipos Básicos** | Comparte validaciones de Odontología |
| **Abiertas Urgencias** | Horarios y responsables (30 min handover) |

**Observación**: CONVENTIONS.md está bien documentado y sirve como especificación funcional. Refleja lo que el código hace, pero no prescribe CÓMO debería estar organizado. La documentación de reglas de Urgencias es extensa (tablas de IDE Contrato por entidad), lo que refuerza la necesidad de separar estas reglas en módulos dedicados.

---

## 6. Recomendación de Estructura Objetivo

### Principios de Diseño

1. **Una responsabilidad por archivo** (SRP): Cada detector de reglas en su propio módulo.
2. **Reglas transversales en `transversales/`**: Sin duplicación con `revision_sheet.py`.
3. **Reglas por área en subdirectorios dedicados**: `services/odontologia/`, `services/urgencias/`, `services/equipos_basicos/`.
4. **Constantes por dominio**: `constants/odontologia.py`, `constants/urgencias.py`, etc.
5. **`revision_sheet.py` eliminado**: Reemplazado por el orquestador `detect_all_problems` en cada área.

### Estructura Propuesta

```
app/
├── constants/
│   ├── __init__.py              ← re-exporta todo para compatibilidad
│   ├── base.py                  ← ALLOWED_EXCEL_SUFFIXES, nombres de sheets, áreas
│   ├── odontologia.py           ← PYP_CUPS_CODES, profesionales, thresholds, IDE Contrato PyP
│   ├── urgencias.py             ← IDE Contrato, centros costo, sala observación, SOAT, CAPITA
│   ├── equipos_basicos.py       ← thresholds, profesionales EB
│   ├── colores.py               ← COLOR_* (UI)
│   └── columnas.py              ← COLUMNS_TO_KEEP, URGENCIA_COLUMNS_TO_KEEP
│
├── services/
│   ├── exporter.py              ← SIN CAMBIOS (ya está bien)
│   ├── cruce_sheet.py           ← SIN CAMBIOS
│   │
│   ├── transversales/           ← reglas compartidas (ampliado)
│   │   ├── __init__.py
│   │   ├── decimales.py         ← unificado (única implementación)
│   │   ├── tipo_documento_edad.py
│   │   ├── codigo_entidad.py
│   │   ├── tipo_usuario.py
│   │   ├── estructura_excel.py
│   │   ├── column_indices.py    ← NUEVO: _get_column_indices (extraído de revision_sheet)
│   │   ├── ruta_duplicada.py    ← NUEVO: parametrizado (threshold configurable)
│   │   ├── cantidades_anomalas.py ← NUEVO: parametrizado
│   │   └── doble_tipo.py        ← NUEVO: _detect_doble_tipo_procedimiento
│   │
│   ├── odontologia/             ← NUEVO: reglas solo de odontología
│   │   ├── __init__.py
│   │   ├── profesionales.py     ← _detect_profesionales_odontologia
│   │   ├── centro_costo.py      ← _detect_centro_costo_odontologia
│   │   ├── ide_contrato.py      ← _detect_ide_contrato_odontologia
│   │   └── detect_all.py        ← orquestador: llama transversales + específicas
│   │
│   ├── urgencias/               ← NUEVO: reglas solo de urgencias
│   │   ├── __init__.py
│   │   ├── centro_costo.py      ← Reglas 1-9 + REVERSE (extraído de _detect_centro_costo_urgencias)
│   │   ├── ide_contrato.py      ← ~30 reglas de IDE Contrato
│   │   ├── cups_equivalentes.py ← 890201, 129B01, 890205, sala observación
│   │   ├── sala_observacion.py  ← Estancia >6h/≤6h, SOAT, códigos obligatorios
│   │   ├── hospitalizacion.py   ← Códigos obligatorios/prohibidos, cantidades
│   │   ├── profesionales.py     ← _detect_profesionales_urgencias (7 tipos)
│   │   ├── mal_capitado.py      ← Prefijo FEV/CAP
│   │   ├── cantidades.py        ← Urgencias, SOAT Urgencias, Hospitalización, SOAT Hosp.
│   │   ├── revision.py          ← _detect_revision_entidad_86, _detect_revision_cantidad
│   │   ├── codigos_db.py        ← _get_codigos_no_en_db_ess118
│   │   ├── ide_contrato_reverse.py ← _detect_ide_contrato_reverse_urgencias
│   │   └── detect_all.py        ← orquestador: llama transversales + específicas
│   │
│   └── equipos_basicos/         ← NUEVO: reglas solo de equipos básicos
│       ├── __init__.py
│       ├── profesionales.py     ← _detect_profesionales_equipos_basicos
│       └── detect_all.py        ← orquestador: reusa transversales + reglas EB
│
├── utils/
│   ├── formatting.py            ← SIN CAMBIOS
│   ├── column_filter.py         ← SIN CAMBIOS
│   └── ...
```

### Qué Eliminar

- **`revision_sheet.py`**: Desaparece. Cada detector va a su módulo de área o a transversales.
- **`_detect_decimals`** (línea 423) y **`_detect_tipo_identificacion_edad`** (línea 581): Se eliminan del todo; solo queda la versión transversales.
- **`_detect_ruta_duplicada_equipos_basicos`** y **`_detect_cantidades_anomalas_equipos_basicos`**: Se unifican con sus versiones de odontología mediante parametrización.

### Interfaz de Cada Módulo de Detección

Cada detector debe seguir la misma firma:

```python
def detect_X(data_sheet: Worksheet, indices: dict[str, int | None], **kwargs) -> list[dict]:
    """Detecta problemas de X. Retorna lista de dicts."""
```

El orquestador de cada área (`detect_all.py`) será responsable de:
1. Obtener índices de columnas (vía `transversales.column_indices`)
2. Llamar a cada detector
3. Consolidar resultados en el formato de respuesta estándar

---

## 7. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Regresión en reglas de negocio** | Alta | Crítico | Mover UNA regla a la vez con tests de verificación. No hacer big-bang refactor. |
| **Ruptura de imports** | Alta | Medio | Mantener `constants.py` como fachada que re-exporta de los nuevos módulos. Usar `__init__.py` con imports explícitos. |
| **Duplicación temporal durante migración** | Media | Bajo | Fase 1: crear nuevos módulos en paralelo. Fase 2: cambiar imports. Fase 3: eliminar código viejo. |
| **IDE Contrato Urgencias extremadamente acoplado** | Alta | Alto | Las ~30 reglas de IDE Contrato en `_detect_centro_costo_urgencias` están entremezcladas con reglas de centro costo en el mismo loop. Extraer requiere separar el loop en fases independientes. |
| **Pérdida de logging/debug** | Media | Medio | Cada regla tiene logs extensos con `logger.warning`. Al migrar, preservar los mensajes de log exactos o mejorar su formato. |
| **Inconsistencia en formatos de retorno** | Media | Medio | `_detect_decimals` retorna `list[dict]`, `transversales/decimales.py` retorna `list[str]`. Unificar requiere actualizar los consumidores (frontend templates, `detect_all_problems`). |
| **Falta de tests automatizados** | Alta | Alto | No hay tests unitarios para las reglas de detección. Cada movimiento debe ser validado manualmente con archivos Excel reales. |

---

## Ready for Proposal

**Sí**. La exploración identificó claramente:
- El monolito (`revision_sheet.py`, 6267 líneas)
- Las duplicaciones exactas (decimales, tipo ID/edad)
- Las casi-duplicaciones (ruta duplicada, cantidades anómalas entre odontología y EB)
- Las reglas mal agrupadas (`_detect_centro_costo_urgencias` hace 5+ cosas)
- Las constantes mezcladas (1346 líneas sin agrupación por dominio)
- Las rutas/bifurcaciones existentes (exporter.py con condicionales por área)

La propuesta debe plantear una migración **incremental**, moviendo un grupo de reglas a la vez, manteniendo compatibilidad hacia atrás con `from app.constants import ...` mediante re-exports.
