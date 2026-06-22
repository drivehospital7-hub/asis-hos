# Genderize — Sistema 4 Valores Specification

## Purpose

Cache-only gender resolution for `/import-facturas` with four values: F (female), M (male), L (lastname/apellido), U (undefined). No external API calls—local JSON cache is the sole source.

## Requirements

### Requirement: Cache-Only Prediction

MUST NOT call any external API. Predictions MUST come exclusively from the local JSON cache.

#### Scenario: Cached name returns gender

- GIVEN a name exists in `genderize_cache.json` with `"gender": "male"`
- WHEN `predict_genders` is called for that name
- THEN it returns `{"nombre": name, "sexo": "M"}` without any HTTP request

#### Scenario: Uncached name produces no result

- GIVEN a name does NOT exist in the cache
- WHEN `predict_genders` is called for that name
- THEN it returns no entry for that name (silently skipped)

### Requirement: 4-Value Normalization

The system MUST normalize both short codes (`F`, `M`, `L`, `U`) and long forms (`female`, `male`, `lastname`, `undefined`) to canonical short codes. Any value outside this set MUST be rejected.

#### Scenario: All valid forms normalize correctly

- GIVEN the input values `"male"`, `"M"`, `"female"`, `"F"`, `"lastname"`, `"L"`, `"undefined"`, `"U"`
- WHEN `_normalize_gender` processes each
- THEN the system MUST return `"M"`, `"M"`, `"F"`, `"F"`, `"L"`, `"L"`, `"U"`, `"U"` respectively

#### Scenario: Invalid value is rejected

- GIVEN the input value `"X"`
- WHEN `_normalize_gender` processes it
- THEN the system MUST raise or return an error indicating the value is invalid

### Requirement: Cache Null Handling

The cache loader MUST map JSON `null` gender values to `"undefined"` in memory. It MUST also strip BOM characters and zero-width spaces from cache keys before processing.

#### Scenario: Null cache entry becomes undefined

- GIVEN a cache entry with `"gender": null` for name `"JUAN PEREZ"`
- WHEN `_load_cache` processes the file
- THEN in-memory representation contains `"JUAN PEREZ"` → `{"gender": "undefined"}`

#### Scenario: BOM-stripped key matches clean query

- GIVEN a cache file with key `"\uFEFFJUAN"` (BOM prefix)
- WHEN `_load_cache` processes it
- THEN the key is stored as `"JUAN"` and a query for `"JUAN"` matches

### Requirement: Frontend Gender Override

The frontend MUST provide a per-row dropdown selector with options F, M, L, U for each discrepancy. The backend MUST accept all four values via the override endpoint.

#### Scenario: Override with new 4-value option

- GIVEN a row displaying name `"MARIA GOMEZ"` with detected gender `"U"`
- WHEN the user selects `"F"` from the dropdown and clicks "Corregir"
- THEN the backend stores `"MARIA GOMEZ"` → `{"gender": "female"}` in the cache

#### Scenario: Dropdown preserves current selection

- GIVEN a row with existing correction `"M"`
- WHEN the dropdown renders
- THEN option `"M"` is pre-selected

### Requirement: Column Extraction

The system MUST extract three new columns from Excel files: Nº Identificación, Entidad Cobrar, Tipo Identificación. The discrepancy response MUST include these fields per row.

#### Scenario: All three columns present

- GIVEN an Excel file with columns `Nº Identificación`, `Entidad Cobrar`, `Tipo Identificación`
- WHEN `genderize_extractor` processes the file
- THEN each discrepancy row includes those values

#### Scenario: Column missing from Excel

- GIVEN an Excel file missing `Entidad Cobrar`
- WHEN `genderize_extractor` processes the file
- THEN the missing column is returned as an empty string per row

### Requirement: No-Cache Export

The system MUST provide an export endpoint that downloads all names without cache entries as a tab-separated file (`nombre\tsexo`).

#### Scenario: Export uncached names

- GIVEN 5 names with no cache entries and 10 with cached genders
- WHEN the user clicks "Exportar no-cache"
- THEN a TSV file is downloaded containing exactly the 5 uncached names with their Excel `sexo` values

#### Scenario: All names cached — no export

- GIVEN all names in the current file have cache entries
- WHEN the user clicks "Exportar no-cache"
- THEN either an empty file is downloaded or the button is disabled with a "No hay nombres sin caché" message
