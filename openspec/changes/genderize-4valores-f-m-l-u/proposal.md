# Proposal: Genderize 4 valores (F/M/L/U)

## Intent

El genderize actual solo soporta 2 valores (male/female). Los apellidos no detectables y nombres sin género conocido quedan fuera del sistema. Necesitamos 4 valores (F/M/L/U) en cache, discrepancias y frontend para empezar a alimentar la DB con datos completos.

## Scope

### In Scope
- Constantes para los 4 valores (F/M/L/U) en `app/constants/base.py`
- `_load_cache()` mapea null → "undefined" (backward compatible)
- `predict_genders()` guarda "undefined" en vez de null
- `override_gender()` acepta los 4 valores
- `verificar_y_comparar()` muestra discrepancias para todos (elimina skip de "?")
- Endpoint `cache-corregir` valida F/M/L/U + long forms
- Frontend: botón único → dropdown con F/M/L/U, pre-selecciona sexo_excel
- Tests actualizados

### Out of Scope
- Cambios en llamada a Genderize API
- Migración de cache existente (backward compatible)
- Cualquier feature fuera de genderize

## Capabilities

### New Capabilities
- `exportar-nocache` — primera especificación formal del dominio genderize.

### Modified Capabilities
None.

## Approach

**Approach 2 from exploration — completo con backward compatibility.** Cache stores full words ("female"/"male"/"lastname"/"undefined") como hasta ahora. Frontend muestra códigos cortos (F/M/L/U). El mapping bidireccional vive en constantes. `_load_cache()` migra null legacy a "undefined" en carga. La discrepancia ya no salta valores — "U" es un valor válido y se muestra.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/constants/base.py` | New | `GENDER_*`, `GENDER_DISPLAY_MAP`, `GENDER_CACHE_MAP`, `GENDER_VALID_*` |
| `app/services/genderize_service.py` | Modified | `predict_genders()`: undef. `override_gender()`: 4 vals. `_load_cache()`: null→undef. |
| `app/services/genderize_verifier.py` | Modified | Mapear 4 vals. Eliminar skip "?". Sexo_api como F/M/L/U en Discrepancia. |
| `app/routes/import_facturas.py` | Modified | Endpoint cache-corregir: validar 4 valores. |
| `frontend/src/pages/genderize/page.tsx` | Modified | Botón → dropdown con F/M/L/U. |
| `tests/services/test_genderize_verifier.py` | Modified | Actualizar fixtures + tests nuevos. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Cache legacy null se pierde | Low | `_load_cache()` mapea null→"undefined" al cargar |
| Frontend dropdown design | Med | Usar `<select>` nativo si shadcn Select no está disponible |
| Tests con sexo="M" hardcodeado | Low | Revisar fixtures al actualizar tests |

## Rollback Plan

Revert commits en orden inverso: frontend → routes → verifier → service → constants. Cache existente no se modifica (solo lectura), rollback inmediato sin pérdida de datos.

## Dependencies

None.

## Success Criteria

- [ ] `predict_genders()` guarda "undefined" cuando API retorna null
- [ ] Discrepancias muestran registros con sexo_api="U" (antes se saltaban)
- [ ] Dropdown en frontend permite elegir entre F/M/L/U y aplicar corrección
- [ ] Cache existente con "male"/"female" funciona sin cambios
- [ ] `override_gender("L")` guarda "lastname", `override_gender("U")` guarda "undefined"
- [ ] Todos los tests pasan (`python -m pytest -v`)
