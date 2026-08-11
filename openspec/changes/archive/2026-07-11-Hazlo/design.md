# Design: Replace centro_costo evaluators with condition trees

## Technical Approach

Convert the 2 black-box evaluators (`CentroCostoCheckEvaluator`, `CentroCostoIntramuralEvaluator`) into AND/OR/NOT condition trees in the `condiciones` table. Each REGLA becomes an atomic sub-tree; all sub-trees combine under an OR root (any violation = MATCH). Constant sets live in the existing `catalogos` table, queried by the already-registered `cat_in` operator.

```
Evaluator (legacy)                     Condition tree (new)
┌─────────────────────┐               ┌──────────────────────┐
│ REGLA1..9 + REVERSE │   ───────►    │ OR(AND(v1),AND(v2)…) │
│ hardcoded in Python │               │ cat_in() reads from  │
│ imports constants   │               │ catalogos DB table   │
└─────────────────────┘               └──────────────────────┘
```

## Architecture Decisions

### Decision 1: Constant sets → existing `catalogos` table + `cat_in`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| New `catalogos` table | Already exists with `CatalogInEvaluator` registered ✅ | **Adopt** — zero infra, existing CRUD API & seed conventions ([`catalogos_service.py`](/app/services/reglas/catalogos_service.py)) |
| JSONB arrays in `reglas.parametros` | Evaluator has no access to rule object (reads `context.invoice_data` where engine merges parametros) ❌ | Rejected |
| Inline arrays in `valor_esperado` | Works for `in`, but centro_costo lists are domain-global, not per-rule | Rejected |

**Rationale**: `catalogos` table with columns `(key, value JSONB, dominio, descripcion)` exists and is populated. `CatalogInEvaluator` (operator `cat_in`) is already registered and queries `SELECT value FROM catalogos WHERE key = :key`. New catalog seeds needed: `codigos_exceptuados`, `centro_costo_pyp`, `centro_costo_quirofano`, `centro_costo_hospitalizacion`, `centros_costo_validos_urgencias`, `centros_costo_pyp_intramural`, `codigos_excluidos_vacunacion`, `codigos_exceptuados_ambulatorio`, `codigos_exceptuados_responsable_urgencias`, `centros_costo_laboratorio_validos`, `codigos_tipo_procedimiento_ambulatorio`, `codigos_tipo_procedimiento_laboratorio`, `centros_costo_validos_intramural`, `facturadores_urgencias`.

### Decision 2: Case-insensitive comparison for `cat_in`

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Modify `CatalogInEvaluator` to normalize like `InEvaluator` | Breaks nothing; all catalog lookups should be case-insensitive | **Adopt** — add `str().strip().upper()` fallback to `.evaluate()`, matching `InEvaluator` behavior |
| Keep case-sensitive | Excel values may differ (e.g., nombres de responsables) | Rejected |

### Decision 3: Tree structure — OR of violations, no top-level NOT

The proposal's `NOT(OR(...))` would invert the result. The engine treats `outcome=True` as MATCH. Each REGLA forward is an AND of (premises AND NOT(conclusion)). All REGLAs combine under OR — any True child = MATCH. Correct encoding:

```
OR(
  AND(eq(cod_tipo,"02"), eq(lab,"No"), NOT(cat_in(exceptuados)), NOT(eq(centro,APOYO_DIAG))),  # REGLA1
  AND(eq(centro,APOYO_DIAG), NOT(AND(eq(cod_tipo,"02"), eq(lab,"No")))),                       # REVERSE1
  AND(eq(cod_tipo,"14"), NOT(eq(centro,TRASLADOS))),                                            # REGLA2
  ...
)
```

### Decision 4: Two rule groups — common (4 domains) + intramural

