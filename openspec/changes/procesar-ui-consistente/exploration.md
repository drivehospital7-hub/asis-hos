# Exploration: `/procesar` UI Consistency

> **Change**: procesar-ui-consistente  
> **Project**: asis-hos (control_system_dev)  
> **Date**: 2026-06-25  
> **Phase**: SDD Explore

---

## 1. The Problem

The `/procesar` page displays problems in a 6-column format:

```
Tipo Error | Factura | Fec.Factura | Responsable | Descripción | Procedimiento (Var1) | Detalle (Var2)
```

Each problem type has a handler in one of two files:
- `app/services/odontologia/normalized_rows.py` — `build_odontologia_normalized_rows()` (used by Odontología + Equipos Básicos)
- `app/services/normalized_rows.py` — `build_normalized_rows()` (shared builder, used by Urgencias)

The engine (`RuleBasedDetector` → `RuleEvaluationEngine`) now enriches problem dicts with row data (`codigo`, `procedimiento`, `vlr_subsidiado`, etc. — see §2). But handlers were written for legacy detector formats and don't consistently use these enriched fields.

---

## 2. What the Engine Provides

### 2.1 Row-by-row rules (`engine.py` lines 149–171)

Every problem dict ALWAYS includes:

| Key | Source | Always present? |
|-----|--------|-----------------|
| `factura` | engine | ✅ Always |
| `problema` | rule.descripcion (or rule.nombre) | ✅ Always |
| `regla` | rule.nombre | ✅ Always |
| `severidad` | rule.severidad | ✅ Always |
| `param_config_id` | engine | ✅ Always |

PLUS these row data fields **when present in the Excel sheet** (engine iterates `row_data` and copies them over if available):

```
codigo, codigo_equiv, procedimiento, tipo_identificacion,
codigo_entidad_cobrar, tipo_procedimiento, vlr_subsidiado,
vlr_procedimiento, cantidad, convenio_facturado, centro_costo,
ide_contrato, entidad_cobrar, entidad_afiliacion, tipo_usuario,
vlr_copago, codigo_tipo_procedimiento, laboratorio, tarifario,
tipo_factura_descripcion, responsable_cierra, profesional_atiende,
identificacion, fec_nacimiento, fec_factura, edad, date.edad,
numero_identificacion
```

**Key fields engine does NOT provide** (compared to what legacy detectors output):
- `vlr_subsidiado`, `vlr_procedimiento` — ✅ Provided
- `codigo_profesional` — ❌ NOT in engine's field list
- `tipo_actual`, `tipo_deberia` — ❌ NOT provided; engine provides `tipo_identificacion` only
- `edad_anios`, `edad_meses` — ❌ NOT provided as named keys; engine provides `edad`, `date.edad`
- `centro_actual`, `centro_deberia` — ❌ NOT provided; engine provides `centro_costo`
- `idea_actual`, `ide_deberia` — ❌ NOT provided; engine provides `ide_contrato`
- `nota` — ❌ NOT provided
- `cod_entidad_actual`, `cod_entidad_esperado` — ❌ NOT provided; engine provides `codigo_entidad_cobrar`
- `codigo_profesional` — ❌ NOT provided; engine provides `codigo`, `profesional_atiende`
- `identificacion` — ✅ Provided (but NOT `codigo_profesional`)

### 2.2 Group-by rules (`group_evaluator.py` lines 301–307)

Group-by rules produce **extremely sparse** dicts:

| Key | Source | Always? |
|-----|--------|---------|
| `factura` | engine | ✅ |
| `problema` | rule_info.descripcion or nombre | ✅ |
| `regla` | rule_info.nombre | ✅ |
| `severidad` | rule_info.severidad | ✅ |

**No row data at all.** No `codigo`, no `procedimiento`, no `identificacion`, nothing.

**Currently known group-by rules**: none migrated yet (seed data has no `group_by` parametros). But the code path exists and is wired. When a rule gets `group_by` in its `parametros` column, the output becomes sparse.

---

## 3. Full Handler Analysis — Odontología (`build_odontologia_normalized_rows`)

### 3.1 Decimales (lines 64–88)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `valores_decimales` (row-by-row) |
| **Handler reads** | `factura`, `valores`, `vlr_subsidiado`, `vlr_procedimiento`, `codigo`, `procedimiento` |
| **Legacy format** | `list[str]` — just factura strings |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `vlr_subsidiado`, `vlr_procedimiento`, `problema` |
| **Is check** | ✅ Handles both formats via `isinstance(item, dict)` |
| **Gaps** | Uses `valores` fallback when engine provides `vlr_subsidiado`/`vlr_procedimiento` directly |
| **Impact** | 🟢 **Low** — works correctly |

