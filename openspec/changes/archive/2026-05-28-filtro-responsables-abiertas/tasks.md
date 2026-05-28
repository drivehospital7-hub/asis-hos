# Tasks: Filtro por responsables en Abiertas Urgencias

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~55 (40 page.tsx + 15 tests) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Summary

Cambio puramente frontend: agregar un `<select>` nativo para filtrar la tabla de Abiertas Urgencias por responsable. Las opciones se derivan dinámicamente de `results[].responsable`. Sin cambios en backend, DB ni APIs. Sigue el patrón existente de `control-novedades`.

### Files Affected

| File | Action | Est. Lines |
|------|--------|------------|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modify | +40 |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | Modify | +15 |

### No Change Confirmed

| File | Reason |
|------|--------|
| `frontend/src/pages/abiertas-urgencias/utils.ts` | `copiarResultados` ya acepta `FacturaResult[]` — funciona con subset |

---

## Phase 1: Filter State & Derivation

- [x] 1.1 Add `useMemo` to React import (line 1)
- [x] 1.2 Add `const [filterResponsable, setFilterResponsable] = useState("")` junto a `showResults`
- [x] 1.3 Add `useMemo` for `responsables` — unique values from `results[].responsable`, sorted, with `|| "—"` fallback
- [x] 1.4 Add `useMemo` for `filteredResults` — filter by `filterResponsable` when active, else pass through

**Verification**: Al cargar resultados con 3 responsables distintos, el array `responsables` contiene 3 strings únicos ordenados. `filteredResults` retorna solo el subconjunto cuando hay filtro activo.

---

## Phase 2: UI Integration

- [x] 2.1 Insert `<select>` nativo entre el contador y el botón "Copiar a Excel" con clases `h-9 rounded-md border border-input bg-background px-3 text-sm`
- [x] 2.2 Change `results.map(...)` → `(filteredResults ?? results).map(...)` en el render de tabla (línea 616)
- [x] 2.3 Update counter to show `(filteredResults ?? results).length` (línea 577)
- [x] 2.4 Pass `filteredResults ?? results` to `copiarResultados` in `handleCopiarResultados` (línea 440-448)
- [x] 2.5 Add `setFilterResponsable("")` in `handleProcesarFacturas` after `setResults(newResults)` (línea 340)

**Verification**: Selector renderiza con opciones únicas. Al seleccionar un responsable, tabla filtra. Counter refleja count filtrado. Copiar a Excel copia solo filas visibles. Al reprocesar, filtro se resetea a "Todos".

---

## Phase 3: Testing

- [x] 3.1 Add test: `getUniqueResponsables` returns unique sorted values from results
- [x] 3.2 Add test: `filterResultsByResponsable` returns full set when `filterResponsable` is `""`
- [x] 3.3 Add test: `filterResultsByResponsable` filters correctly by responsable
- [x] 3.4 Add test: `filterResultsByResponsable` handles null/empty results gracefully
- [x] 3.5 Add test: `getUniqueResponsables` handles null/undefined responsable and special values

**Verification**: `npx vitest run` — all existing tests pass, 5 new tests pass.
