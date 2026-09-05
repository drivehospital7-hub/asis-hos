# Design: Motor de Reglas con Auditoría

## Technical Approach

Replace 19+ hardcoded Python detectors with a DB-backed rule engine that keeps the existing pipeline intact. Rules become data (versioned, parametric, domain-scoped) in PostgreSQL. A `RuleEvaluationEngine` evaluates condition trees (AND/OR/NOT) against row data, records immutable evidence, and returns results indistinguishable from legacy detectors. A `RuleBasedDetector` wrapper exposes the same `(row) → list[dict]` interface. `detect_all.py` orchestrators delegate to the wrapper via feature flag `USE_RULE_ENGINE`. Coexistence between legacy Python and DB-backed detectors during incremental migration.

## Architecture Decisions

| Decision | Option A | Option B | Choice | Rationale |
|----------|----------|----------|--------|-----------|
| Models location | Single `app/models.py` (existing pattern) | New `app/models/` package | **Single file** | Existing app uses `app/models.py` with all SQLAlchemy models. Adding engine models there follows established convention. |
| Engine session | Use Flask `get_db()` generator | Create separate engine session factory | **`get_db()`** | Single session per request avoids dual-transaction complexity. Engine injects session via `EvaluationContext`. |
| Condition tree traversal | Recursive depth-first | Iterative stack-based | **Recursive** | F1 trees are shallow (≤5 levels). Recursive is readable and matches short-circuit semantics directly. Revisit if depth exceeds 20. |
| Evidence batch insert | `session.add_all(records)` + single `flush()` | Per-row `session.add()` + commit | **Batch add_all + flush** | 250 rows × N rules = thousands of evidence rows per batch. Single flush avoids N DB round-trips. |
| Parametric config storage | JSONB column in `reglas` | Separate `parametros` table | **JSONB in `reglas`** | Simpler schema. Query: `SELECT * FROM reglas WHERE estado='active' AND dominio='odontologia'` loads everything in one shot. No join overhead. |
| Seeds migration | Raw SQL seeds file | Alembic migrations | **Raw SQL seeds** | F1 scope — rules are initial seed data, not evolving schema. Alembic added in F2 for schema changes. |

## DB Schema (exact tables)

