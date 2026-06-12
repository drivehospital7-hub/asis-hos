# Design: Genderize 4 valores (F/M/L/U)

## Technical Approach

Cache stores full words (`"female"`, `"male"`, `"lastname"`, `"undefined"`) for backward compatibility. Frontend renders short codes (`F`/`M`/`L`/`U`). A centralized constant mapping in `base.py` bridges both domains. `_load_cache()` transparently maps legacy `null` → `"undefined"`. The discrepancy checker removes the `"? continue"` skip — all 4 values now produce visible discrepancies.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Cache format | Full words (`"female"`) | Short codes (`"F"`) | Backward compatible with existing cache. No migration needed. |
| null handling | `_load_cache()` maps null → `"undefined"` | DB migration, in-place rewrite | Transparent, zero-downtime. Only affects in-memory view. |
| Discrepancy skip | Remove `"? continue"` entirely | Partial skip for L-only | All 4 values must show. Users need to see when API fails. |
| UI correction | Dropdown per row | Single button, modal | User chooses the target value, not forced to Excel's. |

## Data Flow

```
[Frontend]                     [Backend]                     [Cache]
    │                              │                            │
    │  POST cache-corregir         │                            │
    │  {nombre, genero: "M"}       │                            │
    │ ─────────────────────────►   │                            │
    │                              │  Normaliza "M" → "male"    │
    │                              │  override_gender(...)      │
    │                              │ ──────────────────────►   │
    │                              │                            │
    │  200 OK                      │                            │
    │ ◄─────────────────────────   │                            │
    │                              │                            │
    │  Refetch verify results      │                            │
    │ ─────────────────────────►   │                            │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/base.py` | Modify | Add `GENDER_*`, `GENDER_DISPLAY_MAP`, `GENDER_CACHE_MAP`, `GENDER_VALID_*` |
| `app/services/genderize_service.py` | Modify | `predict_genders()`: store `"undefined"` on API null. `override_gender()`: accept short/long forms, normalize. `_load_cache()`: map null→`"undefined"`. |
| `app/services/genderize_verifier.py` | Modify | Remove `sexo_api_code == "?" continue`. Map `"male"→M, "female"→F, "lastname"→L, "undefined"→U`. |
| `app/routes/import_facturas.py` | Modify | `cache-corregir`: validate 8 forms (short + long for each of 4 values). |
| `frontend/src/pages/genderize/page.tsx` | Modify | Replace button with `<select>` dropdown (F/M/L/U) + apply button per row. |
| `tests/services/test_genderize_verifier.py` | Modify | Update fixtures (adjust for new mapping). No breaking change since `sexo="M"` in fixtures still valid. |
| `tests/services/test_genderize_service.py` | Create | New tests for `_load_cache` null mapping, `override_gender` 4-value validation, `predict_genders` undefined storage. |

## Interfaces / Contracts

### New Constants (`app/constants/base.py`)

```python
GENDER_FEMALE = "female"
GENDER_MALE = "male"
GENDER_LASTNAME = "lastname"
GENDER_UNDEFINED = "undefined"

GENDER_DISPLAY_MAP = {"F": "female", "M": "male", "L": "lastname", "U": "undefined"}
GENDER_CACHE_MAP = {"female": "F", "male": "M", "lastname": "L", "undefined": "U"}
GENDER_VALID_SHORT = frozenset({"F", "M", "L", "U"})
GENDER_VALID_LONG = frozenset({"female", "male", "lastname", "undefined"})
```

### Updated `override_gender(normalized_name, new_gender)`

- **Input**: `new_gender` accepts `"F"`/`"M"`/`"L"`/`"U"` (short) or `"female"`/`"male"`/`"lastname"`/`"undefined"` (long)
- **Normalization**: short code → full word via `GENDER_DISPLAY_MAP`; long word validated against `GENDER_VALID_LONG`
- **Error**: Invalid values → `ValueError`

### Endpoint `POST /api/import/cache-corregir`

```json
// Request
{ "nombre_normalizado": "juan perez", "genero": "M" }
// Response (200)
{ "status": "success", "data": { "nombre_normalizado": "...", "genero": "male" } }
// Response (400 - invalid gender)
{ "status": "error", "data": {}, "errors": ["'genero' debe ser F/M/L/U o female/male/lastname/undefined"] }
```

### `Discrepancia.sexo_api` — updated contract

- `"F"` for `"female"`, `"M"` for `"male"`, `"L"` for `"lastname"`, `"U"` for `"undefined"`

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_load_cache()` maps null→`"undefined"`, preserves existing values | Patch `json.loads` return, assert output dict |
| Unit | `override_gender()` accepts short/long, rejects invalid | Call with F/M/L/U + female/male/lastname/undefined + invalid |
| Unit | `predict_genders()` stores `"undefined"` on API null | Mock API response `{"gender": null}`, assert cache entry |
| Unit | `verificar_y_comparar()` includes U/L discrepancies | Mock extract + cache, assert Discrepancia list includes U/L rows |
| Integration | Endpoint accepts F/M/L/U and long forms, rejects X | POST to `/api/import/cache-corregir` with test client |
| UI | Dropdown renders 4 options, pre-selects sexo_excel, applies correction | Manual (React component test if infra exists) |

## Migration / Rollout

No migration required. Legacy `null` values in cache are mapped to `"undefined"` at load time. Existing `"male"`/`"female"` entries remain unchanged. Rollback: revert commits in order frontend → routes → verifier → service → constants.