Rules 27 (equipos_basicos), 28 (odontologia), 29 (urgencias), and hospitalizacion (id 4) use the common set (REGLA1-9 + REVERSE + CENTRO_INVALIDO). The intramural rule adds REGLA3-INTRAMURAL, REGLA6/REVERSE6, REGLA7/REVERSE7, REGLA10/REVERSE10, REGLA_RESPONSABLE_URGENCIAS.

| Rule | Domain | Tree Source |
|------|--------|-------------|
| `centro_costo_hospitalizacion_valido` | hospitalizacion | Common set |
| `centro_costo_equipos_basicos_valido` | equipos_basicos | Common set |
| `centro_costo_odontologia_valido` | odontologia | Common set |
| `centro_costo_urgencias_valido` | urgencias | Common set |
| `centro_costo_intramural_valido` | intramural | Common set (minus REGLA3) + intramural-specific |

## Condition Tree Definitions (pseudocode)

**Common tree** (rules 27, 28, 29, and hospitalizacion):

```
OR(
  AND(eq(invoice.tarifario, "Suminstros, Medicamentos"),
      NOT(eq(invoice.centro_costo, "APOYO TERAPEUTICO-FARMACIA E INSUMOS."))),               # REGLA9
  AND(eq(invoice.codigo_tipo_procedimiento, "02"),
      eq(invoice.laboratorio, "No"),
      NOT(cat_in("codigos_exceptuados", invoice.codigo)),
      NOT(eq(invoice.centro_costo, "APOYO DIAGNOSTICO-IMAGENOLOGIA"))),                       # REGLA1
  AND(eq(invoice.centro_costo, "APOYO DIAGNOSTICO-IMAGENOLOGIA"),
      NOT(AND(eq(invoice.codigo_tipo_procedimiento, "02"),
              eq(invoice.laboratorio, "No")))),                                                # REVERSE1
  AND(eq(invoice.codigo_tipo_procedimiento, "14"),
      NOT(eq(invoice.centro_costo, "TRASLADOS"))),                                            # REGLA2
  AND(eq(invoice.centro_costo, "TRASLADOS"),
      NOT(eq(invoice.codigo_tipo_procedimiento, "14"))),                                      # REVERSE2
  AND(cat_in("centro_costo_pyp", invoice.codigo),
      NOT(eq(invoice.centro_costo, "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"))),              # REGLA3
  AND(eq(invoice.centro_costo, "PROCEDIMIENTO DE PROMOCIÓN Y PREVENCIÓN"),
      NOT(cat_in("centro_costo_pyp", invoice.codigo))),                                       # REVERSE3
  AND(cat_in("centro_costo_quirofano", invoice.codigo),
      NOT(eq(invoice.centro_costo, "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"))),          # REGLA4
  AND(eq(invoice.centro_costo, "QUIRÓFANOS Y SALAS DE PARTO- SALA DE PARTO"),
      NOT(cat_in("centro_costo_quirofano", invoice.codigo))),                                 # REVERSE4
  AND(eq(invoice.centro_costo, "APOYO TERAPEUTICO-FARMACIA E INSUMOS."),
      NOT(eq(invoice.tarifario, "Suminstros, Medicamentos"))),                                # REVERSE9
  AND(cat_in("centro_costo_hospitalizacion", invoice.codigo),
      NOT(eq(invoice.centro_costo, "HOSPITALIZACIÓN - ESTANCIA GENERAL"))),                   # REGLA8
  AND(NOT(cat_in("centros_costo_validos_urgencias", invoice.centro_costo)))                    # CENTRO_INVALIDO
)
```

**Intramural additions** (same as common, without REGLA3/REVERSE3, plus):

