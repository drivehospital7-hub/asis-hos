# CUPS Equivalentes Intramural — Specification

## Purpose

Detect incorrect CUPS codes in Intramural rows where the operator wrote a wrong code instead of the correct equivalent. Two known mappings exist: 906317 → 1906317 (Hepatitis B rápida) and 906249 → 906249PR (VIH Prueba rápida).

---

## Requirements

### R1: Detect 906317 (Hepatitis B Rápida)

The system MUST flag every Intramural row where `Código` = `"906317"` and report the correct equivalent `"1906317"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| 906317 detected | row has Código = 906317, Proc = "Hepatitis B" | detector runs | flagged with acción "Usar 1906317" |
| Already correct | row has Código = 1906317 | detector runs | NOT flagged |

### R2: Detect 906249 (VIH Prueba Rápida)

The system MUST flag every Intramural row where `Código` = `"906249"` and report the correct equivalent `"906249PR"`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| 906249 detected | row has Código = 906249, Proc = "VIH Prueba" | detector runs | flagged with acción "Usar 906249PR" |
| Already correct | row has Código = 906249PR | detector runs | NOT flagged |

### R3: Output Structure

Each flagged item MUST include these fields: `factura`, `codigo`, `codigo_equiv`, `accion`, `procedimiento`.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Complete output | row with 906317 flagged | item returned | dict has all 5 keys with values |
| Empty codigo_equiv | new equiv rule without replacement | future rule | codigo_equiv SHALL be `""` |

### R4: Graceful Degradation

The system MUST return an empty list when required columns are missing. MUST NOT raise exceptions.

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Missing Código column | no "Código" in Excel | detector runs | empty list returned |
| Missing Número Factura | column absent | detector runs | empty list returned |
| Empty Código value | Código cell is None | row evaluated | row skipped gracefully |
| Non-Intramural domain | Tipo Factura = Urgencias | detector runs | not evaluated (filtered by caller) |

### R5: No False Positives with Existing Constants

The system MUST NOT conflict with existing constants. 906249 is already in `CODIGOS_EXCLUIDOS_VACUNACION` — the cups_equivalentes rule is a separate concern (detection context = centro_costo vs cups_equivalentes).

| Scenario | Given | When | Then |
|----------|-------|------|------|
| Coexists with vacunacion | row with Código=906249, CodigoTipoProc=05 | both detectors run | centro_costo evaluates vacunacion rule, cups_equivalentes flags mapping error |

---

## Data Dictionary

### Input Columns

| Column | Type | Used For |
|--------|------|----------|
| `Número Factura` | string | Invoice identifier (output key) |
| `Código` | string | CUPS code to validate |
| `Procedimiento` | string | Procedure name (output context) |

### Output Fields (per flagged item)

| Field | Type | Description |
|-------|------|-------------|
| `factura` | string | Normalized invoice number |
| `codigo` | string | The incorrect CUPS code found |
| `codigo_equiv` | string | Always `""` for Intramural (no replacement stored) |
| `accion` | string | Human-readable action, e.g. `"Usar 1906317"` |
| `procedimiento` | string | Procedure description from the row |

### Constants (added to `app/constants/intramural.py`)

```python
CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL: dict[str, str] = {
    "906317": "1906317",   # Hepatitis B (Prueba rápida) — usar 1906317
    "906249": "906249PR",  # VIH Prueba rápida — usar 906249PR
}
```

---

## Non-Functional Requirements

- **Performance**: O(n) single pass over rows; constant-time dict lookup per row.
- **Safety**: READ-ONLY — never modifies Excel cells, only reports problems.
- **Constants source**: mappings SHALL live in `app/constants/intramural.py` as `CODIGOS_CUPS_EQUIVALENTES_INTRAMURAL`.
- **Domain isolation**: detector SHALL NOT filter by Tipo Factura — the caller (`detect_all.py`) already dispatches by area.
