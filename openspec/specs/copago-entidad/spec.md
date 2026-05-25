# Copago Entidad — Urgencias Specification

## Purpose

Validate that rows with a non-default "Cód Entidad Cobrar" (anything other than `1` or `0001`) MUST have `Vlr. Copago = 0`. If the entity is not the default one, the copago value must be zero — any non-zero copago on a non-default entity is a data error.

This rule applies to Urgencias ONLY.

## Requirements

### R1: Copago debe ser 0 cuando entidad no es default

For every row in an Urgencias sheet, the system MUST check the value of column `Cód Entidad Cobrar` (internal key: `codigo_entidad_cobrar`). If the value (when normalized to string) is NOT `"1"` AND NOT `"0001"`, then the value of column `Vlr. Copago` (internal key: `vlr_copago`) MUST be `0` (considering any type: integer, float, string, or None). Any non-zero copago value on such a row SHALL be flagged as an error.

When a row triggers this rule, the detection output MUST include the fields: `factura`, `codigo`, `procedimiento`, `entidad_cobrar`, and `vlr_copago`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Entidad 1 con copago 500 — ok | entidad_cobrar=`1`, vlr_copago=`500` | detecting | NO error |
| Entidad 0001 con copago 200 — ok | entidad_cobrar=`0001`, vlr_copago=`200` | detecting | NO error |
| Entidad 86 con copago 0 — ok | entidad_cobrar=`86`, vlr_copago=`0` | detecting | NO error |
| Entidad 86 con copago 500 — error | entidad_cobrar=`86`, vlr_copago=`500` | detecting | ERROR — factura, codigo, procedimiento, entidad_cobrar=`86`, vlr_copago=`500` |
| Entidad 3 con copago 100 — error | entidad_cobrar=`3`, vlr_copago=`100.0` | detecting | ERROR — vlr_copago=`100.0` |

### R2: Type normalization

The system MUST normalize `Cód Entidad Cobrar` to string (left-padded zeros preserved, e.g. `0001` stays `"0001"`). The system MUST treat `Vlr. Copago` as numeric for the zero check: empty/None SHALL be treated as `0` (no error). A string value like `"500"` SHALL be parsed as numeric `500`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Entidad 86, Vlr. Copago vacío | entidad_cobrar=`86`, vlr_copago=`None` | detecting | NO error (treated as 0) |
| Entidad 86, Vlr. Copago string "0" | entidad_cobrar=`86`, vlr_copago=`"0"` | detecting | NO error |
| Entidad 86, Vlr. Copago string "500" | entidad_cobrar=`86`, vlr_copago=`"500"` | detecting | ERROR |
| Entidad 0001, Vlr. Copago None | entidad_cobrar=`0001`, vlr_copago=`None` | detecting | NO error (default entity) |
| Entidad vacía, copago 300 — ok | entidad_cobrar=`None`, vlr_copago=`300` | detecting | NO error (no constraint applies) |

### R3: Per-row detection

Each row SHALL be evaluated independently. The same factura number MAY appear multiple times with different results depending on each row's entity + copago combination.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Same factura, two rows, one error | row1: entidad=86 copago=500, row2: entidad=1 copago=300 | detecting | Exactly 1 error (row1) |

### R4: Missing column handling

If column `Vlr. Copago` is missing from the Excel headers, the system MUST NOT crash — it SHALL silently skip this detector (return empty list).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Faltan columnas | `vlr_copago` index is `None` | detecting | Return `[]`, no crash |

## Non-Functional Requirements

- **Performance**: Single pass over rows — no nested loops or per-row database queries.
- **Safety**: Missing columns MUST NOT raise exceptions. Log at `warning` level and return empty.
- **Scope**: This requirement applies to Urgencias only. No other area (Odontología, Equipos Básicos) SHALL run this validation.
