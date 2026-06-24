# Phase 1 Rules Specification

## Purpose

Five row-by-row detectors migrated from legacy Python to DB-backed engine rules. These are the simplest rules, acting as validation gates for migration infrastructure before tackling complex group-by and cross-reference rules.

## Requirements

### R1: cups_equivalentes — Code Substitution Detection

The rule MUST detect CUPS codes with known equivalents. When a row's `codigo_cups` matches a mapping in `code_mappings`, the engine SHALL emit a substitution evidence with both original and equivalent codes.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Global substitution | row has codigo_cups="906317", mapping 906317→1906317 exists | rule evaluates | evidence: {problema: "cups_equivalente", original: "906317", equivalente: "1906317"} |
| Entity-specific | row has codigo="890205", entidad="ESS118", mapping exists for (890205, ESS118) | rule evaluates | evidence emitted with entity-scoped substitution |
| No mapping | row has codigo="999999" not in mappings | rule evaluates | NO_MATCH, no evidence |

### R2: revision_entidad_86 — Entity 86 Review Flag

The rule MUST flag rows where `entidad` equals "86" for manual review. This is a simple equality check: when entidad == "86", the engine SHALL emit a revision evidence.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Entity 86 detected | row has entidad="86" | rule evaluates | evidence: {problema: "revision_entidad_86", entidad: "86"} |
| Other entity | row has entidad="ESS118" | rule evaluates | NO_MATCH |
| Entity empty | row has entidad="" or NULL | rule evaluates | NO_MATCH |

### R3: cantidades_urgencias — Urgency Code Quantity Limits

The rule MUST enforce that urgency-specific codes have `cantidad ≤ 1`. The code set SHALL be loaded from `parametros_sistema` key `URGENCIAS_CODIGOS_CANTIDAD_MAX_1`. When a row's code is in that set AND cantidad > 1, the engine SHALL emit a violation.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Code in set, qty > 1 | row has codigo="C8901" (in list), cantidad=3 | rule evaluates | evidence: {problema: "cantidad_urgencias_excedida", codigo: "C8901", cantidad: 3} |
| Code in set, qty = 1 | same code, cantidad=1 | rule evaluates | NO_MATCH |
| Code NOT in set | row has codigo="XYZ99" (not in list), cantidad=5 | rule evaluates | NO_MATCH (code not restricted) |

### R4: cantidades_soat_urgencias — SOAT-Specific Quantity Limits

The rule MUST flag rows where `Tarifario="SOAT"` AND dominio is urgencias AND codigo is in the restricted set AND cantidad ≠ 1. The restricted code set SHALL use the same `URGENCIAS_CODIGOS_CANTIDAD_MAX_1` constant.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| SOAT + restricted code + qty > 1 | Tarifario="SOAT", codigo="C8901", cantidad=2 | rule evaluates | evidence: {problema: "cantidad_soat_urgencias", tarifario: "SOAT"} |
| SOAT + restricted code + qty = 0 | Tarifario="SOAT", codigo="C8901", cantidad=0 | rule evaluates | MATCH (cantidad ≠ 1) |
| Not SOAT | Tarifario="ISS", codigo="C8901", cantidad=3 | rule evaluates | NO_MATCH (SOAT condition unmet) |

### R5: mal_capitado — Incorrect Capitation Detection

The rule MUST detect two mal-capitado patterns: (1) codes G03XB01 or A02BB01 with factura NOT prefixed "FEV", (2) factura prefixed "CAP" with entidad NOT "ESS118". Both SHALL use the `startswith` engine operator introduced in Phase 5. Before Phase 5 delivery, a temporary `contains`-based implementation MAY be used.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Pattern 1: code requires FEV | codigo="G03XB01", factura="ABC-123" (not FEV*) | rule evaluates | evidence: {problema: "mal_capitado_codigo_fev", codigo: "G03XB01"} |
| Pattern 1: correct prefix | codigo="G03XB01", factura="FEV-456" | rule evaluates | NO_MATCH for pattern 1 |
| Pattern 2: CAP requires ESS118 | factura="CAP-789", entidad="ESS062" | rule evaluates | evidence: {problema: "mal_capitado_entidad_cap", entidad: "ESS062"} |
| Pattern 2: correct entity | factura="CAP-789", entidad="ESS118" | rule evaluates | NO_MATCH for pattern 2 |