### 3.2 Doble Tipo Procedimiento (lines 90–102)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `doble_tipo_procedimiento` (row-by-row) |
| **Handler reads** | `factura`, `tipos` |
| **Legacy format** | dict with `factura`, `tipos` |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `tipo_procedimiento`, `problema` |
| **Gaps** | ❌ `tipos` not in engine output. Engine provides `tipo_procedimiento` (single value, not list of distinct types). `descripcion` is hardcoded "Múltiples tipos de procedimiento" — could use `problema`. `procedimiento` column is empty — could show `codigo - procedimiento`. |
| **Impact** | 🟡 **Medium** — `detalle` shows `tipos` which is legacy-only |

### 3.3 Ruta Duplicada (lines 104–119)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `ruta_duplicada` (row-by-row, no `group_by` parametros yet) |
| **Handler reads** | `identificacion`, `facturas`, `cantidad` |
| **Legacy format** | dict with `identificacion`, `facturas` (comma-separated string), `cantidad` (int) |
| **Engine provides** | dict with `factura`, `problema`, `regla`, `severidad`, `identificacion` |
| **Gaps** | ❌ `facturas` (comma-separated list) and `cantidad` not in engine output. Handler builds `descripcion` from `cantidad`. `procedimiento` shows `facturas_list`. `detalle` shows `identificacion`. |
| **Impact** | 🔴 **High** — if engine is ON, this handler produces broken rows |

### 3.4 Profesionales / Convenio de procedimiento (lines 121–136)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `profesional_odontologia_valido` (row-by-row) |
| **Handler reads** | `factura`, `codigo_profesional`, `procedimiento`, `problema`, `regla` |
| **Legacy format** | dict with `factura`, `codigo_profesional`, `nombre`, `tipo`, `profesional_area`, `procedimiento` (= codigo), `regla`, `problema` |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `profesional_atiende`, `problema`, `regla` |
| **Gaps** | ❌ `codigo_profesional` NOT in engine field list (line 157–171). Engine has `codigo` (CUPS code, not professional code) and `profesional_atiende` (name, not code). Handler calls `_build_procedimiento(cod_prof, proc_nombre)` — `cod_prof` will be empty with engine. |
| **Impact** | 🟡 **Medium** — `codigo_profesional` missing; `procedimiento` column gets `codigo` instead of professional code |

### 3.5 Cantidades (lines 138–152)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `cantidad_consultas_anomalas`, `cantidad_general_anomalas`, `cantidad_pyp_anomalas` (row-by-row) |
| **Handler reads** | `factura`, `tipo_procedimiento`, `cantidad`, `problema` |
| **Legacy format** | dict with `factura`, `tipo_procedimiento`, `cantidad`, `convenio`, `problema` |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `tipo_procedimiento`, `cantidad`, `problema` |
| **Gaps** | Minor: `procedimiento` column shows `tipo_procedimiento` instead of `codigo - procedimiento` |
| **Impact** | 🟢 **Low** — works, but uses inconsistent field for `procedimiento` column |

### 3.6 Tipo Identificación / Edad (lines 154–177)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `tipo_documento_edad_*` (7 rules, row-by-row) |
| **Handler reads** | `factura`, `tipo_actual`, `tipo_deberia`, `edad_anios`, `edad`, `date.edad`, `numero_identificacion`, `identificacion`, `regla`, `problema` |
| **Legacy format** | dict with `factura`, `tipo_actual`, `tipo_deberia`, `numero_identificacion`, `edad_anios`, `edad_meses` |
| **Engine provides** | dict with `factura`, `tipo_identificacion`, `numero_identificacion`, `identificacion`, `edad`, `date.edad`, `problema`, `regla` |
| **Gaps** | ❌ `tipo_actual` → engine has `tipo_identificacion` (handler has fallback via `item.get("tipo_actual", "") or item.get("tipo_identificacion", "")` — OK). ❌ `tipo_deberia` not in engine output. Handler infers from `regla` name (fragile string matching). ❌ `edad_anios`, `edad_meses` not in engine output; engine has `edad`, `date.edad` (handler has fallback `item.get("edad_anios", "") or item.get("edad", "") or item.get("date.edad", "")` — works but `detalle` shows age only without months context). |
| **Impact** | 🟡 **Medium** — `tipo_deberia` inference is fragile; age display loses months fidelity |

