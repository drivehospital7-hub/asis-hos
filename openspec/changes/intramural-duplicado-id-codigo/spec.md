# Spec: Intramural — Duplicado ID+Código

## Purpose

Detectar filas duplicadas en facturación Intramural donde una misma combinación de paciente (`Nº Identificación`) y procedimiento (`Código`) aparece más de una vez. Cada fila del grupo duplicado se marca como error para revisión manual.

## Requirements

### Requirement: Detectar duplicados por identificación + código

The system MUST detect when two or more rows in an Intramural Excel share the same `Nº Identificación` AND the same `Código`, and SHALL mark all rows in that group as errors.

| Aspect | Detail |
|--------|--------|
| Columnas requeridas | `Nº Identificación` → `identificacion`, `Código` → `codigo` |
| Columnas adicionales | `Número Factura` → `numero_factura`, `Procedimiento` → `procedimiento` |
| Agrupación | `(identificacion, codigo)` — grupos con >1 fila son duplicados |
| Error se genera | Por cada fila del grupo, no solo la primera |

#### Scenario: Dos filas mismo paciente y mismo código

- GIVEN an Excel Intramural con filas: `F001, ID=123, Cód=X` y `F002, ID=123, Cód=X`
- WHEN the detector runs
- THEN both filas SHALL appear in the error list with `cantidad_repeticiones=2`

#### Scenario: Mismo paciente, distinto código no es duplicado

- GIVEN filas: `F001, ID=123, Cód=X` y `F002, ID=123, Cód=Y`
- WHEN the detector runs
- THEN ninguna fila SHALL be marked as duplicate

#### Scenario: Columnas faltantes

- GIVEN an Excel without column `Nº Identificación` OR without column `Código`
- WHEN the detector runs
- THEN SHALL return `[]` without error

#### Scenario: Sin duplicados

- GIVEN an Excel where every `(identificacion, codigo)` pair is unique
- WHEN the detector runs
- THEN SHALL return `[]`

### Requirement: Integración con el orquestador

The system MUST register the detector in `_get_intramural_detectors()` and SHALL call it in `detect_all_problems_intramural()`.

| Integration | Detail |
|-------------|--------|
| `_get_intramural_detectors()` | Append `detect_duplicado_id_codigo` to the returned list |
| `error_groups` | Add key `"Duplicado ID+Código"` with detector results |
| `resultado["problemas"]` | Add key `"duplicado_id_codigo"` |
| `resultado["totales"]` | Add key `"duplicado_id_codigo"` with `len()` |
| `build_normalized_rows()` | Add handler block for `"Duplicado ID+Código"` |

#### Scenario: Detector se ejecuta en flujo Intramural

- GIVEN the `detect_all_problems_intramural()` function
- WHEN processing an Excel with duplicates
- THEN the normalized rows SHALL include entries from `"Duplicado ID+Código"` group

### Error Format

```python
{
    "factura": str,                # "F001"
    "identificacion": str,         # "1234567890"
    "codigo": str,                 # "890405"
    "procedimiento": str,          # "CONSULTA MEDICINA GENERAL"
    "cantidad_repeticiones": int,  # 2
}
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `Nº Identificación` is `None` | Fila ignored (no key for grouping) |
| `Código` is `None` | Fila ignored |
| Three+ rows same pair | All filas errored, `cantidad_repeticiones = N` |
| Whitespace variations | Values SHALL be `.strip()`d before comparison |
| Mismatched types (123 vs "123") | Both SHALL be cast to string for comparison |

## Acceptance Criteria

- [ ] Dado Excel con 2+ filas mismo `Nº Identificación` y `Código`, detector marca TODAS como error
- [ ] Dado Excel sin columnas necesarias, detector retorna `[]` sin crash
- [ ] Dado Excel sin duplicados, detector retorna `[]`
- [ ] Error dict incluye `factura`, `identificacion`, `codigo`, `procedimiento`, `cantidad_repeticiones`
- [ ] Handler en `build_normalized_rows()` produce filas con `tipo_error: "Duplicado ID+Código"`
- [ ] Orquestador incluye el nuevo grupo en `error_groups` y `resultado["totales"]`
