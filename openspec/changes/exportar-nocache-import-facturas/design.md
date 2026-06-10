# Design: Botón "exportar no-cache" en /import-facturas

## Technical Approach

Extender `get_stats()` para que retorne la lista de nombres sin cache como tercer valor en la tupla. El endpoint `POST /api/import/facturas-stats` incluye `nombres_no_cache` en la respuesta JSON. El frontend recibe el array y, si no está vacío, muestra un botón que construye un Blob client-side y gatilla el download — sin round-trip extra.

No se crean rutas nuevas. No se toca el cache system.

## Architecture Decisions

### Decision: Extender endpoint existente vs ruta nueva

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Extender `facturas-stats` | +0 round-trips, datos ya computados, sin auth duplicada | ✅ **Elegido** |
| Ruta `/api/import/facturas-nocache` | +1 request, duplica lógica de cache check | ❌ Descartado |

**Rationale**: `get_stats()` ya itera todos los nombres contra el cache. Agregar el listado de los que no están tiene costo ~0 — son los que no entraron en `cache_hits`. Crear una ruta separada forzaría a re-subir el archivo o a pasar el listado en el body, duplicando login y estado.

### Decision: Blob download client-side vs archivo server-side

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Blob JS client-side | 0 server load, instantáneo, sin archivos temporales | ✅ **Elegido** |
| Generar .txt en servidor y devolver como download | +escritura/limpieza en tmp, +latencia, +complejidad en ruta | ❌ Descartado |

**Rationale**: Los datos ya están en el frontend. Generar un Blob con `text/plain` y usar un `download` link es ~5 líneas de JS. Mandarlo al server y volver agrega latencia y complejidad sin beneficio.

## Data Flow

```
Usuario sube .xlsx
       │
       ▼
fetch("/api/import/facturas-stats")   [POST]
       │
       ▼
genderize_verifier.get_stats(path)
  ├── extrae nombres del Excel
  ├── carga cache
  ├── computa cache_hits
  ├── deriva nombres_no_cache = unique_names - cache_hits
  └── retorna (Stats, facturas, nombres_no_cache)
       │
       ▼
Route arma JSON: { ...data: { ..., nombres_no_cache: [...] } }
       │
       ▼
Frontend recibe → setStatsPreview(data)
       │
       ▼
Si data.nombres_no_cache.length > 0 → muestra "Exportar no-cache"
       │
       ▼
Click → Blob("\uFEFF" + names.join(", "), {type: "text/plain"})
       → <a download="nombres_no_cache.txt">
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/services/genderize_verifier.py` | Modify | `get_stats()` retorna `nombres_no_cache: list[str]` como tercer elemento; `Stats` dataclass no se toca |
| `app/routes/import_facturas.py` | Modify | Incluir `nombres_no_cache` en JSON de `/api/import/facturas-stats` |
| `frontend/src/pages/genderize/page.tsx` | Modify | Añadir campo `nombres_no_cache` en `StatsData` interface; botón "Exportar no-cache" condicional; handler Blob download |

## Interfaces / Contracts

```python
# genderize_verifier.py — antes
def get_stats(excel_path: str) -> tuple[Stats, dict[str, ExtractResult]]:

# después
def get_stats(excel_path: str) -> tuple[Stats, dict[str, ExtractResult], list[str]]:
    # tercer elemento: nombres_no_cache (compound_name, orden de archivo)
```

```python
# StatsResponse (implícito en la ruta)
{
    "status": "success",
    "data": {
        "total_excel": int,
        "nombres_unicos": int,
        "cache_hits": int,
        "api_calls_necesarias": int,
        "nombres_no_cache": list[str],     # ← NUEVO
    },
    "errors": []
}
```

```typescript
// page.tsx
interface StatsData {
  total_excel: number;
  nombres_unicos: number;
  cache_hits: number;
  api_calls_necesarias: number;
  nombres_no_cache: string[];   // ← NUEVO
}
```

## Key Implementation Details

**Backend — `get_stats()`**: Después de clasificar nombres como cache hit o miss, construir `nombres_no_cache` preservando el orden de aparición en el archivo. En lugar de iterar sobre `unique_names` (un set sin orden), iterar sobre `facturas.values()` y por cada `r.nombre_normalizado` no presente en cache, agregar su `compound_name` original.

```python
# Modo de construcción (dentro de get_stats)
compound_name = f"{r.primer_nombre} {r.segundo_nombre}".strip() if r.segundo_nombre else r.primer_nombre
# Se obtiene de ExtractResult igual que en genderize_extractor.py
```

**Frontend — export handler**:
```tsx
const exportNoCache = () => {
  const text = "\uFEFF" + (statsPreview?.nombres_no_cache ?? []).join(", ");
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "nombres_no_cache.txt";
  a.click();
  URL.revokeObjectURL(url);
};
```

**Botón**: Se renderiza dentro del `Card` de stats preview, junto a los botones existentes, solo si `statsPreview?.nombres_no_cache?.length > 0`. Sigue el mismo estilo que los otros botones (className con `flex items-center gap-1.5`).

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (backend) | `get_stats()` retorna `nombres_no_cache` con `compound_name` correctos | pytest: test_genderize_verifier.py — mock cache con nombres conocidos, verificar que los que no están en mock aparecen en la lista |
| Unit (backend) | Tupla unpacking no se rompe | pytest: test que el tercer elemento es `list[str]` y tiene la longitud esperada |
| Manual (frontend) | Botón visible/invisible según response | Navegador: cargar archivo, ver botón, hacer clic, verificar .txt descargado |
| Manual (frontend) | Formato del .txt | Abrir descarga en bloc de notas: verificar coma+espacio, sin trailing comma, UTF-8 BOM |

## Migration / Rollout

No migration required. Rollback: revertir cambios en los 3 archivos. El campo extra en la respuesta es ignorado por frontends anteriores (no rompe).

## Open Questions

None.
