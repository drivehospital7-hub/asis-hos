# Exploration: Migración Completa de Reglas Legacy al Motor de Reglas

## Current State

Se han migrado **9 detectores** al motor de reglas DB-backed:
- `valores_decimales`, `ruta_duplicada`
- `tipo_id_requiere_entidad_86000`, `entidad_86000_requiere_as_ms`
- `tipo_usuario_valido`
- `cantidad_consultas_anomalas`, `cantidad_general_anomalas`, `cantidad_pyp_anomalas`
- `copago_entidad_valido`

El motor actual soporta:
- **Operadores atómicos**: `eq`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`, `regex`
- **Operadores compuestos**: `AND`, `OR`, `NOT` (con short-circuit)
- **Evaluación fila por fila** (cada fila es independiente)
- **Parámetros** (JSONB configurables por regla)
- **Excepciones** (skip/override por scope)
- **Providers**: Solo `InvoiceProvider` (resuelve `invoice.{field_name}`)
- **Evidence + Audit trail** (Evidencia → ResultadoAuditoria)

**~30+ detectores legacy** permanecen sin migrar, con lógica que va más allá de la evaluación fila-por-fila.

---

## All Remaining Detectors — Categorized

### 1. TRANSVERSALES (`app/services/transversales/`)

| Detector | Archivo | ¿Qué hace? | Capability Necesaria | Complejidad |
|---|---|---|---|---|
| **tipo_documento_edad** | `tipo_documento_edad.py` | Valida tipo de documento (CC, TI, RC, MS, AS, CN, CE) según edad calculada desde fecha nacimiento y fecha factura. Reglas por rango etario y tipo de documento. Calcula edad en años y meses. | **Age calculation function**: necesita fecha_nacimiento - fecha_factura → edad en años y meses. Operador `age_based_doc_type` o proveedor `patient.age`. | **medium** |
| **codigo_entidad** | `codigo_entidad.py` | Extrae código de entidad desde texto tipo `"{ESSC18}"` vía regex y lo compara con `Cód Entidad Cobrar`. | **Regex extract + cross-column compare**: necesita extraer substring vía regex y comparar con otro campo. Se podría modelar como dos condiciones atómicas (regex + eq) si hay un provider que extraiga. | **simple** |
| **centro_costo_rules** | `centro_costo_rules.py` | 10+ reglas de centro de costo (1, 1-REVERSE, 2, 2-REVERSE, 3, 3-REVERSE, 4, 4-REVERSE, 8, 9, 9-REVERSE, CENTRO_INVALIDO). Compara múltiples columnas contra constantes. | **Constantes en DB**: las reglas referencian constantes como `CODIGO_TIPO_PROCEDIMIENTO_DIAGNOSTICO=02`, `LABORATORIO_NO=No`, `CENTRO_COSTO_FARMACIA=FARMACIA`, etc. Necesita tabla de constantes o parametrización. | **complex** (muchas reglas, constantes) |
| **doble_tipo_procedimiento** | `doble_tipo_procedimiento.py` | Agrupa filas por factura, recolecta todos los `tipo_procedimiento` distintos. Si una factura tiene >1 tipo, marca error. | **Group-by aggregation**: necesita agrupar filas por factura y contar valores distintos de otra columna. | **medium** |
| **detect_duplicados_base** | `detect_duplicados_base.py` | Agrupa filas por factura (y opcionalmente código tipo procedimiento). Dentro del grupo, cuenta ocurrencias de cada par (código, cantidad). Si TODOS los pares tienen count ≥ 2, el grupo se marca como duplicado. | **Group-by multi-pass aggregation**: necesita (1) filtrar, (2) agrupar, (3) contar pares, (4) verificar condición sobre el grupo completo. Totalmente fuera del modelo fila-por-fila. | **high** |
| **cups_equivalentes** | `cups_equivalentes.py` | Mapeo simple de código incorrecto → código correcto (906317→1906317, 906249→906249PR). | **Code substitution mapping**: lookup table de código → reemplazo. Se podría modelar como regla que chequea si el código está en un set y reporta el reemplazo. | **simple** |
| **procedimiento_contratado** | `procedimiento_contratado.py` | Consulta DB (JOIN 5 tablas: EpsContratado → EpsNota → NotaHoja → NotasTecnicas → Procedimiento) para verificar si el par (entidad, código) está contratado. Excepciones: responsables urgencias, facturas CAP, entidades con nota_hoja especial. | **DB cross-reference provider**: necesita provider que ejecute query multi-tabla y devuelva si un par (entidad, cups) es válido. **Scope exceptions por entidad/tipo de factura**. | **complex** |
| **create_revision_sheet** | `create_revision_sheet.py` | **NO es un detector**. Es un builder de la hoja Revision en Excel. Orquesta TODOS los detectores y normaliza resultados. | No migrar. | N/A |

### 2. ODONTOLOGÍA (`app/services/odontologia/`)

| Detector | Archivo | ¿Qué hace? | Capability Necesaria | Complejidad |
|---|---|---|---|---|
| **profesionales** | `profesionales.py` | Busca código profesional en diccionario `PROFESIONALES_ODONTOLOGIA_VALIDACION`. Si es HIGIENISTA, solo códigos PyP. Si es ODONTOLOGO, no códigos PyP (excepto P0000011). | **Catalog lookup**: necesita diccionario de profesionales (código → tipo). **Lookup table provider** o importar datos a DB. | **medium** |
| **ide_contrato** | `ide_contrato.py` | ~15 entidades con reglas PyP/NO-PyP, cada una tiene un set de IDE Contrato válido. Para RES001, la validación depende del mes de factura (histórico). | **Multi-value validation**: reglas entidad + código → set de IDE válidos. **Month-dependent rules** (histórico RES001). | **medium** |
| **centro_costo** | `centro_costo.py` | Dos modos: (1) solo permite ODONTOLOGIA y EXTRAMURAL; (2) validación por días del profesional + fecha de factura. Calcula día de la semana desde fec_factura. | **Date parsing provider**: necesita extraer el día del mes de una fecha. **Calendar lookup**: profesional_id → días seleccionados. | **medium** |

### 3. URGENCIAS (`app/services/urgencias/`)

| Detector | Archivo | ¿Qué hace? | Capability Necesaria | Complejidad |
|---|---|---|---|---|
| **profesionales_urgencias** | `profesionales_urgencias.py` | Busca código profesional en `PROFESIONALES_URGENCIAS`. Valida por tipo (TRABAJADORA_SOCIAL, PSICOLOGA, NUTRICIONISTA, FISIOTERAPEUTA, JEFE_ENFERMERIA, BACTERIOLOGA, ODONTOLOGO, MEDICO) — cada tipo tiene sus códigos CUPS permitidos/prohibidos. Validación de laboratorio para BACTERIOLOGA y MEDICO. | **Complex catalog + conditional validation**: catálogo de profesionales + reglas por tipo + validación multi-columna. Necesita lookup table y reglas condicionales anidadas. | **high** |
| **ide_contrato_urgencias** | `ide_contrato_urgencias.py` | ~30+ reglas de IDE Contrato: simples (exact match), condicionales por inserción 861801 (pre-scan de identificación), condicionales por 890405 (ESSC62), múltiples (set de IDE válidos), Regla 29 (entidad→contrato), Regla 30 (entidad multi-contrato). | **Multi-pass pre-scan**: necesita escanear todo el Excel primero para recolectar identificaciones con 861801/890405. **Multi-rule registry**: 4 tipos de reglas con diferentes lógicas de matching. | **high** |
| **ide_contrato_reverse** | `ide_contrato_reverse.py` | Dado un IDE Contrato, verifica que el código CUPS corresponda. ~12 reglas reverse (986, 977, 979, 839, 842, 958, 961, 922, 863, 975, 920, 908, 970, 974). Condicionales por presencia de 861801 en la identificación. | **Multi-pass pre-scan** (mismo que ide_contrato_urgencias — necesita identificar identificaciones con 861801). **Reverse conditional logic**. | **high** |
| **centro_costo_urgencias** | `centro_costo_urgencias.py` | Aplica `centro_costo_rules` (compartidas) + regla específica: Urgencias + Centro=HOSPITALIZACIÓN → Error. Wrapper que delega en transversales. | **Reuse centro_costo_rules**: depende de la migración de centro_costo_rules primero. | **medium** |
| **cantidades_urgencias** | `cantidades_urgencias.py` | Códigos específicos (URGENCIAS_CODIGOS_CANTIDAD_MAX_1) deben tener cantidad ≤ 1. | Row-by-row, simple. **Lookup set** de códigos. | **simple** |
| **cantidades_soat_urgencias** | `cantidades_soat_urgencias.py` | Si Tarifario=SOAT + Urgencias, códigos específicos deben tener cantidad = 1. | Row-by-row, simple. **Multi-condition**: tarifario filter + código filter. | **simple** |
| **mal_capitado** | `mal_capitado.py` | (1) Códigos G03XB01/A02BB01 deben tener factura con prefijo "FEV". (2) Factura con prefijo "CAP" requiere entidad ESS118. | **Prefix matching** en número de factura (`contains` o `startswith`). **Entidad conditional**. | **simple** |
| **sala_observacion** | `sala_observacion.py` | ~10+ reglas de sala de observación: estancia basada en horas (fec_factura - fecha_cierre), códigos requeridos según horas y entidad, códigos prohibidos (890601H, 05DSB01, 129B02), reglas SOAT especiales. Requiere agrupar datos por factura (pre-scan). | **Date diff calculation**: fec_factura - fecha_cierre → horas de estancia. **Group-by pre-scan**: recolectar todos los códigos por factura. **Multi-conditional rules**: estancia + entidad + tarifario. | **complex** |
| **revision_entidad_86** | `revision_entidad_86.py` | Marca facturas con entidad=86 para revisión manual. | Row-by-row, simple `eq` check. | **simple** |
| **revision_cantidad** | `revision_cantidad.py` | Reglas de cantidad anómala: general (cantidad > 1 salvo exentos), 02+Lab=No (máx 2, 903883 máx 5), 09/12 (máx 20, V03AN0101 exento). | **Multi-rule cascade**: aplicar regla según condiciones de código_tipo_procedimiento y laboratorio. Similar a centro_costo_rules pero en cascada. | **medium** |
| **duplicados_farmacia** | `duplicados_farmacia.py` | Thin wrapper que delega en `detect_duplicados_generico` (transversales) con parámetros de Urgencias. | Depende de `detect_duplicados_generico` → **group-by multi-pass**. | **high** (por dependencia) |
| **cups_equivalentes** | `cups_equivalentes.py` | Reglas CUPS por entidad: 890201→890701, 129B01→129B02, 890205→890405 (excepto ESS118/ESSC18), 939402 prohibido en Hospitalización, 12333 prohibido en Hospitalización. | **Conditional code substitution**: depende de entidad y tipo_factura. | **medium** |

### 4. EQUIPOS BÁSICOS (`app/services/equipos_basicos/`)

| Detector | Archivo | ¿Qué hace? | Capability Necesaria | Complejidad |
|---|---|---|---|---|
| **profesionales** | `profesionales.py` | Misma lógica que odontología.profesionales pero con `PROFESIONALES_EQUIPOS_BASICOS`. Catalogo lookup + validación por tipo. | **Catalog lookup** (mismo que odontología). | **medium** |

---

## New Engine Capabilities Needed (Grouped by Type)

### 1. Age / Date Calculation Functions
- **`age_from_dates(birth_date, reference_date) → int`**: calcular edad en años y meses
- **`hours_diff(start_date, end_date) → float`**: calcular horas de estancia
- **`day_of_month(date) → int`**: extraer día del mes (para centro_costo odontología)
- **`month(date) → int`**: extraer mes (para RES001 histórico)
- Afecta: `tipo_documento_edad`, `sala_observacion`, `centro_costo_odontologia`, `ide_contrato_odontologia`

### 2. String Operation Functions
- **`startswith(str, prefix) → bool`**: para prefijos FEV, CAP (mal_capitado)
- **`regex_extract(str, pattern) → str`**: extraer substring vía regex (codigo_entidad)
- Afecta: `mal_capitado`, `codigo_entidad`

### 3. Group-By / Aggregation Engine
- **`group_by(factura) → {key: [rows]}`**: agrupar filas por factura
- **`distinct_count(column, group) → int`**: contar valores distintos dentro del grupo
- **`pair_count(group) → dict`**: contar ocurrencias de pares (código, cantidad)
- **`collect_set(column, group) → set`**: recolectar valores únicos (códigos de sala)
- Afecta: `doble_tipo_procedimiento`, `detect_duplicados_base`, `sala_observacion`, `duplicados_farmacia`

### 4. Multi-Pass / Pre-Scan Support
- **Pre-scan phase**: escanear todo el Excel antes de la evaluación principal para recolectar metadatos (identificaciones con 861801, 890405)
- Afecta: `ide_contrato_urgencias`, `ide_contrato_reverse`

### 5. Catalog / Lookup Table Provider
- **`CATALOG_PROVIDER`**: resolver código profesional → tipo y nombre desde tabla DB
- **`CONTRACT_PROVIDER`**: verificar si par (entidad, cups) existe en DB (JOIN 5 tablas)
- **`CODE_MAPPING_PROVIDER`**: lookup de código incorrecto → código correcto
- Afecta: `profesionales_odontologia`, `profesionales_urgencias`, `profesionales_equipos_basicos`, `procedimiento_contratado`, `cups_equivalentes` (ambos)

### 6. Constants / Reference Data in DB
- Tabla de constantes (tipo `centro_costo_rules.CENTRO_COSTO_FARMACIA`, `VALOR_TARIFARIO_FARMACIA`, etc.)
- Tabla de profesionales (tipo `PROFESIONALES_ODONTOLOGIA_VALIDACION`, `PROFESIONALES_URGENCIAS`)
- Tabla de sets de IDE válidos (tipo `IDE_CONTRATO_MULTIPLE_*`)
- Afecta: `centro_costo_rules`, `ide_contrato_odontologia`, `ide_contrato_urgencias`

### 7. Complex Conditional / Multi-Rule Cascade
- **Rule chaining**: aplicar reglas en orden de prioridad, cascada con REVERSE rules
- **Conditional branches**: elegir regla según combinación de columnas (entidad + código + tipo_procedimiento + laboratorio)
- Afecta: `profesionales_urgencias` (8 tipos con reglas diferentes), `revision_cantidad` (3 niveles de cascada)

### 8. Calendar / Day-Based Validation
- Proveedor de días seleccionados por profesional (desde DB o parámetros)
- Validación de fecha contra días del calendario
- Afecta: `centro_costo_odontologia`

---

## Recommended Migration Order

### Fase 1 — Bajo Riesgo, Rápido (3-4 detectores)
Migrar los detectores que son esencialmente **row-by-row con lookup simple**:

1. **`cups_equivalentes` (transversal)** — lookup table simple. Agregar provider de mapeo de códigos.
2. **`revision_entidad_86`** — eq check trivial.
3. **`cantidades_urgencias`** — set lookup + gt check.
4. **`cantidades_soat_urgencias`** — multi-condition + eq check.
5. **`mal_capitado`** — prefix matching + eq check.

**Esfuerzo**: 1-2 días. **Riesgo**: Bajo.

### Fase 2 — Catálogos + DB Cross-Reference (3 detectores)
Migrar los que dependen de datos maestro en DB:

6. **`profesionales` (odontología)** — catalog lookup.
7. **`profesionales` (equipos básicos)** — catalog lookup (mismo provider).
8. **`profesionales_urgencias`** — catalog lookup + conditional rules (más complejo).

**Esfuerzo**: 2-3 días. **Riesgo**: Medio. Requiere importar datos de profesionales a DB.

### Fase 3 — IDE Contrato (3 detectores)
Migrar las reglas de IDE Contrato que comparten lógica:

9. **`ide_contrato` (odontología)** — multi-value + month-dependent.
10. **`ide_contrato_urgencias`** — pre-scan + multi-rule registry.
11. **`ide_contrato_reverse`** — pre-scan + reverse conditional.

**Esfuerzo**: 3-4 días. **Riesgo**: Alto. Requiere implementar pre-scan + multi-rule registry.

### Fase 4 — Centro Costo (3 detectores)
Migrar centro de costo, que comparte lógica entre áreas:

12. **`centro_costo_rules` (transversal)** — base rules + constants.
13. **`centro_costo_urgencias`** — wrapper que importa rules.
14. **`centro_costo` (odontología)** — calendar-dependent.

**Esfuerzo**: 2-3 días. **Riesgo**: Medio. Requiere tabla de constantes.

### Fase 5 — Age + Date Calculations (2 detectores)
15. **`tipo_documento_edad`** — age calculation + type determination.
16. **`sala_observacion`** — hours diff + aggregation + multi-conditional.

**Esfuerzo**: 2-3 días. **Riesgo**: Medio. Requiere date function providers + group-by soporte parcial.

### Fase 6 — Aggregation / Group-By (3 detectores)
Los más complejos, porque exigen cambiar el paradigma de evaluación:

17. **`doble_tipo_procedimiento`** — simple group-by distinct count.
18. **`detect_duplicados_base`** → **`duplicados_farmacia`** — multi-pass group-by counting.
19. **`revision_cantidad`** — multi-rule cascade.

**Esfuerzo**: 3-5 días. **Riesgo**: Alto. Requiere extensión del engine para soportar evaluación por grupos.

### Fase 7 — DB Cross-Reference Complejo (2 detectores)
20. **`codigo_entidad`** — regex extract + compare.
21. **`procedimiento_contratado`** — DB JOIN query + scope exceptions.

**Esfuerzo**: 2-3 días. **Riesgo**: Alto. Requiere provider multi-tabla + exceptions avanzadas.

---

## Estimated Total Effort

| Fase | Detectores | Días Estimados | Riesgo |
|---|---|---|---|
| Fase 1 — Row-by-row simple | 5 | 1-2 | Bajo |
| Fase 2 — Catálogos | 3 | 2-3 | Medio |
| Fase 3 — IDE Contrato | 3 | 3-4 | Alto |
| Fase 4 — Centro Costo | 3 | 2-3 | Medio |
| Fase 5 — Date/Age | 2 | 2-3 | Medio |
| Fase 6 — Group-By | 3 | 3-5 | Alto |
| Fase 7 — DB Complejo | 2 | 2-3 | Alto |
| **Total** | **21 detectores** | **15-23 días** | |

---

## Engine Extensions Required (Prioritized)

### Must-Have (para Fases 1-2)
1. **Constantes provider** — tabla `parametros_sistema` con key/value para constantes compartidas
2. **Catalog lookup provider** — tabla `profesionales` con código, tipo, nombre
3. **Code mapping evaluator** — operador `substitute` que reemplaza código incorrecto por correcto
4. **Lookup table provider** — resolver conjuntos desde DB (URGENCIAS_CODIGOS_CANTIDAD_MAX_1, etc.)

### Should-Have (para Fases 3-4)
5. **Pre-scan phase** — hook `before_evaluate()` que recorre el sheet y carga metadatos en contexto
6. **Multi-rule registry** — soporte para múltiples reglas del mismo tipo con diferentes lógicas
7. **Date function providers** — `date_diff()`, `extract_month()`, `extract_day()`
8. **String function operators** — `startswith()`, `regex_extract()`

### Nice-to-Have (para Fases 5-6)
9. **Group-by evaluation mode** — evaluar reglas sobre grupos de filas, no solo filas individuales
10. **Aggregation functions** — `distinct_count()`, `pair_count()`, `collect_set()`
11. **Multi-rule cascade** — evaluar reglas en orden con fall-through (como revision_cantidad)

### Advanced (para Fase 7)
12. **DB cross-reference provider** — query multi-tabla arbitraria
13. **Reverse rules** — evaluar reglas donde columna A → debe ser B (como ide_contrato_reverse)

---

## Risks

1. **Group-by aggregation cambia el paradigma**: El engine actual evalúa fila-por-fila. Las reglas de grupo requieren un búfer de filas, lo que cambia el modelo mental. Podría requerir un engine secundario (GroupEvaluator) en paralelo al RowEvaluator existente.

2. **Pre-scan incrementa complejidad**: Los detectores de IDE Contrato necesitan 2 pases sobre los datos. El engine actual es single-pass. Habría que agregar un hook de pre-procesamiento.

3. **Constantes duplicadas**: Actualmente las constantes viven en `app/constants/` como frozensets/dicts de Python. Migrarlas a DB es tedioso pero necesario. Alternativa: mantener constantes en Python y referenciarlas desde la regla vía parámetros.

4. **Rendimiento**: Las reglas DB cross-reference (procedimiento_contratado) hacen JOINs pesados. Si se evaluaran por fila (1000+ filas), sería muy lento. Solución: pre-cargar todo el set de pares válidos en memoria (como ya hace el detector legacy).

5. **Pruebas de regresión**: Cada detector legacy tiene casos borde no documentados. Se recomienda usar el simulador de reglas existente (`app/services/reglas/simulator_service.py`) para comparar output legacy vs motor en cada migración.

---

## Ready for Proposal
**Sí**. Esta exploración cubre todos los detectores restantes (~21), categoriza las capacidades necesarias del engine, y propone un orden de migración por fases con esfuerzo estimado. El siguiente paso es crear el **proposal.md** con el enfoque técnico detallado para cada fase, empezando por la Fase 1 (bajo riesgo) para generar tracción.
