# Tasks: Reordenar Tabla de Resultados

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~100 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Foundation — fec_factura pipeline (backend)

- [x] 1.1 **`app/services/odontologia/normalized_rows.py`**: Add `fec_factura_map: dict[str, str]` param to `build_odontologia_normalized_rows()`; add `_get_fec_factura()` helper; add `"fec_factura"` key to every row dict
- [x] 1.2 **`app/services/urgencias/normalized_rows.py`**: Same change — add param, `_get_fec_factura()` helper, `"fec_factura"` key to every row dict
- [x] 1.3 **`app/services/odontologia/detect_all.py`**: Build `fec_factura_map` from raw sheet (mirror `responsable_cierra` block); pass to `build_odontologia_normalized_rows()`
- [x] 1.4 **`app/services/urgencias/detect_all.py`**: Same — build `fec_factura_map`; pass to `build_urgencias_normalized_rows()`
- [x] 1.5 **`app/services/equipos_basicos/detect_all.py`**: Same — build `fec_factura_map`; pass to `build_odontologia_normalized_rows()`

## Phase 2: Integration — JSON response + columns

- [x] 2.1 **`app/routes/excel_headers.py`**: Add `"fec_factura": row.get("fec_factura", "")` to `all_items`; prepend `"Fec. Factura"` to `columnas`
- [x] 2.2 **`app/routes/urgencias.py`**: Same — add `fec_factura` to `all_items`; prepend to `columnas`
- [x] 2.3 **`app/routes/odontologia_equipos_basicos.py`**: Same — add `fec_factura` to `all_items`; prepend to `columnas`

## Phase 3: Frontend — Acción removal + Fec. Factura render

- [x] 3.1 **`frontend/src/pages/odontologia/page.tsx`**: Add `fec_factura` to `ErrorGroup` interface; remove `<th>Acción</th>` and `<td><Button>Controlar...</Button></td>`; add `<th>Fec. Factura</th>` as first `<th>` and `<td>{f.fec_factura}</td>` as first `<td>`
- [x] 3.2 **`frontend/src/pages/urgencias/page.tsx`**: Same changes
- [x] 3.3 **`frontend/src/pages/odontologia-equipos-basicos/page.tsx`**: Same changes

## Phase 4: Verification

- [x] 4.1 **Regression**: Run `pytest -v` — assert no failures (492 passed, 1 pre-existing unrelated failure)
- [x] 4.2 **Integration**: POST to each route → assert `all_items[*].fec_factura` exists and `columnas[0] === "Fec. Factura"`
- [ ] 4.3 **Visual check**: All 3 pages render without "Controlar" button; "Fec. Factura" appears as first column (pending manual browser check)