### 3.7 Tipo Identificación / Entidad (lines 179–199)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `tipo_id_requiere_entidad_86000`, `entidad_86000_requiere_as_ms` (row-by-row) |
| **Handler reads** | `factura`, `tipo_identificacion`, `cod_entidad_actual`, `cod_entidad_esperado`, `problema` |
| **Legacy format** | dict with `factura`, `tipo_identificacion`, `cod_entidad_actual`, `cod_entidad_esperado`, `problema` (key name) |
| **Engine provides** | dict with `factura`, `tipo_identificacion`, `codigo_entidad_cobrar`, `problema`, `regla` |
| **Gaps** | ❌ `cod_entidad_actual` → engine provides `codigo_entidad_cobrar`. ❌ `cod_entidad_esperado` not in engine output. Handler builds descriptions from `problema` key directly — works but `detalle` shows `cod_actual` which maps to `codigo_entidad_cobrar`. |
| **Impact** | 🟡 **Medium** — works functionally but uses different key names |

### 3.8 Centro Costo (lines 201–214)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `centro_costo_odontologia_valido` (row-by-row) |
| **Handler reads** | `factura`, `centro_actual`, `centro_deberia` |
| **Legacy format** | dict with `factura`, `centro_actual`, `centro_deberia`, `profesional`, `fec_factura` |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `centro_costo`, `problema`, `regla` |
| **Gaps** | ❌ `centro_actual` → engine provides `centro_costo` (different key). ❌ `centro_deberia` not in engine output. `descripcion` uses `centro_deberia` — will show "N/A" with engine. `procedimiento` column is empty — engine provides `codigo`, `procedimiento` but they're not used. |
| **Impact** | 🟡 **Medium** — `centro_deberia` missing; `procedimiento` empty |

### 3.9 IDE Contrato (lines 216–231)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `ide_contrato_odontologia_valido` (row-by-row) |
| **Handler reads** | `factura`, `codigo`, `ide_actual`, `ide_deberia`, `nota` |
| **Legacy format** | dict with `factura`, `codigo`, `cod_entidad`, `ide_actual`, `ide_deberia`, `nota` |
| **Engine provides** | dict with `factura`, `codigo`, `procedimiento`, `ide_contrato`, `codigo_entidad_cobrar`, `problema`, `regla` |
| **Gaps** | ❌ `ide_actual` → engine provides `ide_contrato`. ❌ `ide_deberia` not in engine output. ❌ `nota` not in engine output. `descripcion` will show "IDE Contrato debería ser (N/A)" or empty. `procedimiento` is built from `codigo` — OK. |
| **Impact** | 🟡 **Medium** — `ide_deberia` and `nota` missing from engine |

### 3.10 Código Entidad vs Afiliación (lines 233–273)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `codigo_entidad` (row-by-row) |
| **Handler reads** | `factura`, `tipo_identificacion`, `cod_entidad_actual`, `cod_entidad_esperado`, `codigo_entidad_cobrar`, `entidad_cobrar_nombre`, `entidad_afiliacion`, `problema` |
| **Legacy format** (old) | dict with `factura`, `codigo_entidad_cobrar`, `entidad_cobrar_nombre`, `entidad_afiliacion`, `problema` |
| **Legacy format** (new) | dict with `factura`, `tipo_identificacion`, `cod_entidad_actual`, `cod_entidad_esperado`, `problema` (key name) |
| **Engine provides** | dict with `factura`, `codigo_entidad_cobrar`, `entidad_afiliacion`, `tipo_identificacion`, `problema`, `regla` |
| **Gaps** | Old path ✅ works. New path: `cod_entidad_actual` → `codigo_entidad_cobrar`, `cod_entidad_esperado` not in engine. But handler builds from `problema` key. |
| **Impact** | 🟢 **Low** — handles both paths, uses `problema` key for description |

### 3.11 Tipo Usuario (lines 275–288)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `tipo_usuario_valido` (row-by-row) |
| **Handler reads** | `factura`, `tipo_actual` |
| **Legacy format** | dict with `factura`, `tipo_actual` |
| **Engine provides** | dict with `factura`, `tipo_usuario`, `codigo`, `procedimiento`, `problema`, `regla` |
| **Gaps** | `tipo_actual` → engine provides `tipo_usuario` (different key, not mapped). `descripcion` hardcoded "Revisar tipo usuario en Targetero" (could use `problema`). `procedimiento` column empty — engine provides `codigo`, `procedimiento`. |
| **Impact** | 🟡 **Medium** — `tipo_actual` key mismatch; `codigo`/`procedimiento` not used |

