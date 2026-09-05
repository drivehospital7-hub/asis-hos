# Delta for Genderize

> Este spec es un delta sobre `openspec/changes/genderize-4valores-f-m-l-u/specs/genderize/spec.md`.
> Describe cambios ONLY — requirements no mencionados acá permanecen como estaban.

## ADDED Requirements

### Requirement: Export includes sexo from Excel

The `get_stats()` function MUST return `nombres_no_cache` as `list[dict]` where each
dict contains `nombre` (normalized lowercase, no accents) and `sexo` (the `"M"` or `"F"`
value from the Excel `"Sexo"` column). The frontend export SHALL produce tab-separated
format: `<nombre>\t<sexo>`, entries comma-separated, prefixed with BOM (`\uFEFF`).

#### Scenario: Export with sexo from Excel

- GIVEN an Excel row with `Nombre="María", Sexo="F"` and "maria" not in cache
- WHEN `get_stats()` executes
- THEN `nombres_no_cache` MUST include `{nombre: "maria", sexo: "F"}`
- AND the export string SHALL contain `"maria\tF"`

#### Scenario: Deduplicated names preserve sexo

- GIVEN two Excel rows with `Nombre="Juan", Sexo="M"` and "juan" not in cache
- WHEN `get_stats()` executes
- THEN `nombres_no_cache` MUST contain exactly one entry `{nombre: "juan", sexo: "M"}`

### Requirement: Estimation stats are preserved

`get_stats()` MUST continue to return `total_excel`, `nombres_unicos`, `cache_hits`,
and `api_calls_necesarias`. Since no API calls remain, `api_calls_necesarias` SHALL
always be 0. Cache misses SHALL NOT be counted for auto-processing.

#### Scenario: All stats returned

- GIVEN an input with `total_excel=10`, 6 unique names, 4 in cache
- WHEN `get_stats()` executes
- THEN `cache_hits` MUST equal 4
- AND `nombres_unicos` MUST equal 6
- AND `api_calls_necesarias` MUST equal 0

## MODIFIED Requirements

### Requirement: predict_genders uses cache only, skips on miss

`predict_genders()` MUST operate entirely without HTTP requests. On cache hit it
SHALL return the cached gender. On cache miss it SHALL silently skip — no prediction,
no auto-assignment to any value (including `"U"`), no cache mutation. `_classify()`
for "Hijo de"/"Hija de" SHALL remain local and function as before.
(Previously: predict_genders called Genderize API and stored `"undefined"` on API null)

#### Scenario: Cache hit returns cached value

- GIVEN a cache with `{"maria": {"gender": "female"}}`
- WHEN `predict_genders()` processes `"maria"`
- THEN it MUST return `{"maria": "female"}`
- AND the cache SHALL NOT be modified

#### Scenario: Cache miss skips silently

- GIVEN a cache with no entry for `"juan"`
- WHEN `predict_genders()` processes `"juan"`
- THEN it MUST NOT return a result for `"juan"`
- AND no entry SHALL be created in the cache

#### Scenario: Hijo de classified locally

- GIVEN a name `"hijo de juan"`
- WHEN `predict_genders()` processes it
- THEN it MUST classify via `_classify()` without cache or network access

#### Scenario: No auto-assignment of U

- GIVEN a name `"pedro"` not in cache
- WHEN `predict_genders()` processes it
- THEN it MUST NOT assign `"U"` or any other value
- AND the cache state SHALL remain unchanged

## REMOVED Requirements

### Requirement: predict_genders stores undefined on API null

(Reason: No API calls exist. Fully replaced by the local-only requirement above.)

#### Scenario: API returns null

- Obsolete — removed.

#### Scenario: API returns valid gender

- Obsolete — removed.
