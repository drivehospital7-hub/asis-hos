# Design: Cerradas Toggle — Ordenado y Facturado

## Technical Approach

Añadir columna opcional `Fecha Cierre` a los headers de Ayudas. Cuando `cerradas=True`, filtrar `no_facturados` post-construcción, eliminando registros con fecha vacía. Recalcular `total_no_facturado` y los valores por categoría en `totalizado`. La ruta lee el checkbox del form data. El frontend agrega un checkbox "Cerradas" antes del botón Procesar.

El filtro es **post-hoc** sobre la lista ya construida — no modifica la lógica de matching, dedup, ni agregación existente.

## Architecture Decisions

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Filtrar en servicio vs en ruta | Ruta sería punto único pero rompe SRP (filtrar datos ≠ enrutar) | **Servicio**: `procesar_cruce()` recibe `cerradas: bool = False` |
| Filtrar durante matching vs post-hoc | Durante matching ahorra loop extra pero acopla lógica de filtro con matching | **Post-hoc**: después de construir `no_facturados` completo, filter + recount |
| Añadir `Fecha Cierre` a `AYUDAS_OPTIONAL_HEADERS` vs detectar aparte | Detectar aparte duplica patrón existente | **AYUDAS_OPTIONAL_HEADERS**: mismo patrón que `paciente` y `profesional_solicito` |
| Recalcular `totalizado` desde `conteo_ayudas` vs recontar desde `no_facturados` filtrados | Recontar desde `no_facturados` evita session state | **Recontar desde `no_facturados` filtrados**: simple, correcto, sin estado lateral |

## Data Flow

```
Frontend                    Route                         Service
  │                          │                              │
  ├─ checkbox "Cerradas" ──→│                              │
  │   formData("cerradas")  │                              │
  │                          ├─ request.form.get() ───────→│
  │                          │   cerradas=True/False       │
  │                          │                              ├─ detectar Fecha Cierre
  │                          │                              ├─ construir no_facturados
  │                          │                              │   (incluye fecha_cierre)
  │                          │                              ├─ construir totalizado
  │                          │                              ├─ si cerradas:
  │                          │                              │   filter no_facturados
  │                          │                              │   recount por categoría
  │                          │                              │   actualizar totalizado
  │                          │                              └─ retornar
  │                          │                              │
  │                          │←──── JSON response ──────────│
  │←──── render result ─────│                              │
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/ordenado_facturado_service.py` | Modify | +`Fecha Cierre` opcional, +param `cerradas`, +filtro post-hoc, +recount totalizado |
| `app/routes/ordenado_facturado.py` | Modify | Leer `request.form.get("cerradas")`, pasar a `procesar_cruce()` |
| `frontend/src/pages/ordenado-facturado/page.tsx` | Modify | +checkbox "Cerradas" en el form, +append a FormData si checked |
| `tests/services/test_ordenado_facturado_service.py` | Modify | +tests: cerradas ON/OFF, columna faltante, vacíos mixtos |

## Interfaces / Contracts

```python
# ── Service signature (modified) ──
def procesar_cruce(
    path_reporte: Path,
    path_ayudas: Path,
    path_notas: Path | None = None,
    cerradas: bool = False,          # ← NEW
) -> dict[str, Any]:
```

```typescript
// ── Frontend: FormData addition (inside handleSubmit) ──
const cerradasEl = document.getElementById("cerradas") as HTMLInputElement;
if (cerradasEl?.checked) {
  formData.append("cerradas", "true");
}
```

```typescript
// ── NoFacturadoItem (incluye fecha_cierre opcional) ──
interface NoFacturadoItem {
  // ... existing fields
  fecha_cierre?: string | null;  // ← NEW, opcional
}
```

## Implementation Detail — Filtro post-hoc

Insertar después de la construcción de `no_facturados` (incluyendo traslados) y antes de `total_no_facturado = len(no_facturados)`:

```python
if cerradas and idx_fecha_cierre is not None:
    before = len(no_facturados)
    no_facturados = [
        r for r in no_facturados
        if r.get("fecha_cierre") is not None
        and str(r["fecha_cierre"]).strip() not in ("", "nan", "NaN", "NAN")
    ]

    # Recontar por código desde lista filtrada
    nuevo_conteo: dict[str, int] = {}
    for item in no_facturados:
        cups = _normalizar_codigo(item["cups"])
        if cups:
            nuevo_conteo[cups] = nuevo_conteo.get(cups, 0) + 1

    # Actualizar totalizado rows (solo total_no_facturado cambia)
    CATEGORY_CODE_MAP = {
        "PARTO": PROCESADOS_PARTO,
        "INTERCONSULTAS": PROCESADOS_INTERCONSULTAS,
        "OTROS": PROCESADOS_OTROS,
        "TRASLADOS": CODIGOS_EXCEPCION,
    }
    for trow in totalizado:
        codeset = CATEGORY_CODE_MAP.get(trow["codigo"])
        if codeset:
            trow["total_no_facturado"] = sum(
                nuevo_conteo.get(c, 0) for c in codeset
            )
```

Los casos `Fecha Cierre = NaN` vienen de Excel como float NaN, que Polars lee como `float('nan')` en el raw list-of-lists. El chequeo con `str().strip()` cubre `None`, `""`, y `nan`.

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Cerradas ON filtra vacíos | Mock `_leer_como_raw` con columna `Fecha Cierre`, verificar `no_facturados` excluye rows con None/""/NaN |
| Unit | Cerradas OFF = unchanged | Mismos datos, `cerradas=False`, verificar idéntico a antes |
| Unit | Columna faltante tolerada | Ayudas sin `Fecha Cierre`, `cerradas=True`, no error |
| Unit | totalizado recalculado | Verificar `PARTO.total_no_facturado` baja después de filtro |
| Unit | TRASLADOS también filtrado | Notas data + excepción codes, verificar filtro aplica |
| Integration | Route acepta form param | Request POST con `cerradas="true"`, status success |
| E2E | Frontend checkbox presente | Render test, checkbox existe y checked por defecto = false |

## Migration / Rollout

No migration required. Un solo commit atómico.

## Open Questions

None.
