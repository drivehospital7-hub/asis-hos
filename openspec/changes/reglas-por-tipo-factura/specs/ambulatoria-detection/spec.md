# Ambulatoria Detection Specification

## Purpose

Independent orchestrator for "Ambulatoria" invoices, created as a new package `app/services/ambulatoria/` with its own `detect_all.py` and Ambulatoria-specific detectors extracted from `centro_costo_urgencias.py`.

## Requirements

### R1: Package Structure

Ambulatoria detection MUST live at `app/services/ambulatoria/detect_all.py` with `detect_all_problems_ambulatoria()` orchestrator. Ambulatoria-specific detectors SHALL reside in the same package.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Package exists | deployed code | import `app.services.ambulatoria` | `__init__.py` present, no ImportError |
| Orquestador callable | deployment | `detect_all_problems_ambulatoria(sheet, indices)` | returns `(result_dict, responsables_map)` |

### R2: Detector Scope

Ambulatoria orchestrator MUST detect only Ambulatoria-specific problems: initially Ambulatoria rules extracted from `centro_costo_urgencias.py` split. It MUST NOT execute Hospitalización, Urgencias, or Intramural detectors. Detection scope SHALL grow as new Ambulatoria-specific rules are added.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Ambulatoria-only | Excel with Ambulatoria rows | detection runs | only Ambulatoria detectors + transversals executed |
| Excludes Urgencias | Ambulatoria data | detection runs | `detect_cantidades_urgencias` NOT called |
| Excludes Hosp | Ambulatoria data | detection runs | `detect_hospitalizacion_codes` NOT called |

### R3: Transversal Detectors

Ambulatoria orchestrator SHALL call all transversal detectors: `decimales`, `tipo_documento_edad`, `codigo_entidad_vs_entidad_afiliacion`, `tipo_usuario`. Behavior SHALL match current execution of these detectors from `detect_all_problems_urgencias`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Transversals included | Ambulatoria detection | orchestrator runs | all 4 transversal detectors called |
| Same behavior | same input Excel | run Ambulatoria vs Urgencias transversals | identical output for shared detectors |

### R4: Response Format

Result dictionary MUST use `"area": "ambulatoria"` and maintain the same `problemas` structure. Backward-compatible with frontend — no consumer changes required.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Area key | Ambulatoria detection | result returned | `result["area"] == "ambulatoria"` |
| Same keys | detection complete | inspect `result["problemas"]` | contains `centros_de_costos`, `ide_contrato`, `cups_equivalentes`, `decimales`, `tipo_usuario`, etc. |
| Normalized rows | detection complete | inspect `result["problemas"]["normalizados"]` | 6-column normalized format present |

### R5: Centro Costo Split

Ambulatoria-specific rules from `centro_costo_urgencias.py` MUST be extracted into `ambulatoria/centro_costo_ambulatoria.py`. The detector file SHALL detect centro_costo problems only for "Ambulatoria" rows.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Dedicated file | deployed code | import `app.services.ambulatoria.centro_costo_ambulatoria` | file exists |
| Filters by tipo | Excel with mixed tipos | run Ambulatoria centro_costo | only Ambulatoria rows processed |
| Original excludes Ambulatoria | post-split | `detect_centro_costo_urgencias(sheet, indices)` | no Ambulatoria rules triggered |
