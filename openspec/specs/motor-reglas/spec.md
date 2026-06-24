# Motor de Reglas — DB-Backed Rule Engine

## Purpose

Replace hardcoded Python detectors with a DB-backed rule engine. Rules are data (versioned, parametric, domain-scoped) — not code. The engine evaluates condition trees (AND/OR/NOT composites) against row data and returns structured results indistinguishable from legacy detectors.

---

## Requirements

### R1: Domain-Scoped Rule Loading

The Rule Resolver MUST load only rules matching the current processing domain (odontología, urgencias, equipos_basicos). Inactive rules (draft, deprecated without override, retired) SHALL be excluded.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Domain match | 3 active odontología rules, 5 active urgencias rules in DB | resolver loads for odontología | only the 3 odontología rules are returned |
| Draft excluded | 1 draft rule for odontología | resolver loads for odontología | draft rule is NOT in the result set |
| Deprecated with override | deprecated rule with `excepcion` active for this batch | resolver evaluates | rule IS included (overridden by exception) |

### R2: Condition Tree Evaluation

Each rule has a condition tree (AND, OR, NOT composites with atomic leaf comparisons: eq, gt, lt, gte, lte, in, contains, regex). The evaluator MUST traverse the tree depth-first. An AND node with one false child MUST short-circuit. An OR node with one true child MUST short-circuit.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| AND passes | AND(eq(convenio, "A"), gt(valor, 1000)), row has convenio="A", valor=1500 | evaluate | result: MATCH |
| AND fails | same rule, row has convenio="A", valor=500 | evaluate | result: NO_MATCH |
| OR short-circuit | OR(eq(convenio, "A"), expensive_check()), first child true | evaluate | second child never evaluated |
| NOT inverts | NOT(eq(estado, "ANULADO")), row has estado="ACTIVO" | evaluate | result: MATCH |
| Unknown operator | tree has leaf with operator="fuzzy_match" | evaluate | result: ERROR, logged; does NOT crash pipeline |

### R3: Exception Handling

An Exception entity MAY suspend or modify a specific rule for a scope (factura, convenio, periodo, usuario). For suspensions: the rule is excluded from evaluation. For modifications: parameter overrides are injected before evaluation.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Suspension | rule R1 active, exception suspends R1 for convenio "X" | row has convenio="X" | R1 excluded from evaluation for this row |
| Modification | rule R2 with umbral=1000, exception overrides umbral=500 for factura="F001" | row has factura="F001" | R2 evaluates with umbral=500, not 1000 |
| No exception | rule R3, no matching exception | normal evaluation | R3 evaluated as-is |

### R4: Parametric Rules

A rule definition MUST support parameter placeholders (e.g., `{umbral}`). Multiple parameter configurations reference the same rule definition — one rule, many parametrizations. Each parametrization is evaluated independently.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Multi-param | rule "valor > {umbral}" with param configs: [umbral=1000], [umbral=5000] | row with valor=3000 | config1 MATCH, config2 NO_MATCH — both results recorded |
| Default param | rule with no parameter configs | evaluation | rule evaluates with its own default parameters |
| Missing param | rule requires "{umbral}" but param config omits it | evaluation | ERROR — rule skipped, logged |

### R5: Versioning and State Machine (with Auto-Versioning)

Rules MUST have a version (integer, auto-incremented on modification). States SHALL follow: draft → active → deprecated → retired. Only `active` rules are evaluated by default. `deprecated` rules MAY be evaluated when overridden by an active exception.

