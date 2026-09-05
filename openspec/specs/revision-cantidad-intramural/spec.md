# Revisión Cantidad Intramural — Specification

## Purpose

Detect anomalously high `Cantidad` values in Intramural rows using area-specific thresholds. Flags items as "⚠️ Revisión Necesaria" — this is a signal for manual review, not a definitive error.

---

## Requirements

### R1: Rule Cascade

The system MUST evaluate every data row and apply the first matching rule in the cascade: (1) 02+Lab=No, (2) 03/04, (3) general. The first match SHALL determine the threshold.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| 02+Lab=No exceeds threshold | `Código Tipo Procedimiento` = "02", `Laboratorio` = "No", `Cantidad` = 5 | detector runs | row flagged as revision |
| 02+Lab=No within threshold | `Cantidad` = 2 | detector runs | row NOT flagged |
| 03 exceeds threshold | `Código Tipo Procedimiento` = "03", `Cantidad` = 15 | detector runs | row flagged as revision |
| 04 within threshold | `Código Tipo Procedimiento` = "04", `Cantidad` = 8 | detector runs | row NOT flagged |
| General exceeds threshold | `Código Tipo Procedimiento` = "01", `Cantidad` = 3 | detector runs | row flagged as revision |
| General within threshold | `Cantidad` = 1 | detector runs | row NOT flagged |

### R2: Threshold 02+Lab=No

If `Código Tipo Procedimiento` = "02" AND `Laboratorio` = "No", then `Cantidad` MUST be ≤ 2. If > 2, the system SHALL flag the row.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Flagged | 02 + Lab=No, Cantidad = 3 | detector runs | flagged |
| Not flagged | 02 + Lab=No, Cantidad = 2 | detector runs | not flagged |

### R3: Threshold 03/04

If `Código Tipo Procedimiento` = "03" or "04", then `Cantidad` MUST be ≤ 12. If > 12, the system SHALL flag the row.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Flagged | tipo 03, Cantidad = 13 | detector runs | flagged |
| Not flagged | tipo 04, Cantidad = 12 | detector runs | not flagged |

### R4: General Threshold

For any other case, `Cantidad` MUST be ≤ 1. If > 1, the system SHALL flag the row.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Flagged | tipo 06, Cantidad = 2 | detector runs | flagged |
| Not flagged | tipo 06, Cantidad = 1 | detector runs | not flagged |

### R5: No Tipo Factura Filter

The detector SHALL process ALL rows without filtering by `Tipo Factura Descripción`. The caller already dispatches by area.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| All rows processed | mixed tipo_factura values | detector runs | every row evaluated regardless of tipo_factura |

### R6: Flagged Item Structure

Each flagged row MUST include these fields: `factura`, `codigo`, `procedimiento`, `cantidad`, `codigo_tipo_procedimiento`, `laboratorio`, `detalle`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Contains all fields | a row flagged | detector returns item | dict has all 7 keys with values |
| Missing any field | defective data | detector runs | row skipped gracefully |

### R7: Graceful Degradation

The system MUST return an empty list when required columns are missing. MUST NOT raise exceptions.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Missing Cantidad column | no "Cantidad" in Excel | detector runs | empty list returned |
| Missing Código Tipo Procedimiento | column absent | detector runs | all rows evaluated with general rule |
| Missing Laboratorio | column absent | detector runs | 02+Lab=No rule cannot match; falls through to general |

---

## Non-Functional Requirements

- **Performance**: single pass over rows; O(n) with n = data rows.
- **Safety**: no auto-correction — rows are NEVER modified, only flagged for review.
- **Constants**: all thresholds MUST live in `app/constants/intramural.py`.
