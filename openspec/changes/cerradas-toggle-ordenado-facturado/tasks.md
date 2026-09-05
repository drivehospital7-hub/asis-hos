# Tasks: Cerradas Toggle — Ordenado y Facturado

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~140 (all additions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-always |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Toggle completo + tests | PR 1 | Single PR, ~140 lines, well under budget |

---

## Phase 1: Service — Parámetro, Header Opcional y Filtro

- [ ] 1.1 Agregar `"fecha_cierre": "Fecha Cierre"` a `AYUDAS_OPTIONAL_HEADERS` en `app/services/ordenado_facturado_service.py`
- [ ] 1.2 Agregar `cerradas: bool = False` a la firma de `procesar_cruce()`
- [ ] 1.3 Detectar `idx_fecha_cierre` junto a los otros headers opcionales (`indices_opt_ayudas.get("fecha_cierre")`)
- [ ] 1.4 Incluir `"fecha_cierre"` en cada dict de `no_facturados` (tanto en el loop de VISIBLE_CODES como en el de traslados)
- [ ] 1.5 Insertar filtro post-hoc después de construir `no_facturados` (línea ~808): si `cerradas=True` y `idx_fecha_cierre is not None`, excluir registros con `fecha_cierre` vacío (None, `""`, NaN)
- [ ] 1.6 Recalcular `total_no_facturado = len(no_facturados)` y actualizar cada fila de `totalizado` recontando desde la lista filtrada

## Phase 2: Route — Leer Cerradas del Form

- [ ] 2.1 En `app/routes/ordenado_facturado.py`, leer `request.form.get("cerradas") == "true"` antes de llamar `procesar_cruce()`
- [ ] 2.2 Pasar `cerradas=cerradas` a la llamada de `procesar_cruce()`

## Phase 3: Frontend — Checkbox Cerradas

- [ ] 3.1 Agregar `fecha_cierre?: string | null;` a la interfaz `NoFacturadoItem` en `frontend/src/pages/ordenado-facturado/page.tsx`
- [ ] 3.2 Agregar checkbox "Cerradas" en el formulario (antes del botón Procesar), con estado local `cerradas: boolean`
- [ ] 3.3 En `handleSubmit`, agregar `if (cerradas) formData.append("cerradas", "true")` al FormData

## Phase 4: Tests — Verificar Filtro y Tolerancia

- [ ] 4.1 Agregar helper `_build_ayudas_rows_con_cierre()` que incluya columna `Fecha Cierre` en el mock de ayudas
- [ ] 4.2 Test: `cerradas=False` — todos los registros aparecen en `no_facturados` independientemente de `Fecha Cierre`
- [ ] 4.3 Test: `cerradas=True` — registros con `Fecha Cierre` vacío (None, `""`, NaN) excluidos
- [ ] 4.4 Test: `cerradas=True` — `total_no_facturado` y `totalizado` recalculados correctamente tras filtro
- [ ] 4.5 Test: columna `Fecha Cierre` ausente — no produce error, no se aplica filtro
- [ ] 4.6 Test: valores mixtos — algunos con fecha, otros sin ella, verificar que solo los vacíos se excluyen
- [ ] 4.7 Test: traslados también filtrados cuando `cerradas=True`
