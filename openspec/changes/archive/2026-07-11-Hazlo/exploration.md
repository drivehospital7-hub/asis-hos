## Exploration: Centro Costo Black-Box Evaluators — Technical Debt Analysis

### Current State

**The Problem.** Three DB-backed rules (IDs 27, 28, 29) and a fourth (ID 4) all use the `centro_costo_check` evaluator, which is an opaque black box that ignores the engine's condition tree contract entirely.

**How it works today:**

```
reglas table                           condiciones table
┌──────────────────────────┐           ┌────────────────────────────────────┐
│ Rule #27 equipos_basicos │ ────────► │ atomic, centro_costo_check,       │
│ Rule #28 odontologia     │ ────────► │ invoice.centro_costo,             │
│ Rule #29 urgencias       │ ────────► │ valor_esperado=NULL               │
│ Rule #4 hospitalizacion  │ ────────► │                                   │
└──────────────────────────┘           └────────────────────────────────────┘
                                                │
                                                ▼
                               CentroCostoCheckEvaluator.evaluate()
                               ┌────────────────────────────────────┐
                               │ Ignores row_value (centro_costo)   │
                               │ Ignores valor_esperado (NULL)      │
                               │ Reads ALL fields from context:     │
                               │  • centro_costo                    │
                               │  • codigo                          │
                               │  • codigo_tipo_procedimiento       │
                               │  • laboratorio                     │
                               │  • tarifario                       │
                               │ Then applies 10+ hardcoded rules   │
                               │ (REGLA1-9 + REVERSE)               │
                               └────────────────────────────────────┘
```

**Hardcoded business rules inside CentroCostoCheckEvaluator:**

| Rule | Logic | Forward | Reverse |
|------|-------|---------|---------|
| REGLA1 | cod_tipo=diagnóstico + Lab=NO → centro=APOYO_DIAG | ✅ | ✅ (centro→cod+lab) |
| REGLA2 | cod_tipo=traslados → centro=TRASLADOS | ✅ | ✅ |
| REGLA3 | código in PYP → centro=PYP | ✅ | ✅ |
| REGLA4 | código in QUIRÓFANO → centro=QUIRÓFANO | ✅ | ✅ |
| REGLA8 | código in HOSPITALIZACIÓN → centro=HOSPITALIZACIÓN | ✅ | ❌ |
| REGLA9 | tarifario=farmacia → centro=FARMACIA | ✅ | ✅ (reverse) |

**Intramural variant (CentroCostoIntramuralEvaluator)** removes REGLA3/REVERSE3 and adds 5 specific rules (REGLA3-INTRAMURAL, REGLA6/REVERSE6, REGLA7/REVERSE7, REGLA10/REVERSE10, REGLA_RESPONSABLE_URGENCIAS). ~70% code duplication with the base evaluator.

**Legacy duplication:** `apply_common_centro_costo_rules()` in `app/services/transversales/centro_costo_rules.py` contains the exact same logic as the evaluator — a second source of truth that must be kept in sync manually.

**`rule.parametros` JSONB usage today:**
- Column exists on `reglas` table, currently `NULL` for all centro_costo rules
- Engine merges `rule.parametros` into `invoice_data` before evaluation (engine.py:111-115)
- Used by group-by rules for `group_by`, `aggregations`, `filter_field`, `filter_value`
- No evaluator currently reads parametros for business logic configuration
- Evaluators only receive `condition, row_value, valor_esperado, context` — they don't have direct access to the rule object

### Affected Areas

| File | Role |
|------|------|
| `app/services/engine/evaluators.py` | Contains `CentroCostoCheckEvaluator` (lines 570-640) and `CentroCostoIntramuralEvaluator` (lines 643-804) |
| `app/services/transversales/centro_costo_rules.py` | Legacy `apply_common_centro_costo_rules()` — duplicate logic mirroring the evaluator |
| `app/services/intramural/centro_costo_intramural.py` | Legacy `detect_centro_costo_intramural()` — duplicate logic for intramural variant |
| `app/services/engine/engine.py` | Engine merges `rule.parametros` into context — potential config injection point |
| `app/services/engine/condition_evaluator.py` | Tree evaluator — would need changes if splitting into condition trees |
| `seed/migracion-engine/03_centro_costo_hospitalizacion_valido.sql` | Migration pattern for centro_costo rules |
| `seed/migracion-engine/05_centro_costo_intramural_valido.sql` | Migration pattern for intramural variant |
| `app/models.py` | `Regla.parametros` (JSONB) — already exists, `NULL` for centro_costo rules |
| `app/services/intramural/detect_all.py` | Wires legacy intramural centro_costo detector (line 242) |

### Approaches

1. **Split evaluator into individual condition-tree rules** — Replace the black-box evaluator with proper AND/OR/NOT condition trees in the `condiciones` table. Each REGLA becomes one or more condition nodes.
   - **Pros**: Full transparency — business rules visible in `condiciones` table; no Python code changes needed for rule modifications; proper use of `valor_esperado` and `fuente_datos`; each rule independently testable; eliminates duplication with legacy code
   - **Cons**: Complex tree design (conditional implications need `NOT(P) OR Q` encoding); constant lists (CODIGOS_PYP, etc.) are Python-internal and would need DB migration to `catalogos` table for `cat_in` evaluator; ~22+ condition rows per rule; cross-field logic is harder to express in the tree model; would need to re-evaluate behavior is identical
   - **Effort**: High (est. 3-5 days for design + migration + testing + verification of behavioral equivalence)

