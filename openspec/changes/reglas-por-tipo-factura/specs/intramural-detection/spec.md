# Intramural Detection Specification

## Purpose

Independent orchestrator for "Intramural" invoices, created as a new package `app/services/intramural/` with its own `detect_all.py` and Intramural-specific detectors extracted from `centro_costo_urgencias.py`.

## Requirements

### R1: Package Structure

Intramural detection MUST live at `app/services/intramural/detect_all.py` with `detect_all_problems_intramural()` orchestrator. Intramural-specific detectors SHALL reside in the same package.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Package exists | deployed code | import `app.services.intramural` | `__init__.py` present, no ImportError |
| Orquestador callable | deployment | `detect_all_problems_intramural(sheet, indices)` | returns `(result_dict, responsables_map)` |

### R2: Detector Scope

Intramural orchestrator MUST detect only Intramural-specific problems: initially Intramural rules extracted from `centro_costo_urgencias.py` split. It MUST NOT execute Hospitalización, Urgencias, or Ambulatoria detectors. Detection scope SHALL grow as new Intramural-specific rules are added in future changes.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Intramural-only | Excel with Intramural rows | detection runs | only Intramural detectors + transversals executed |
| Excludes Urgencias | Intramural data | detection runs | `detect_cantidades_urgencias` NOT called |
| Excludes Hosp | Intramural data | detection runs | `detect_cantidades_hospitalizacion` NOT called |

### R3: Transversal Detectors

Intramural orchestrator SHALL call all transversal detectors: `decimales`, `tipo_documento_edad`, `codigo_entidad_vs_entidad_afiliacion`, `tipo_usuario`. Behavior SHALL match current execution of these detectors from `detect_all_problems_urgencias`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Transversals included | Intramural detection | orchestrator runs | all 4 transversal detectors called |
| Same behavior | same input Excel | run Intramural vs Urgencias transversals | identical output for shared detectors |

### R4: Response Format

Result dictionary MUST use `"area": "intramural"` and maintain the same `problemas` structure. Backward-compatible with frontend — no consumer changes required.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Area key | Intramural detection | result returned | `result["area"] == "intramural"` |
| Same keys | detection complete | inspect `result["problemas"]` | contains `centros_de_costos`, `ide_contrato`, `cups_equivalentes`, `decimales`, `tipo_usuario`, etc. |
| Normalized rows | detection complete | inspect `result["problemas"]["normalizados"]` | 6-column normalized format present |

### R5: Centro Costo Split

Intramural-specific rules from `centro_costo_urgencias.py` MUST be extracted into `intramural/centro_costo_intramural.py`. The detector file SHALL detect centro_costo problems only for "Intramural" rows.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Dedicated file | deployed code | import `app.services.intramural.centro_costo_intramural` | file exists |
| Filters by tipo | Excel with mixed tipos | run Intramural centro_costo | only Intramural rows processed |
| Original excludes Intramural | post-split | `detect_centro_costo_urgencias(sheet, indices)` | no Intramural rules triggered |