### 3.12 Cups Sin Contrato (lines 290–306)

| Aspect | Detail |
|--------|--------|
| **Engine rule(s)** | `cups_sin_contrato` (row-by-row) |
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `entidad`, `codigo_entidad_cobrar`, `problema` |
| **Legacy format** | dict with `factura`, `codigo`, `procedimiento`, `entidad`, `codigo_entidad_cobrar` |
| **Engine provides** | dict with all these fields |
| **Gaps** | None significant |
| **Impact** | 🟢 **Low** — all keys available |

---

## 4. Full Handler Analysis — Shared Builder (`build_normalized_rows`, used by Urgencias)

### 4.1 Centros de Costo (lines 51–64)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `centro_actual`, `centro_deberia` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `centro_costo`, `problema`, `regla` |
| **Gaps** | ❌ `centro_actual` → `centro_costo`. ❌ `centro_deberia` not in engine. |
| **Impact** | 🟡 **Medium** |

### 4.2 IDE Contrato (lines 67–85)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `ide_contrato_deberia`, `ide_contrato_actual` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `ide_contrato`, `problema`, `regla` |
| **Gaps** | ❌ `ide_contrato_actual` → `ide_contrato`. ❌ `ide_contrato_deberia` not in engine. Note: uses DIFFERENT key names than odontologia handler (`ide_contrato_deberia` vs `ide_deberia`). |
| **Impact** | 🟡 **Medium** |

### 4.3 Cups Equivalentes (lines 88–109)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `estancia_str`, `accion` |
| **Engine provides** | `factura`, `codigo`, `codigo_equiv` (from `codigo_equiv` field), `procedimiento`, `problema`, `regla` |
| **Gaps** | ❌ `estancia_str` not in engine. ❌ `accion` not in engine; engine provides `problema`. |
| **Impact** | 🟡 **Medium** — `accion`/`estancia_str` missing |

### 4.4 MAL CAPITADO (lines 112–125)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `observacion`, `ide_contrato_actual` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `ide_contrato`, `problema`, `regla` |
| **Gaps** | ❌ `observacion` not in engine (engine has `problema`). ❌ `ide_contrato_actual` → `ide_contrato`. |
| **Impact** | 🟡 **Medium** |

### 4.5 Cantidades (lines 128–153)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `cantidad`, `cantidad_esperada` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `cantidad`, `problema`, `regla` |
| **Gaps** | ❌ `cantidad_esperada` not in engine output (legacy had it from template). `descripcion` uses template with `cantidad_esperada` — will show literal `{cantidad_esperada}`. |
| **Impact** | 🔴 **High** — `cantidad_esperada` missing breaks the description template |

### 4.6 Decimales (lines 155–166)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | Just `factura` (list of strings from `error_groups`) |
| **Legacy format** | `list[str]` |
| **Engine provides** | Engine goes through odontologia path, NOT this one. |
| **Gaps** | `procedimiento` is hardcoded "Vlr. Procedimiento". `detalle` is hardcoded "Vlr. Subsidiado". These are COLUMN HEADERS, not actual values! |
| **Impact** | 🟡 **Medium** — shows misleading info (header text instead of values) |

### 4.7 Tipo Identificación / Edad (lines 168–185)

Same analysis as §3.6. Additionally:
- `descripcion` uses `f"Tipo actual {tipo_actual} debería ser {tipo_deberia}"` — no fallback to `problema`
- If engine provides `tipo_identificacion` (not `tipo_actual`) and no `tipo_deberia`, description will show "Tipo actual  debería ser "
- **Impact**: 🟡 Medium (worse than odontologia because no `problema` fallback)

### 4.8 Profesionales (lines 188–201)

Same as §3.4.
- `detalle` shows `f"Cód: {cod_prof}"` — will show "Cód: " when engine doesn't provide `codigo_profesional`
- **Impact**: 🟡 Medium

### 4.9 Código Entidad vs Afiliación (lines 203–248)

Same as §3.10. Wired correctly.
- **Impact**: 🟢 Low

### 4.10 Tipo Usuario (lines 250–263)