### `reglas`
| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | SERIAL | PK | Rule identifier |
| `nombre` | VARCHAR(100) | NOT NULL, UNIQUE | Human name (e.g., "valores_decimales") |
| `descripcion` | TEXT | NULL | Rule description |
| `dominio` | VARCHAR(50) | NOT NULL | Domain filter: odontologia, urgencias, equipos_basicos, transveral |
| `estado` | VARCHAR(20) | NOT NULL, DEFAULT 'draft' | State machine: draft → active → deprecated → retired |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Auto-incremented on modification |
| `prioridad` | INTEGER | NOT NULL, DEFAULT 100 | Evaluation order (lower = first) |
| `parametros` | JSONB | NULL | Parametric config: `[{"umbral": 1000}, {"umbral": 5000}]` |
| `parametros_default` | JSONB | NULL | Default params when no configs present |
| `severidad` | VARCHAR(20) | NOT NULL, DEFAULT 'error' | error, warning, info |
| `activo` | BOOLEAN | NOT NULL, DEFAULT TRUE | Soft-delete flag |
| `creado_en` | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `actualizado_en` | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_reglas_dominio_estado` ON (dominio, estado) WHERE activo=true; UNIQUE `uq_reglas_nombre_version` ON (nombre, version).

### `condiciones`
| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | SERIAL | PK | |
| `regla_id` | INTEGER | FK→reglas.id, NOT NULL | Owning rule |
| `padre_id` | INTEGER | FK→condiciones.id, NULL | Self-referencing tree parent; NULL = root |
| `tipo` | VARCHAR(10) | NOT NULL | `composite` (AND/OR/NOT) or `atomic` (eq, gt, lt, gte, lte, in, contains, regex, exists_in_db, date_between) |
| `operador` | VARCHAR(20) | NULL | Logic operator for composite nodes (AND, OR, NOT) or comparison operator for atomic nodes |
| `fuente_datos` | VARCHAR(100) | NULL | Data path for atomic nodes: `invoice.vlr_subsidiado`, `patient.edad` |
| `valor_esperado` | JSONB | NULL | Expected value(s): `1000`, `["A","B","C"]`, `{"min":18,"max":65}` |
| `orden` | INTEGER | NOT NULL, DEFAULT 0 | Child ordering within parent |

**Indexes**: `idx_condiciones_regla_id` ON (regla_id); `idx_condiciones_padre_id` ON (padre_id).

### `excepciones`
| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | SERIAL | PK | |
| `regla_id` | INTEGER | FK→reglas.id, NOT NULL | Target rule |
| `tipo_efecto` | VARCHAR(20) | NOT NULL | `skip` (suspend), `downgrade` (lower severity), `override` (modify params) |
| `condicion_json` | JSONB | NOT NULL | Scope condition: `{"convenio": "Promoción y Prevención"}` |
| `parametros_override` | JSONB | NULL | Override values (used with tipo_efecto=override) |
| `activo` | BOOLEAN | NOT NULL, DEFAULT TRUE | |
| `creado_en` | TIMESTAMP | NOT NULL, DEFAULT NOW() | |
| `expira_en` | TIMESTAMP | NULL | Auto-expiry |

**Index**: `idx_excepciones_regla_activo` ON (regla_id) WHERE activo=true.

### `resultados_auditoria`
| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | SERIAL | PK | |
| `evidencia_id` | INTEGER | FK→evidencias.id, NOT NULL | Links to evidence snapshot |
| `regla_id` | INTEGER | FK→reglas.id, NOT NULL | Rule that produced this result |
| `regla_version` | INTEGER | NOT NULL | Rule version used |
| `factura` | VARCHAR(50) | NOT NULL | Invoice identifier |
| `param_config_id` | INTEGER | NULL | Which param config produced this (0 = default, 1..N = config index) |
| `resultado` | VARCHAR(10) | NOT NULL | PASS, FAIL, NA, ERROR |
| `severidad` | VARCHAR(20) | NOT NULL | error, warning, info |
| `mensaje` | TEXT | NULL | Human-readable detection message |
| `detalles` | JSONB | NULL | Detection specifics (e.g., affected values) |
| `creado_en` | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Indexes**: `idx_resultados_factura` ON (factura); `idx_resultados_regla` ON (regla_id, regla_version).

### `evidencias`
| Column | Type | Constraint | Purpose |
|--------|------|------------|---------|
| `id` | SERIAL | PK | |
| `regla_id` | INTEGER | FK→reglas.id, NOT NULL | |
| `regla_version` | INTEGER | NOT NULL | |
| `dominio` | VARCHAR(50) | NOT NULL | |
| `factura` | VARCHAR(50) | NOT NULL | |
| `param_config_id` | INTEGER | NULL | |
| `outcome` | VARCHAR(10) | NOT NULL | MATCH, NO_MATCH, ERROR |
| `arbol_evaluado` | JSONB | NOT NULL | Per-node trace: `[{node_id, tipo, operador, fuente, valor_real, valor_esperado, result}]` |
| `snapshot_fila` | JSONB | NOT NULL | Row data at evaluation time |
| `snapshot_referencia` | JSONB | NULL | Reference data (contracts, procedure catalog) |
| `error_mensaje` | TEXT | NULL | Error message if outcome=ERROR |
| `creado_en` | TIMESTAMP | NOT NULL, DEFAULT NOW() | |

**Constraint**: CHECK — no UPDATE or DELETE allowed via application-layer guard + DB trigger. **Indexes**: `idx_evidencias_regla` ON (regla_id, regla_version); `idx_evidencias_factura` ON (factura); `idx_evidencias_creado` ON (creado_en).

## Core Interfaces

### AtomicEvaluator (registry)
```python
class AtomicEvaluator(ABC):
    operator: str  # Key for registry lookup

    @abstractmethod
    def evaluate(self, condition: dict, row_value: Any, expected: Any) -> bool: ...

class EqEvaluator(AtomicEvaluator):
    operator = "eq"
    def evaluate(self, condition, row_value, expected):
        return row_value == expected

class GtEvaluator(AtomicEvaluator):
    operator = "gt"
    def evaluate(self, condition, row_value, expected):
        return float(row_value) > float(expected)
```

New evaluators register via `EVALUATOR_REGISTRY["operator_name"] = MyEvaluator()`. UNKNOWN operators → log + return ERROR (never crash).

### ContextProvider (data resolution)
```python
class ContextProvider(ABC):
    @abstractmethod
    def resolve(self, path: str, context: "EvaluationContext") -> Any: ...

class InvoiceProvider(ContextProvider):
    prefix = "invoice"
    def resolve(self, path, context):
        return context.invoice_data.get(path.split(".")[-1])
