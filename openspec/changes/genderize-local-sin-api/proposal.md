# Proposal: Export no-cache con genero del Excel y eliminar dependencia de API Genderize

## Intent

Dos cambios convergen: (1) el export no-cache actual solo manda nombres, sin el sexo del Excel — forzando pegado manual. (2) `predict_genders()` hace HTTP calls a Genderize.io que ya no usamos. Eliminar la dependencia de red simplifica el flujo a cache-local puro, y el export con sexo elimina el paso manual para el usuario.

## Scope

### In Scope
- Modificar `get_stats()` para que `nombres_no_cache` incluya `sexo_excel` (M/F del Excel) por cada entrada
- Reescribir `predict_genders()` como 100% local: cache hit → valor cacheado, cache miss → skip (sin "U" automática)
- `verificar_y_comparar()`: eliminar batching y API calls; solo procesa cache hits + "Hijo de"/"Hija de"
- Ruta `/api/genderize/` completa → eliminar
- Frontend: export como `nombre_normalizado\tsexo_excel,nombre2\tsexo2`; remover contador de tokens
- Tests: reescribir tests que mockean `urlopen`; actualizar tests de verifier para nuevos formatos

### Out of Scope
- Auto-asignar "U" a nombres sin cache
- Cambiar manejo del archivo `genderize_cache.json`
- Modificar `override_gender` o el dropdown de discrepancias (F/M/L/U)
- Cualquier otra feature

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- **`genderize`** (capa existente del cambio `genderize-4valores-f-m-l-u`): `predict_genders()` cambia de HTTP+cache a solo cache. Response de `/api/import/facturas-stats` cambia: `nombres_no_cache` pasa de `string[]` a `array[{nombre, sexo}]`. `/api/genderize/` se elimina.

## Approach

### Change 1 — Export con sexo (tab-separado)

| Capa | Cambio |
|------|--------|
| `genderize_verifier.get_stats()` | `nombres_no_cache` pasa de `list[str]` a `list[tuple[str, str]]` → cada entrada es `(nombre_normalizado, sexo_excel)` |
| Route `/api/import/facturas-stats` | Response: `nombres_no_cache` como `array[{nombre: string, sexo: string}]` |
| Frontend `StatsData` | Interface: `nombres_no_cache: {nombre: string, sexo: string}[]` |
| Frontend `exportNoCache()` | Formato: `"\uFEFF" + items.map(i => `${i.nombre}\t${i.sexo}`).join(", ")` |

### Change 2 — Eliminar API Genderize

| Capa | Cambio |
|------|--------|
| `genderize_service.predict_genders()` | Remover imports HTTP, `GENDERIZE_API_URL`, `GENDERIZE_API_KEY`, `RateLimitInfo`. Cache hit → devuelve valor. Cache miss → SKIP (no retorna GenderResult). `_classify()` se mantiene. |
| `genderize_verifier.verificar_y_comparar()` | Eliminar batching de 10. Solo itera `unique_names`, consulta cache. Nombres sin cache simplemente no aparecen en `all_results` → no generan discrepancia. |
| `routes/genderize_api.py` | Eliminar archivo + blueprint de `app/__init__.py` |
| `routes/import_facturas.py` | Eliminar import `HTTPError`, bloque `except HTTPError`, contador de tokens del response |
| Frontend | Botón "Verificar" sin `(N tokens)`. Stats muestra `api_calls_necesarias=0` o se renombra. |
| Tests | Tests que mockean `urlopen` → reescribir como tests de cache-hit y cache-miss-skip. Tests de `verifier` actualizar para nuevo formato de `nombres_no_cache` y flujo sin API. |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/services/genderize_service.py` | Modified | Simplificar `predict_genders()` a local-only; remover imports HTTP, `RateLimitInfo`, env vars |
| `app/services/genderize_verifier.py` | Modified | `get_stats()` retorna pares nombre+sexo; `verificar_y_comparar()` sin API path |
| `app/routes/import_facturas.py` | Modified | Response stats cambia formato; remover `except HTTPError`; remover token count |
| `app/routes/genderize_api.py` | Removed | Eliminar archivo + blueprint |
| `app/__init__.py` | Modified | Remover registro de `genderize_bp` |
| `frontend/src/pages/genderize/page.tsx` | Modified | Export format `nombre\tsexo`; remover token count de UI |
| `tests/services/test_genderize_service.py` | Modified | Reescribir tests de `predict_genders` sin mock de `urlopen` |
| `tests/services/test_genderize_verifier.py` | Modified | Actualizar tests para nuevo formato y flujo sin API |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Breaking change response stats** | Low | Frontend y backend se deployan juntos. Cambio es controlado. |
| **Cache no crece automáticamente** | Med | Esperado y deseado. El usuario entiende que solo crece con correcciones manuales vía dropdown. |
| **Test rotos por mock de urlopen** | Low | 3 tests existentes fáciles de reescribir como tests de cache-hit/miss-skip. |

## Rollback Plan

1. Revertir `genderize_service.py` a versión anterior con `urlopen` y API calls
2. Revertir `genderize_verifier.py` — `get_stats()` vuelve a `list[str]`, `verificar_y_comparar()` recupera batching
3. Restaurar `genderize_api.py` y su blueprint
4. Deshacer cambios en frontend
5. Revertir tests

## Dependencies

- Ninguna externa. Todo es stdlib (Flask, Polars, openpyxl ya instalados).

## Success Criteria

- [ ] `predict_genders()` NO hace ninguna llamada HTTP (confirmado por ausencia de imports de red + cobertura de tests)
- [ ] Export no-cache produce formato `nombre\tsexo,nombre2\tsexo2` con sexo M/F del Excel
- [ ] Discrepancias siguen mostrando L y U con dropdown F/M/L/U funcional
- [ ] Tests pasan sin mockear `urlopen`
- [ ] Cache hit/miss counts se mantienen en stats