```
OR(
  ...common minus REGLA3/REVERSE3...
  AND(cat_in("centro_costo_pyp", invoice.codigo),
      NOT(cat_in("centros_costo_pyp_intramural", invoice.centro_costo))),                     # REGLA3-INTRAMURAL
  AND(cat_in("centros_costo_pyp_intramural", invoice.centro_costo),
      NOT(cat_in("centro_costo_pyp", invoice.codigo))),                                       # REVERSE3-INTRAMURAL
  AND(cat_in("codigos_tipo_procedimiento_laboratorio", invoice.codigo_tipo_procedimiento),
      eq(invoice.laboratorio, "Si"),
      NOT(cat_in("centros_costo_laboratorio_validos", invoice.centro_costo))),                # REGLA10
  AND(cat_in("centros_costo_laboratorio_validos", invoice.centro_costo),
      OR(NOT(cat_in("codigos_tipo_procedimiento_laboratorio", invoice.codigo_tipo_procedimiento)),
         AND(NOT(cat_in("codigos_exceptuados", invoice.codigo)),
             NOT(eq(invoice.laboratorio, "Si"))))),                                           # REVERSE10
  AND(eq(invoice.codigo_tipo_procedimiento, "05"),
      NOT(cat_in("codigos_excluidos_vacunacion", invoice.codigo)),
      NOT(cat_in("centro_costo_pyp", invoice.codigo)),
      NOT(eq(invoice.centro_costo, "SALUD PUBLICA-VACUNACION  REGULAR")),
      NOT(AND(cat_in("codigos_tipo_procedimiento_laboratorio", invoice.codigo_tipo_procedimiento),
              eq(invoice.laboratorio, "Si")))),                                               # REGLA6
  AND(eq(invoice.centro_costo, "SALUD PUBLICA-VACUNACION  REGULAR"),
      OR(NOT(eq(invoice.codigo_tipo_procedimiento, "05")),
         cat_in("codigos_excluidos_vacunacion", invoice.codigo))),                             # REVERSE6
  AND(cat_in("codigos_tipo_procedimiento_ambulatorio", invoice.codigo_tipo_procedimiento),
      NOT(cat_in("codigos_exceptuados_ambulatorio", invoice.codigo)),
      NOT(eq(invoice.centro_costo, "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS"))), # REGLA7
  AND(eq(invoice.centro_costo, "SERVICIOS AMBULATORIOS- CONSULTA EXTERNA Y PROCEDIMIENTOS"),
      NOT(cat_in("codigos_tipo_procedimiento_ambulatorio", invoice.codigo_tipo_procedimiento))),  # REVERSE7
  AND(cat_in("facturadores_urgencias", invoice.responsable_cierra),
      cat_in(invoice.codigo_tipo_procedimiento, ["01", "04"]),
      NOT(cat_in("codigos_exceptuados_responsable_urgencias", invoice.codigo)),
      NOT(cat_in(invoice.centro_costo, ["URGENCIAS", "HOSPITALIZACIÓN - ESTANCIA GENERAL"])))  # RESPONSABLE_URGENCIAS
)
```

## Data Flow

```
Sheet rows ──→ engine.py reads row data ──→ EvaluationContext(invoice_data)
                                                    │
                          condition_evaluator.py ────┤
                              │                      │
                              ▼                      ▼
                   build_tree(condiciones)    providers.resolve("invoice.field")
                              │                      │
                              ▼                      ▼
                   evaluate(tree, ctx) ──→ evaluator.evaluate(row_value, valor_esperado)
                                                    │
                                                    ▼
                                        CatalogInEvaluator ──→ catalogos DB table (via session)
                                        EqEvaluator       ──→ direct comparison
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/engine/evaluators.py` | Modify | Add `.strip().upper()` fallback to `CatalogInEvaluator.evaluate()`; remove `CentroCostoCheckEvaluator` and `CentroCostoIntramuralEvaluator` from `_register_builtins()` |
| `app/services/engine/evaluators.py` | Remove | Delete `CentroCostoCheckEvaluator` class and `CentroCostoIntramuralEvaluator` class |
| `seed/migracion-engine/13_centro_costo_comun.sql` | Create | SQL to create catalogos entries + rebuild rule conditions for rules 4, 27, 28, 29 |
| `seed/migracion-engine/14_centro_costo_intramural.sql` | Create | SQL for intramural rule conditions + its catalogos entries |
| `tests/engine/test_centro_costo_tree.py` | Create | Snapshot equivalence tests comparing evaluator vs tree output |
| `app/services/transversales/centro_costo_rules.py` | Modify | Add `@deprecated` decorator and docstring warning |