Same as §3.11.
- **Impact**: 🟡 Medium (same key mismatch)

### 4.11 ⚠️ Revisión Necesaria (lines 265–289)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `detalle`, `descripcion`, `problema` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `problema`, `regla` |
| **Gaps** | Uses `descripcion` key (not `problema`) — engine provides `problema`. Fallback to `problema` if `descripcion` empty — OK. |
| **Impact** | 🟢 **Low** |

### 4.12 Copago vs Entidad (lines 291–307)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `entidad_cobrar`, `vlr_copago` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `entidad_cobrar`, `vlr_copago`, `problema`, `regla` |
| **Gaps** | None |
| **Impact** | 🟢 **Low** |

### 4.13 Duplicados Farmacia (lines 309–340)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo_tipo_procedimiento`, `total_pares`, `pares_duplicados` (list of dicts) |
| **Engine provides** | `factura`, `codigo_tipo_procedimiento`, `problema`, `regla`. `total_pares` and `pares_duplicados` not in engine field list. |
| **Gaps** | ❌ `total_pares`, `pares_duplicados` missing from engine. |
| **Impact** | 🔴 **High** — complex structure not supported by engine enrichment |

### 4.14 Cups Sin Contrato (lines 342–358)

Same as §3.12. All keys present.
- **Impact**: 🟢 Low

### 4.15 Cups No CAPITA (lines 360–374)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `codigo`, `procedimiento`, `observacion` |
| **Engine provides** | `factura`, `codigo`, `procedimiento`, `problema`, `regla` |
| **Gaps** | ❌ `observacion` not in engine. Uses `problema`? No — uses `observacion`. |
| **Impact** | 🟡 **Medium** |

### 4.16 Duplicado ID+Código (lines 376–398)

| Aspect | Detail |
|--------|--------|
| **Handler reads** | `factura`, `identificacion`, `codigo`, `procedimiento`, `cantidad_repeticiones`, `facturas` (list) |
| **Engine provides** | `factura`, `identificacion`, `codigo`, `procedimiento`, `problema`, `regla` |
| **Gaps** | ❌ `cantidad_repeticiones` not in engine. ❌ `facturas` (list) not in engine. |
| **Impact** | 🟡 **Medium** — count missing, but works with what's available |

---

## 5. Priority Impact Matrix

| Priority | Handler | Why | Engine gap |
|----------|---------|-----|------------|
| 🔴 **P0** | Ruta Duplicada | `cantidad` and `facturas` list not in engine; `descripcion` breaks | group-by path produces sparse dicts |
| 🔴 **P0** | Cantidades (Urgencias) | `cantidad_esperada` not in engine; `descripcion` template breaks | missing key |
| 🔴 **P0** | Duplicados Farmacia | Complex nested structure (`pares_duplicados` list) not supported | complex structure |
| 🟡 **P1** | Doble Tipo Procedimiento | `tipos` not in engine; `procedimiento` empty | missing aggregation key |
| 🟡 **P1** | IDE Contrato (both) | `ide_deberia`/`ide_contrato_deberia` not in engine; `nota` missing | derived key |
| 🟡 **P1** | Centro Costo (both) | `centro_deberia` not in engine; `procedimiento` empty | derived key |
| 🟡 **P1** | Tipo Identificación / Edad (shared) | `tipo_deberia` inference fragile; no `problema` fallback | derived key |
| 🟡 **P1** | Tipo Usuario (both) | `tipo_actual` key mismatch; hardcoded description; `procedimiento` empty | key name mismatch |
| 🟡 **P1** | Profesionales (both) | `codigo_profesional` not in engine | missing engine field |
| 🟡 **P1** | MAL CAPITADO | `observacion` not in engine; `ide_contrato_actual` key mismatch | key names |
| 🟡 **P1** | Cups Equivalentes | `estancia_str`, `accion` not in engine | missing keys |
| 🟡 **P1** | Cups No CAPITA | `observacion` not in engine | key name |
| 🟡 **P1** | Duplicado ID+Código | `cantidad_repeticiones` not in engine | missing key |
| 🟢 **P2** | Decimales (odontología) | Works, but uses `valores` fallback unnecessarily | minor |
| 🟢 **P2** | Cantidades (odontología) | `procedimiento` shows `tipo_procedimiento` instead of `codigo - procedimiento` | inconsistent column |
| 🟢 **P2** | Tipo Identificación / Edad (odontología) | Age display loses months; `tipo_deberia` fallback works | minor |
| 🟢 **P2** | Decimales (Urgencias) | `procedimiento`/`detalle` show hardcoded header text | misleading |
| 🟢 **P2** | Código Entidad vs Afiliación | Works correctly | none |
| 🟢 **P2** | Cups Sin Contrato | Works correctly | none |
| 🟢 **P2** | Copago vs Entidad | Works correctly | none |
| 🟢 **P2** | ⚠️ Revisión Necesaria | Works correctly | none |

