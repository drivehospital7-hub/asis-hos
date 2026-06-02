# Design: Filtro por responsables en Abiertas Urgencias

## Technical Approach

Filtro `<select>` nativo en el frontend con opciones derivadas de `results[].responsable`. Sin cambios en backend. Sigue el mismo patrón de `control-novedades`: estado local `useState`, `useMemo` para valores únicos, `.filter()` inline antes del render.

## Architecture Decisions

### Decision: Copiar SOLO resultados filtrados

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Copiar filtrados | El usuario copia exactamente lo que ve. Inconsistencia: no puede copiar todo sin limpiar filtro. | ✅ **Elegido** — UX predecible (WYSIWYG). |
| Copiar todos | Siempre copia el dataset completo. | ❌ Inconsistente con lo visible. |

### Decision: Resetear filtro al reprocesar

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Reset en reproceso | Usuario pierde el filtro activo. | ✅ **Elegido** — previene estado colgado donde el filtro apunta a un responsable que ya no existe en los nuevos datos. |
| Mantener filtro | Si el responsable aún existe, el filtro sigue funcionando. | ❌ Riesgo de mostrar tabla vacía sin feedback claro. |

### Decision: `useMemo` para responsables únicos

Derivar lista de opciones con `useMemo` en vez de recalcular en cada render. `Set` para deduplicación con `|| "—"` para catch de valores falsy.

## Data Flow

```
results (FacturaResult[])
  │
  ├── useMemo #1 ──→ responsables (string[]) ──→ <select> options
  │
  ├── useMemo #2 ──→ filteredResults (FacturaResult[] | null)
  │       ↑ depends on: results + filterResponsable
  │
  ├── filteredResults.map(...) ──→ table rows
  ├── filteredResults.length ──→ counter
  └── copiarResultados(filteredResults, ...) ──→ clipboard TSV
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modify | +~40 líneas: estado, useMemo, select, filtered render, reset |
| `frontend/src/pages/abiertas-urgencias/utils.ts` | No change | `copiarResultados` acepta `FacturaResult[]` — funciona con subset |
| `frontend/src/pages/abiertas-urgencias/__tests__/utils.test.ts` | No change | `copiarResultados` no necesita cambios de interfaz |

## Interfaces / Contracts

Sin cambios en interfaces. `FacturaResult.responsable: string` ya existe.

## Changes Detail

### 1. Import `useMemo`

```tsx
// Line 1 — add useMemo to the import
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
```

### 2. New state (after line 101, junto a `showResults`)

```tsx
const [filterResponsable, setFilterResponsable] = useState("");
```

### 3. Derived data (antes del return, después de `showToast`)

```tsx
const responsables = useMemo(() => {
  if (!results) return [];
  return Array.from(new Set(results.map((r) => r.responsable || "—"))).sort();
}, [results]);

const filteredResults = useMemo(() => {
  if (!filterResponsable || !results) return results;
  return results.filter((r) => r.responsable === filterResponsable);
}, [results, filterResponsable]);
```

### 4. UI: `<select>` en el header de resultados

Insertar entre el `<div>` del contador (línea 571-579) y el botón "Copiar a Excel" (línea 580-587), antes del `</div>` que las envuelve:

```tsx
<div className="flex items-center gap-2">
  <select
    value={filterResponsable}
    onChange={(e) => setFilterResponsable(e.target.value)}
    className="h-9 rounded-md border border-input bg-background px-3 text-sm"
  >
    <option value="">Todos</option>
    {responsables.map((r) => (
      <option key={r} value={r}>{r}</option>
    ))}
  </select>
  <Button size="sm" variant="outline" onClick={handleCopiarResultados}>
    <ClipboardCopy className="h-4 w-4" />
    Copiar a Excel
  </Button>
</div>
```

### 5. Counter (línea 577)

```tsx
{(filteredResults ?? results ?? []).length} facturas
```

### 6. Table render (línea 616) + copiar (línea 441-448)

- `results.map(...)` → `(filteredResults ?? results).map(...)`
- `handleCopiarResultados` pasa `filteredResults ?? results` a `copiarResultados`

### 7. Reset en reprocesar

En `handleProcesarFacturas`, después de `setResults(...)` (línea 340):

```tsx
setFilterResponsable("");
```

## Edge Cases

| Case | Behavior |
|------|----------|
| `results` is null | `useMemo` returns `[]` → select solo muestra "Todos". Tabla no se renderiza (`showResults && results`). |
| `results` is empty array | `useMemo` returns `[]`. Select solo muestra "Todos". Tabla vacía. |
| `responsable` is `""` | `|| "—"` catch → aparece como "—" en el dropdown. |
| `responsable` is `undefined` | `|| "—"` catch. |
| Solo un responsable | Dropdown muestra "Todos" + 1 opción. |
| Filtrar y reprocesar | `setFilterResponsable("")` limpia el filtro al reprocesar. |
| Filtrar a un valor y que no haya resultados | Tabla sin filas, contador muestra 0. Select sigue mostrando el filtro activo. |

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `copiarResultados` con subset | Verificar que copia exactamente las filas pasadas. Sin cambios — `copiarResultados` ya acepta `FacturaResult[]`. |
| Manual | Comportamiento visual | No hay infraestructura de tests montados para page component. Verificar manualmente: cargar datos, filtrar, copiar, reprocesar. |

Casos de prueba manual:
1. Cargar datos con múltiples responsables → dropdown muestra "Todos" + cada responsable
2. Seleccionar un responsable → tabla filtra
3. "Copiar a Excel" copia solo filas visibles
4. Cambiar a "Todos" → tabla muestra todo
5. Reprocesar → filtro se resetea a "Todos"
6. Datos con "Sin Egreso" → aparece en dropdown
7. Solo 1 responsable → dropdown muestra "Todos" + 1 opción

## Migration / Rollout

No migration required. Cambio puramente frontend — deploy y ya.

## Open Questions

None.