2. **Parametrize evaluator via `rule.parametros` JSONB** — Keep the evaluator as Python code but make it configurable. Store active REGLAs, constant overrides, or domain-specific tuning in `rule.parametros`. The evaluator reads config from `context.invoice_data` (where engine merges parametros).
   - **Pros**: Minimal code changes to evaluator; existing behavior preserved unchanged; each rule can enable/disable specific REGLAs via JSONB; `parametros` infrastructure already exists; backward compatible (NULL = all rules enabled); can also accept constant list overrides
   - **Cons**: Business rules remain in Python code (hidden from SQL queries); does NOT eliminate duplication with legacy `centro_costo_rules.py`; `fuente_datos` and `valor_esperado` remain vestigial; parametros only configures — doesn't express business logic
   - **Effort**: Low-Medium (est. 1-2 days for evaluator refactor + parametros schema + migration SQL + tests)

3. **Keep as-is but document the debt** — Leave the evaluator unchanged. Add clear docstrings and a TECH_DEBT.md entry explaining the anti-pattern.
   - **Pros**: Zero code changes; zero risk of introducing bugs; works correctly today
   - **Cons**: Technical debt accumulates; each new centro_costo rule requires Python changes; duplication continues; contract lies (`fuente_datos` says one field, evaluator reads five); another developer must understand the evaluator internals to modify rules
   - **Effort**: None (just documentation)

### Recommendation

**Approach 2 (parametrize via `rule.parametros` JSONB) as the immediate step, with a migration path to Approach 1 in a future change.** Here's why:

1. **Pragmatism.** The centro_costo rules involve complex conditional logic (implications with forward/reverse checks across multiple fields). Encoding these in the condition tree requires composite AND/OR/NOT trees with `NOT(P) OR Q` patterns — which is technically correct but hard to audit. Python is the right language for this kind of logic.

2. **Incremental de-duplication.** With parametros, we can:
   - Make the evaluator read `context.invoice_data.get("__reglas_activas__")` to know which REGLAs to apply per rule
   - This means each domain's rule (odontologia, urgencias, equipos_basicos, hospitalizacion) would explicitly declare which REGLAs apply via JSONB
   - Eventually merge `CentroCostoCheckEvaluator` and `CentroCostoIntramuralEvaluator` into a single parametrized evaluator

3. **Minimal risk.** The engine already merges `parametros` into `context.invoice_data`. The evaluator already reads from `context.invoice_data`. The change is additive — add parametros parsing, keep backward compatibility when parametros is NULL.

4. **Documentation gap filled.** Once parametros lists the active REGLAs for each rule, querying `SELECT parametros FROM reglas WHERE id IN (4,27,28,29)` tells you exactly what business rules apply — solving the transparency problem.

**Suggested parametros schema:**
```json
{
  "reglas_activas": ["REGLA1", "REVERSE1", "REGLA2", "REVERSE2", "REGLA3", "REVERSE3", "REGLA4", "REVERSE4", "REGLA8", "REGLA9", "REVERSE9"]
}
```

For Intramural:
```json
{
  "reglas_activas": ["REGLA1", "REVERSE1", "REGLA2", "REVERSE2", "REGLA4", "REVERSE4", "REGLA8", "REGLA9", "REVERSE9", "REGLA3_INTRAMURAL", "REVERSE3_INTRAMURAL", "REGLA6", "REVERSE6", "REGLA7", "REVERSE7", "REGLA10", "REVERSE10", "REGLA_RESPONSABLE_URGENCIAS"]
}
```

**What to tell the Proposer to propose:**
- Refactor `CentroCostoCheckEvaluator` and `CentroCostoIntramuralEvaluator` into a single parametrized evaluator
- Define an `active_rules` configuration in parametros JSONB
- Create migration SQL to populate parametros for rules 4, 27, 28, 29 (centro_costo_check) and the intramural rule
- Keep backward compatibility: NULL parametros = all rules active (no migration required for existing rows, just add parametros on next edit)
- Do NOT delete legacy `centro_costo_rules.py` yet — mark as deprecated after evaluator tests pass

### Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Behavioral drift between parametrized evaluator and original | Low | Keep the original evaluator method as the default path when parametros is NULL; add integration tests that compare parametrized vs. original output on real Excel data |
| parametros schema changes needed later | Medium | Future-proof by using a versioned config key (`"v1": {...}`) inside parametros |
| Intramural evaluator shares ~70% code but diverges in subtle ways | Medium | Step 1: extract common rule dict into a class-level constant; Step 2: parametrize which rules fire; the Intramural-specific rules (REGLA6/7/10, RESPONSABLE_URGENCIAS) need `codigo_tipo_procedimiento` which the base evaluator already reads — no gap |
| Legacy code deleted prematurely | Low | Keep centro_costo_rules.py until the engine path has been tested in production for at least one cycle |
| Business owners add new REGLAs via JSONB without understanding evaluator | Low | New rules still require Python code — parametros only controls which rules are **active**, not their logic. Document this boundary clearly. |

### Ready for Proposal

**Yes.** The exploration is complete. Key findings for the proposer:

- There are **two duplicated evaluators** (check + intramural) that should be unified
- **`rule.parametros` JSONB** is the correct hook for configuration — infrastructure already exists in the engine
- The fundamental tension: Python is the right language for complex conditional logic, but the result should be explicitly configured per-rule
- **Approach 2 is recommended** (parametrize via JSONB) as the pragmatic step, with Approach 1 as future work
- Legacy `centro_costo_rules.py` should NOT be deleted yet — mark as deprecated after the parametrized evaluator is verified
- Critical constraint: evaluators don't have direct access to `rule.parametros` — they read from `context.invoice_data` which the engine has already merged with parametros. This is the injection mechanism.
