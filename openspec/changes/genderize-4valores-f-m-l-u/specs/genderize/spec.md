# Genderize Specification

## Purpose

Define the behavior for gender prediction and correction using 4 canonical values: female (F), male (M), lastname (L), and undefined (U). These values support both API-driven prediction and manual override in the import-facturas workflow.

## Requirements

### Requirement: Cache stores 4 canonical values

The genderize cache MUST store gender as one of four canonical strings: `"female"`, `"male"`, `"lastname"`, or `"undefined"`. Legacy `null` values in the cache file SHALL be mapped to `"undefined"` when loaded.

#### Scenario: Load maps null to undefined

- GIVEN a cache file with `{"name": {"gender": null}}`
- WHEN `_load_cache()` executes
- THEN the in-memory entry MUST contain `{"gender": "undefined"}`

#### Scenario: Existing values unchanged

- GIVEN a cache file with existing `"female"` and `"male"` entries
- WHEN `_load_cache()` executes
- THEN those entries MUST NOT be modified

### Requirement: predict_genders stores undefined on API null

When the Genderize API returns `null` for a name, `predict_genders()` MUST store `"undefined"` in the cache instead of `null`.

#### Scenario: API returns null

- GIVEN an API response with `"gender": null`
- WHEN `predict_genders()` processes the result
- THEN the cache MUST store `{"gender": "undefined"}`

#### Scenario: API returns valid gender

- GIVEN an API response with `"gender": "male"`
- WHEN `predict_genders()` processes the result
- THEN the cache MUST store `{"gender": "male"}`

### Requirement: override_gender accepts short and long forms

`override_gender(normalized_name, new_gender)` MUST accept short codes (`"F"`, `"M"`, `"L"`, `"U"`) and long forms (`"female"`, `"male"`, `"lastname"`, `"undefined"`). Any other value MUST be rejected.

#### Scenario: Short code normalizes to long

- GIVEN a cache entry with `{"gender": "undefined"}`
- WHEN calling `override_gender("juan", "M")`
- THEN the cache SHALL update to `{"gender": "male"}`

#### Scenario: Long form accepted directly

- GIVEN a cache entry with `{"gender": "undefined"}`
- WHEN calling `override_gender("juan", "lastname")`
- THEN the cache SHALL update to `{"gender": "lastname"}`

#### Scenario: Invalid value raises error

- GIVEN any cache entry
- WHEN calling `override_gender("juan", "X")`
- THEN the function MUST raise an error
- AND the cache SHALL NOT be modified

### Requirement: Discrepancies include all 4 values

`verificar_y_comparar()` MUST include discrepancies for all 4 values. The skip for unknown/null values SHALL be removed. The `sexo_api` field in discrepancy objects SHALL use short codes: `"F"`, `"M"`, `"L"`, or `"U"`.

#### Scenario: Undefined shows as U

- GIVEN `sexo_excel="M"` and `sexo_api="undefined"`
- WHEN `verificar_y_comparar()` executes
- THEN a discrepancy SHALL exist with `sexo_api="U"`

#### Scenario: Lastname shows as L

- GIVEN `sexo_excel="F"` and `sexo_api="lastname"`
- WHEN `verificar_y_comparar()` executes
- THEN a discrepancy SHALL exist with `sexo_api="L"`

### Requirement: API endpoint validates 4 values

`POST /api/import/cache-corregir` MUST accept `genero` values in `{"F", "M", "L", "U", "female", "male", "lastname", "undefined"}`. Other values MUST return a 400-level error.

#### Scenario: Valid short code accepted

- GIVEN a request with `genero="L"`
- WHEN the endpoint processes the request
- THEN it SHALL normalize `"L"` to `"lastname"`
- AND update the cache

#### Scenario: Invalid code rejected

- GIVEN a request with `genero="X"`
- WHEN the endpoint validates the input
- THEN it SHALL return a 400-level error
- AND SHALL NOT modify the cache

### Requirement: Frontend dropdown with 4 options

The GenderizePage MUST render a dropdown with options `"F"`, `"M"`, `"L"`, `"U"` for each discrepancy row. The dropdown MUST pre-select the `sexo_excel` value.

#### Scenario: Dropdown pre-selects Excel value

- GIVEN a row where `sexo_excel="M"`
- WHEN the row renders
- THEN the dropdown SHALL show `"M"` as selected

#### Scenario: User corrects via dropdown

- GIVEN a row with `sexo_excel="M"` and `sexo_api="U"`
- WHEN the user selects `"F"` and clicks apply
- THEN a POST to `/api/import/cache-corregir` SHALL include `genero="F"`
- AND the row SHALL update on success

### Requirement: Short codes in UI, long forms in cache

The frontend SHALL display gender using short codes (`F`, `M`, `L`, `U`). The backend cache SHALL store long forms (`female`, `male`, `lastname`, `undefined`). The bidirectional mapping SHALL be defined in app constants.

#### Scenario: Frontend shows F for female

- GIVEN a cache value of `"female"`
- WHEN the frontend renders the value
- THEN it SHALL display `"F"`

#### Scenario: Cache stores female for F

- GIVEN a correction with `genero="F"`
- WHEN the backend processes it
- THEN the cache SHALL store `"gender": "female"`