**AUTO-VERSIONING**: When the REST API (`PUT /api/reglas/<id>`) modifies an active rule, the system SHALL atomically: (1) mark the current version as `deprecated`, (2) create a new version with `estado=active` and `version = previous + 1`. Both operations SHALL be transactional — if either fails, both roll back. Partial updates SHALL be supported (only changed fields in body). If no fields have changed, no new version SHALL be created.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Active only | R1 v3 active, R1 v2 archived | resolver loads | only v3 returned |
| Draft activation | R2 draft → set state=active | next evaluation | R2 is now evaluated |
| Deprecation | R3 active → deprecated | next evaluation | R3 excluded unless exception overrides |
| Retired terminal | R4 retired | any action | R4 cannot transition to any other state |
| **Auto-version on PUT** | R1 v3 active, content changed | `PUT /api/reglas/1` | R1 v3 → deprecated, R1 v4 → active, both persisted atomically |
| **Partial update** | R2 active, only `prioridad` sent | `PUT /api/reglas/2` with `{"prioridad": 5}` | new version created with prioridad=5, other fields unchanged |
| **No-op update** | PUT with same data as current | `PUT /api/reglas/1` | no new version created, old stays active |
| **Rollback** | DB error after deprecating old | `PUT /api/reglas/1` | old rule remains active, no orphan version created |

### R6: Legacy Pipeline Wrapper

A `RuleBasedDetector` wrapper MUST implement the same callable interface as existing Python detectors: `(row: dict) → list[dict]`. `detect_all.py` orchestrators SHALL delegate to this wrapper for migrated detectors. The output format MUST be identical to legacy detectors.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Same interface | legacy detector `detectar_decimales(row)` returns `[{problema, valor}]` | call `RuleBasedDetector("decimales").detect(row)` | identical list-of-dicts output |
| Unmigrated detector unchanged | "duplicados" still uses Python code | `detect_all.py` runs | legacy function called directly, no wrapper |
| Migration toggle | feature flag `USE_RULE_ENGINE=true` | `detect_all.py` runs | migrated detectors use `RuleBasedDetector` |

### R7: Feature Flag Rollback

A configuration flag `USE_RULE_ENGINE` (boolean) MUST control whether migrated detectors use the engine. When `false`, ALL detectors revert to legacy Python code. The flag SHALL be settable via environment variable or config file without redeployment.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Engine on | `USE_RULE_ENGINE=true` | process file | 2-3 migrated detectors use DB-backed engine |
| Engine off | `USE_RULE_ENGINE=false` | process file | ALL detectors use legacy Python code |
| Flag change runtime | flag changed via env var | next `/procesar` request | new flag value respected without server restart |

### R8: Catalog Provider (Phase 2)

The engine MUST provide a `CatalogProvider` that resolves reference data from DB tables during evaluation. Condition expressions SHALL reference catalog entries via dot-path syntax (e.g., `catalog.profesionales[codigo].tipo`). The provider SHALL cache results per evaluation session.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Professional lookup | professional code "OD001" exists in `profesionales` table with tipo="ODONTOLOGO" | condition evaluates `catalog.profesionales["OD001"].tipo == "ODONTOLOGO"` | result: MATCH |
| Missing entry | code "XX999" not in catalog | condition references `catalog.profesionales["XX999"]` | result: NO_MATCH, no error |
| Cache hit | same code queried 50 times in one sheet | second through 50th lookup | DB queried only once, cached result reused |

### R9: Contract Data Provider (Phase 3)

The engine MUST provide a `ContractDataProvider` that resolves contract info — notas técnicas, tarifas, ide_contrato — from DB. It SHALL support path expressions like `contract.nota_tecnica[entidad].tarifa` and `contract.ide_valido[entidad][codigo]`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| IDE validation | entidad "ESS118" has valid IDE set [100, 200] for code "890201" | condition checks `contract.ide_valido["ESS118"]["890201"]` contains row's ide_contrato=100 | result: MATCH |
| Tariff lookup | entidad "ESSC18" has tarifa=5000 in notas técnicas | resolver loads `contract.nota_tecnica["ESSC18"].tarifa` | returns 5000 |
| Month-dependent | RES001 contract changes at month 6 | evaluation month is 4 | pre-June contract data returned |

### R10: Multi-Rule Cascade (Phase 4)

