# Delta for Motor de Reglas

## ADDED Requirements

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