---

## 6. Root Cause Analysis

### 6.1 Three sources of inconsistency

1. **Legacy format variation** — each legacy detector had its own dict format (different key names, different structures). Handlers were written to match each specific format.

2. **Engine enrichment doesn't match legacy key names** — engine uses canonical column names from the Excel sheet (`tipo_identificacion`, `centro_costo`, `ide_contrato`, `codigo_entidad_cobrar`), while legacy detectors used semantic names (`tipo_actual`, `centro_deberia`, `ide_deberia`, `cod_entidad_esperado`).

3. **Group-by rules produce sparse output** — when a rule uses `group_by`, the engine outputs ONLY `factura`, `problema`, `regla`, `severidad`. No row data at all. This is the highest-impact gap.

### 6.2 The common column pattern

The `/procesar` 6-column format has a consistent semantic for columns 5-7:

| Column | What it should show |
|--------|---------------------|
| **Descripción** | `rule.descripcion` or `problema` — the human-readable problem description |
| **Procedimiento (Var1)** | `codigo - procedimiento` — the CUPS code + name (the object being audited) |
| **Detalle (Var2)** | The problematic value(s) — what's wrong / what it should be |

But handlers use these columns inconsistently:
- Some show `codigo - procedimiento` (✔ correct), others show `tipo_procedimiento` or empty string or hardcoded headers
- Some use `problema` for description, others hardcode text, others use `regla`
- Some use `detalle` for the problematic value, others for aggregate data, others for identifying info

---

## 7. Recommendation

### Standardize ALL handlers to use this pattern:

```python
{
    "tipo_error": "<human label>",
    "factura": item.get("factura", ""),
    "fec_factura": _get_fec_factura(item.get("factura", "")),
    "responsable_cierra": _get_responsable(item.get("factura", "")),
    "descripcion": item.get("problema", "") or "<fallback description>",
    "procedimiento": _build_procedimiento(
        item.get("codigo", ""),
        item.get("procedimiento", "")
    ),
    "detalle": "<the problematic value or expected vs actual>",
}
```

**Rules:**
1. **`descripcion`** = `item.get("problema", "")` always. The engine's `problema` field = `rule.descripcion` (the DB-stored human-readable description). Fallback to hardcoded text only when `problema` is empty.
2. **`procedimiento`** = `_build_procedimiento(codigo, procedimiento)` always. If the problem isn't about a specific procedure code (e.g., Ruta Duplicada), use empty string.
3. **`detalle`** = the value that triggered the problem, or "expected X, got Y", or empty if not applicable.
4. **No hardcoded values** in `procedimiento` or `detalle` — those should always reflect actual data.

### Engine-side improvements needed:
1. Add `codigo_profesional` to the engine's row-data enrichment list
2. Ensure all rules that need derived keys (`tipo_deberia`, `centro_deberia`, `ide_deberia`) include them in the condition output or add them to the enrichment path
3. For group-by rules, add a post-processing step that enriches the sparse output with representative row data from the group

### Handlers needing the most work (priority order):

1. Ruta Duplicada — `build_odontologia_normalized_rows` lines 104-119
2. Cantidades (Urgencias) — `build_normalized_rows` lines 128-153
3. Duplicados Farmacia — `build_normalized_rows` lines 309-340
4. Doble Tipo Procedimiento — `build_odontologia_normalized_rows` lines 90-102
5. IDE Contrato (both) — lines 67-85 and 216-231
6. Centro Costo (both) — lines 51-64 and 201-214
7. Tipo Identificación / Edad (shared) — lines 168-185
8. Tipo Usuario (both) — lines 250-263 and 275-288
9. Profesionales (both) — lines 121-136 and 188-201
10. Decimales (Urgencias) — lines 155-166
11. MAL CAPITADO — lines 112-125
12. Cups Equivalentes — lines 88-109
13. Cups No CAPITA — lines 360-374
14. Duplicado ID+Código — lines 376-398