```

Paths like `invoice.vlr_subsidiado`, `patient.edad` are resolved by matching prefix to provider. New providers register via `PROVIDER_REGISTRY["prefix"] = MyProvider()`.

## RuleEvaluationEngine Core Flow

```
┌──────────────┐    ┌───────────────┐    ┌──────────────┐    ┌─────────────────┐
│ Flask Route  │───▶│ detect_all.py │───▶│RuleBasedDetect│───▶│ RuleEvaluation  │
│ (thin deleg) │◀───│ (orchestrator)│◀───│   or(wrapper) │◀───│     Engine      │
└──────────────┘    └───────────────┘    └──────────────┘    └────────┬───────┘
                                                                      │
  ┌───────────────────────────────────────────────────────────────────┤
  │                                                                   │
  ▼                                                                   ▼
┌───────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────┐
│ 1. LOAD   │  │ 2. RESOLVE   │  │ 3. EVALUATE   │  │ 4. COLLECT & STORE   │
│ Context   │  │ Active rules │  │ Condition     │  │ Evidence + Results   │
│ (invoice  │  │ by domain    │  │ Tree (AND/OR/ │  │ (batch insert)       │
│ +items+   │  │ sorted by    │  │ NOT short-    │  │                      │
│ patient)  │  │ priority     │  │ circuit)      │  │                      │
└───────────┘  └──────────────┘  └───────────────┘  └──────────────────────┘
```

### Sequence Diagram

```
Engine               RuleResolver        ConditionTree        ExceptionHandler     EvidenceCollector
  │                       │                    │                     │                    │
  │─load_context()───────▶│                    │                     │                    │
  │                       │─SELECT * FROM      │                     │                    │
  │                       │  reglas WHERE       │                     │                    │
  │                       │  dominio=X AND      │                     │                    │
  │                       │  estado='active'    │                     │                    │
  │                       │  ORDER BY prioridad │                     │                    │
  │◀──rules[]─────────────│                    │                     │                    │
  │                       │                    │                     │                    │
  │  FOR EACH rule:       │                    │                     │                    │
  │──check_exceptions()─────────────────────────────────────────────▶                    │
  │◀──(skip|override)─────────────────────────────────────────────────│                    │
  │                       │                    │                     │                    │
  │──evaluate(rule, ctx)──────────────────────▶│                     │                    │
  │                       │                    │─SELECT * FROM       │                    │
  │                       │                    │  condiciones WHERE  │                    │
  │                       │                    │  regla_id=X ORDER   │                    │
  │                       │                    │  BY padre_id, orden │                    │
  │                       │                    │                     │                    │
  │                       │                    │─traverse(root):     │                    │
  │                       │                    │  AND: all children? │                    │
  │                       │                    │  OR: any child?     │                    │
  │                       │                    │  atomic: resolve    │                    │
  │                       │                    │    value → eval     │                    │
  │◀──result + trace──────│                    │                     │                    │
  │                       │                    │                     │                    │
  │──record_evidence()─────────────────────────────────────────────────────────────────▶
  │                       │                    │                     │                    │
  │                       │                    │                     │    session.add_all()
  │                       │                    │                     │    session.flush()
```

## Wrapper Integration

### RuleBasedDetector contract
```python
# app/services/engine/wrapper.py
class RuleBasedDetector:
    """Wrapper que expone la misma interfaz que los detectores legacy."""

    def __init__(self, rule_name: str, session: Session):
        self._rule_name = rule_name
        self._engine = RuleEvaluationEngine(session)

    def detect(self, data_sheet: Worksheet, indices: dict) -> list[dict]:
        """Same signature as legacy detectors. Returns list of problem dicts."""
        return self._engine.evaluate_sheet(rule_name=self._rule_name,
                                           data_sheet=data_sheet,
                                           indices=indices)
```

### detect_all.py integration pattern
```python
# In detect_all.py — migrated detectors use wrapper, not direct function call
USE_RULE_ENGINE = os.getenv("USE_RULE_ENGINE", "false").lower() == "true"

if USE_RULE_ENGINE:
    from app.services.engine.wrapper import RuleBasedDetector
    from app.database import get_session
    session = get_session()
    decimales = RuleBasedDetector("valores_decimales", session).detect(data_sheet, indices)
else:
    from app.services.transversales.decimales import detect_decimales
    decimales = detect_decimales(data_sheet, indices)