The engine MUST support `evaluate_sheet_domain(domain)` that loads ALL active rules for a domain and evaluates them in priority order. When two rules match the same row, BOTH results SHALL be recorded. Rule priority SHALL be an integer column in the `reglas` table — lower numbers evaluated first.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Priority order | R1 (priority=1) and R2 (priority=2) both match row | evaluate_sheet_domain("urgencias") | R1 result appears before R2 in output |
| Both match | two active rules for same row | evaluate | both results in evidence array |
| Domain isolation | 3 odontología rules + 5 urgencias rules | evaluate for "odontología" | only 3 odontología rules evaluated |

### R11: Age Evaluator (Phase 5)

The engine MUST provide `age_from_dates(fecha_nac, fecha_ref)` returning integer years. The function SHALL handle leap years and date parsing from common formats (YYYY-MM-DD, DD/MM/YYYY).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Age calculation | fecha_nac="2000-06-15", fecha_ref="2024-06-15" | age_from_dates(fecha_nac, fecha_ref) | returns 24 |
| Before birthday | fecha_nac="2000-12-01", fecha_ref="2024-06-15" | age_from_dates | returns 23 |
| Invalid date | fecha_nac="not-a-date" | age_from_dates | returns ERROR, logged, does NOT crash |

### R12: Hours Diff Evaluator (Phase 5)

The engine MUST provide `hours_diff(fecha1, fecha2)` returning hours as float. The function SHALL support date and datetime inputs, always returning positive difference (absolute value).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Same day | fecha1="2024-01-15 08:00", fecha2="2024-01-15 14:30" | hours_diff | returns 6.5 |
| Multi-day | fecha1="2024-01-15", fecha2="2024-01-17" | hours_diff | returns 48.0 |
| Reversed order | fecha1 > fecha2 | hours_diff | returns absolute value, same as if ordered |

### R13: Group-By Evaluator (Phase 6)

The engine SHALL provide a `GroupEvaluator` that pre-scans sheet data, groups rows by a key field, then evaluates rules on each group. It MUST support `group_by(field, function, threshold)` patterns. The motivating case: detect when a factura has more than one distinct `tipo_procedimiento`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Distinct count | factura "F001" has rows with tipo_procedimiento=["02","03","02"] | group_by("factura", distinct_count("tipo_procedimiento"), gt(1)) | result: MATCH (2 distinct values) |
| Single type | factura "F002" has all rows with tipo_procedimiento="02" | same rule | result: NO_MATCH |
| Empty group | factura "F003" has 0 rows in filtered data | group evaluation | group skipped, no error |

### R14: regex_extract Operator (Phase 7)

The engine MUST provide `regex_extract(pattern, field)` that extracts the first capture group from a field. The pattern SHALL be a standard Python/PCRE regex.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Match found | field `codigo_entidad` = "{ESSC18}-123" | regex_extract(r"\{(\w+)\}", codigo_entidad) | returns "ESSC18" |
| No match | field = "no-brackets" | regex_extract(r"\{(\w+)\}", field) | returns NULL |
| Compare result | extracted="ESSC18", Cód Entidad Cobrar="ESSC18" | eq(regex_extract(...), Cód Entidad Cobrar) | result: MATCH |

### R15: exists_in_db Operator (Phase 7)

The engine MUST provide `exists_in_db(table, field, value)` that checks if a value exists in a DB table column. Results SHALL be cached per table per session to avoid repeated queries.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Value exists | code "890201" in `procedimientos_contratados` table | exists_in_db("procedimientos_contratados", "codigo", "890201") | returns true |
| Value missing | code "999999" not in table | exists_in_db | returns false |
| Cache | same table+field queried 200 times | second through 200th call | DB hit once, cache serves rest |

---

## Acceptance Criteria

- [ ] Rule resolver returns only active+matching-domain rules
- [ ] AND/OR/NOT trees evaluate correctly per truth-table tests
- [ ] Exceptions suspend and modify as specified
- [ ] Parametric rule with 3 configs produces 3 independent evaluations
- [ ] Version increment on modification; old version archived, not deleted
- [ ] `RuleBasedDetector` output matches legacy detector output (snapshot tests)
- [ ] `USE_RULE_ENGINE=false` disables all engine code paths