## Interfaces / Contracts

**New catalogos keys to seed:**

| key | JSONB value |
|-----|-------------|
| `codigos_exceptuados` | `["194901","23105","23116","232200",…]` (from `CODIGOS_EXCEPTUADOS`) |
| `centro_costo_pyp` | `["990211","890205","890405","861801","39360","29116"]` |
| `centro_costo_quirofano` | `["735301","90DS02","512002","39220"]` |
| `centro_costo_hospitalizacion` | `["890601H","39133"]` |
| `centros_costo_validos_urgencias` | `["URGENCIAS","APOYO TERAPEUTICO-FARMACIA E INSUMOS.",…]` |
| `centros_costo_pyp_intramural` | `["SERVICIOS AMBULATORIOS- PROMOCION Y PREVENCION",…]` |
| `codigos_excluidos_vacunacion` | `["906249PR","906249"]` |
| `codigos_exceptuados_ambulatorio` | `["735301","861101"]` |
| `codigos_exceptuados_responsable_urgencias` | `["735301"]` |
| `centros_costo_laboratorio_validos` | `["APOYO DIAGNOSTICO-LABORATOR CLINICO","APOYO DIAGNOSTICO-LABORATOR CLINICO."]` |
| `codigos_tipo_procedimiento_ambulatorio` | `["03","04"]` |
| `codigos_tipo_procedimiento_laboratorio` | `["02","05"]` |
| `centros_costo_validos_intramural` | `["APOYO DIAGNOSTICO-LABORATOR CLINICO",…]` |
| `facturadores_urgencias` | `["ARIAS CULCHA ANGIE CAROLINA","ESPAÑA DIAZ LORENY ALEJANDRA",…]` |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `CatalogInEvaluator` normalization | 3 cases: exact match, case-different, whitespace-different |
| Equivalence | Each REGLA matches evaluator output for 100+ real rows per domain | Create `EvaluationContext` with real invoice data, run evaluator.evaluate() then tree.evaluate() — assert identical outcomes |
| Snapshot | Full rule output for 3 real Excel files per domain | Run `engine.evaluate_sheet()` with old evaluator → capture MATCH rows. Run with new tree → compare sets are identical |
| Integration | Rules 27,28,29,4 still fire via `evaluate_sheet_domain()` | Same as snapshot but through the full engine pipeline |

## Migration Sequence

1. Seed catalogos entries for all 14 constant sets
2. Add CI fallback to `CatalogInEvaluator.evaluate()`
3. Run equivalence test against evaluator output on real data
4. Deploy SQL migrations to replace condition trees:
   - `DELETE FROM condiciones WHERE regla_id IN (...)`
   - `INSERT INTO condiciones ...` (one OR root + sub-trees)
5. Run snapshot test: before vs after tree output on real Excel files
6. Remove `CentroCostoCheckEvaluator` and `CentroCostoIntramuralEvaluator` from evaluators.py
7. Mark `centro_costo_rules.py` as deprecated

## Rollback Plan

Per REGLA: keep evaluator code in file but commented out (not deleted until prod verification). Rollback via `UPDATE reglas SET version = version + 1, ...` + restore single `centro_costo_check`/`centro_costo_intramural` condition row. No data loss — catalogos seeds are additive.

## Effort Estimate

| Phase | Effort |
|-------|--------|
| Catalog seeds + SQL migrations | 2h |
| CatalogInEvaluator CI fix | 0.5h |
| Equivalence tests | 3h |
| Snapshot tests | 2h |
| Evaluator removal + deprecation | 0.5h |
| **Total** | **8h** |