```

## Migration Strategy

### Phase 1: Candidate Selection (2-3 detectors)

| Detector | Complexity | Why selected |
|----------|-----------|--------------|
| `decimales` | Atomic (single condition) | Exercises simple evaluator, data provider, evidence recording end-to-end. Quick win. |
| `ruta_duplicada` | Composite (3 conditions: convenio=PyP AND count≥threshold AND patient_id not null) | Exercises AND tree, parametric threshold, data aggregation. |
| `tipo_documento_edad` | Composite with DB lookup | Exercises exists_in_db evaluator (patient age vs document type rules). |

### Phase 2: Condition Tree Mapping

For each migrated detector, map current logic to condition tree rows in `condiciones`:

- **decimales**: AND(eq(vlr_subsidiado_has_decimals, false), eq(vlr_procedimiento_has_decimals, false)) → IF either has decimals → FAIL
- **ruta_duplicada**: AND(eq(convenio_facturado, "Promoción y Prevención"), gte(factura_count, {umbral}))
- **tipo_documento_edad**: OR(age_group_mismatch_violations...) — composite with DB-backed checks

### Phase 3: Snapshot Tests

```python
# tests/engine/test_migration_snapshots.py
def test_decimales_identical_output(legacy_excel, engine):
    legacy_result = detect_decimales(legacy_excel.sheet, legacy_excel.indices)
    engine_result = RuleBasedDetector("valores_decimales", session).detect(
        legacy_excel.sheet, legacy_excel.indices
    )
    assert engine_result == legacy_result
```

Run against production Excel files before enabling engine in production.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/models.py` | Modify | Add Regla, Condicion, Excepcion, ResultadoAuditoria, Evidencia models |
| `app/services/engine/__init__.py` | Create | Engine package |
| `app/services/engine/evaluators.py` | Create | Registry + built-in evaluators (eq, gt, lt, gte, lte, in, contains, regex, exists_in_db, date_between) |
| `app/services/engine/providers.py` | Create | Registry + providers (invoice, patient, contract) |
| `app/services/engine/resolver.py` | Create | RuleResolver: loads active rules by domain |
| `app/services/engine/evaluator.py` | Create | ConditionTree: recursive tree traversal with short-circuit |
| `app/services/engine/exceptions.py` | Create | ExceptionHandler: skip/downgrade/override logic |
| `app/services/engine/evidence.py` | Create | EvidenceCollector: builds tree trace + batch insert |
| `app/services/engine/engine.py` | Create | RuleEvaluationEngine: orchestrates the full flow |
| `app/services/engine/wrapper.py` | Create | RuleBasedDetector with legacy-compatible interface |
| `app/services/engine/context.py` | Create | EvaluationContext dataclass (invoice_data, patient_data, reference_data) |
| `app/services/odontologia/detect_all.py` | Modify | Add feature-flag integration for migrated detectors |
| `app/services/transversales/decimales.py` | Modify | Add migration note (detector now also in DB) |
| `app/services/transversales/ruta_duplicada.py` | Modify | Add migration note |
| `app/constants/base.py` | Modify | Add ENGINE_DOMAINS, DEFAULT_SEVERITY constants |
| `seeds/` | Create | SQL seeds for initial rules, conditions, exceptions |
| `tests/engine/` | Create | Engine tests: evaluators, tree traversal, resolver, evidence |
| `tests/engine/test_migration_snapshots.py` | Create | Identity tests: legacy vs engine output |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Each AtomicEvaluator (eq, gt, lt, etc.) | Parametrized pytest: input values → expected boolean |
| Unit | ConditionTree: AND/OR/NOT truth tables | All 8 combos for AND, OR, NOT with short-circuit assertions |
| Unit | RuleResolver: domain filter, state exclusion | Given seed rules → assert loaded set |
| Unit | ExceptionHandler: skip, override, downgrade | Given rule + matching exception → assert effect |
| Integration | engine.evaluate_sheet() with seed rules | Load test Excel → assert problems match expected |
| Integration | Evidence immutability | Assert no UPDATE/DELETE after evaluate_sheet |
| Snapshot | Migrated detector output = legacy output | Side-by-side comparison with production Excel files |

## Open Questions

- [ ] Should `evidencias.arbol_evaluado` use a nested JSON structure or a flat array of node results? Flat array (shown above) is simpler for querying; nested mirrors the tree structure. **Recommend flat array with `padre_id` references.**
- [ ] DB trigger for immutability vs. application-layer guard? Trigger is stronger but adds deployment dependency. Application-layer guard fits F1 deployment model (no DBA needed). **Recommend application-layer guard + CHECK constraint in F1; trigger in F2.**
- [ ] Seed file format: raw SQL vs Python script? Raw SQL is simpler for initial load. Python script if we need conditional logic. **Recommend raw SQL for F1.**
