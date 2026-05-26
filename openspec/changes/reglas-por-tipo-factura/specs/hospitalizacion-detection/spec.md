# Hospitalización Detection Specification

## Purpose

Independent orchestrator for "Hospitalización" invoices, extracting detectors currently mixed into `app/services/urgencias/` into a dedicated package `app/services/hospitalizacion/`.

## Requirements

### R1: Package Structure

Hospitalización detection MUST live at `app/services/hospitalizacion/detect_all.py` with its own `detect_all_problems_hospitalizacion()` orchestrator. Detectors specific to Hospitalización SHALL reside in the same package — not in `urgencias/`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Package exists | deployed code | import `app.services.hospitalizacion` | `__init__.py` present, no ImportError |
| Orquestador callable | deployment | `detect_all_problems_hospitalizacion(sheet, indices)` | returns `(result_dict, responsables_map)` |
| No urgencias coupling | Hospitalización detection | review imports | no imports from `app.services.urgencias` |

### R2: Detector Scope

Hospitalización orchestrator MUST detect only Hospitalización-specific problems: `cantidades_hospitalizacion`, `cantidades_soat_hospitalizacion`, `hospitalizacion_codes`, and Hospitalización-only rules from `centro_costo_urgencias` (split per tipo_factura). It MUST NOT execute Urgencias, Intramural, or Ambulatoria detectors.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Includes cantidades_hosp | Excel with Hospitalización rows | detection runs | `detect_cantidades_hospitalizacion` called |
| Includes hosp codes | Excel with Hospitalización rows | detection runs | `detect_hospitalizacion_codes` called |
| Excludes Urgencias | Excel with Hospitalización rows | detection runs | `detect_cantidades_urgencias` NOT called |
| Excludes sala_observacion | Hospitalización data | detection runs | `detect_sala_observacion` NOT called |

### R3: Transversal Detectors

Hospitalización orchestrator SHALL call all transversal detectors: `decimales`, `tipo_documento_edad`, `codigo_entidad_vs_entidad_afiliacion`, `tipo_usuario`. Behavior identical to current `detect_all_problems_urgencias`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Transversals included | Hospitalización detection | orchestrator runs | all 4 transversal detectors called |
| Same behavior | same input Excel | run Hospitalización vs Urgencias transversals | identical output for shared detectors |

### R4: Response Format

Result dictionary MUST use `"area": "hospitalizacion"` and maintain the same `problemas` sub-structure keys (`centros_de_costos`, `ide_contrato`, `cups_equivalentes`, `decimales`, etc.). No change to current response shape — backward-compatible with frontend.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Area key | Hospitalización detection | result returned | `result["area"] == "hospitalizacion"` |
| Same keys | detection complete | inspect `result["problemas"]` | contains `centros_de_costos`, `ide_contrato`, `cups_equivalentes`, `decimales`, etc. |
| Normalized rows | detection complete | inspect `result["problemas"]["normalizados"]` | 6-column normalized format present |

### R5: Centro Costo Split

Rules from `centro_costo_urgencias.py` that apply to "Hospitalización" tipo_factura MUST be extracted into `hospitalizacion/centro_costo_hospitalizacion.py`. The original file SHALL not execute Hospitalización rules after the split.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Dedicated file | deployed code | import `app.services.hospitalizacion.centro_costo_hospitalizacion` | file exists |
| Original excludes Hosp | post-split | `detect_centro_costo_urgencias(sheet, indices)` on Hospitalización row | no Hospitalización rules triggered |
