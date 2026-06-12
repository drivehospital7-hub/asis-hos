# Exploration: Export no-cache con genero del Excel y eliminar dependencia de API Genderize

## Current State

### Change 1 — Export format

Hoy el botón "Exportar no-cache" produce un `.txt` con nombres separados por coma:

```
maria carmela,nerci beatriz,rosalba
```

El flujo es:

1. `genderize_verifier.py::get_stats()` retorna `(Stats, dict[str, ExtractResult], list[str])`
   - 3er elemento: `nombres_no_cache` — solo los `compound_name` de pacientes sin cache
   - No incluye el sexo del Excel (disponible en `ExtractResult.sexo` pero no se envía)
2. Route `/api/import/facturas-stats` manda `nombres_no_cache: string[]`
3. Frontend `exportNoCache()`: `"\uFEFF" + names.join(", ")`

El `ExtractResult.sexo` (M/F) está en el dict `facturas` (2do return de `get_stats()`) pero nunca viaja al frontend en este endpoint.

### Change 2 — API Genderize

**`predict_genders()`** en `genderize_service.py` es la única función que hace llamadas HTTP:

```
predict_genders(names: list[str]) → tuple[list[GenderResult], RateLimitInfo | None]
```

Flujo actual:
1. Clasifica "Hijo de"/"Hija de" vía `_classify()` — 100% local ✅
2. Cache hit → retorna valor cacheado inmediatamente
3. Cache miss → agrega a lista `api_names`
4. Si hay `api_names`: construye URL con `urllib.parse.urlencode`, llama `urllib.request.urlopen()`
   - En batches (todos juntos, API recibe `name[0]`, `name[1]`, ... en un request)
   - Retry con backoff 1s/2s/4s para 429 Too Many Requests
   - Lee headers `X-Rate-Limit-*` para info de rate limiting
   - Guarda resultados en cache local (`genderize_cache.json`)
   - Retorna `RateLimitInfo` si hubo API call
5. Ordena resultados igual al input original

**Dependencias de red**: solo stdlib `urllib.request`, `urllib.parse`, `urllib.error`. NO hay third-party.

**Variables de entorno**:
- `GENDERIZE_API_KEY` (opcional)
- `GENDERIZE_COUNTRY_ID` (default "CO")

**`verificar_y_comparar()`** llama `predict_genders()` en batches de 10 para uncached names.

**`genderize_api.py`** es una ruta test `/api/genderize/` que consulta `predict_genders()` con 10 nombres fijos.

## Affected Areas

| Archivo | Change 1 | Change 2 | Por qué |
|---------|----------|----------|---------|
| `app/services/genderize_service.py` | ❌ | ✅ | Eliminar bloque API call + imports (urlopen, urlencode, HTTPError, time, os), simplificar predict_genders() a solo cache lookup |
| `app/services/genderize_verifier.py` | ✅ | ✅ | get_stats(): incluir sexo en nombres_no_cache. Verificar_y_comparar: eliminar batching, simplificar stats |
| `app/routes/import_facturas.py` | ✅ | ✅ | Response stats: cambiar formato incluyendo sexo. Remover HTTPError handling (ya no hay API call). Remover token display |
| `app/routes/genderize_api.py` | ❌ | ✅ | Eliminar ruta completa — pierde sentido sin API |
| `frontend/src/pages/genderize/page.tsx` | ✅ | ✅ | Export handler: formato tab-separado con sexo. Remover contador de tokens. Simplificar labels |
| `app/constants/base.py` | ❌ | ❌ | No tocar — no tiene constantes de API |
| `tests/services/test_genderize_service.py` | ❌ | ✅ | 3 tests de predict_genders que mockean urlopen → reescribir como tests de cache-miss→undefined |
| `tests/services/test_genderize_verifier.py` | ✅ | ✅ | Tests de get_stats + verificar_y_comparar con los nuevos formatos |

## Approaches

### Change 1: Export con género (tab-separado)

**Enfoque A (Recomendado): Extender nombres_no_cache a pares nombre+sexo**

Cambiar `get_stats()` para que retorne cada entrada como `(compound_name, sexo)`:

```python
# genderize_verifier.py
nombres_no_cache: list[tuple[str, str]] = []  # (nombre, sexo)
for r in facturas.values():
    if r.nombre_normalizado in nombres_hijo:
        continue
    if r.nombre_normalizado not in cache:
        compound_name = f"{r.primer_nombre} {r.segundo_nombre}".strip() if r.segundo_nombre else r.primer_nombre
        nombres_no_cache.append((_normalize(compound_name), r.sexo))
```

Route response cambia de `string[]` a `array[{nombre: string, sexo: string}]`:

```json
{
  "nombres_no_cache": [
    {"nombre": "maria carmela", "sexo": "F"},
    {"nombre": "nerci beatriz", "sexo": "F"}
  ]
}
```

Frontend:
```tsx
interface NombreSexo {
  nombre: string;
  sexo: string;
}
nombres_no_cache: NombreSexo[];
```

Export handler:
```tsx
const text = "\uFEFF" + (statsPreview?.nombres_no_cache ?? [])
  .map(item => `${item.nombre}\t${item.sexo}`)
  .join(", ");
// → maria carmela\tF,nerci beatriz\tF,rosalba\tF
```

Pros:
- Datos viajan juntos, sin lookup extra
- Mínimo cambio en backend y frontend
- El normalize ya se aplica (minúsculas, sin tildes)

Cons:
- Breaking change al response format del endpoint stats
- Effort: **Low** (~3 files)

**Enfoque B: Enviar facturas map separado**

Enviar `facturas` dict + `nombres_no_cache` por separado. Frontend hace lookup.

Pros: No breaking change al array
Cons: Más complejo en frontend, doble lookup
Effort: Low-Medium — **descartado**

### Change 2: Eliminar API Genderize

**Enfoque A (Recomendado): predict_genders() local-only + simplificar**

1. En `genderize_service.py`:
   - Eliminar imports: `urlopen`, `urlencode`, `Request`, `HTTPError`, `time`, `os` (API key)
   - Eliminar variables: `GENDERIZE_API_URL`, `GENDERIZE_API_KEY`, `GENDERIZE_COUNTRY_ID`
   - Eliminar dataclass `RateLimitInfo`
   - Simplificar `predict_genders()`:
     - Cache hit → GenderResult con valor cacheado
     - Cache miss → GenderResult(gender="undefined", probability=None, count=None)
     - NO guarda en cache los misses
     - Retorna siempre `rate_limit=None`

2. En `genderize_verifier.py`:
   - `verificar_y_comparar()`: eliminar batching (ya no hay rate limit), simplificar stats
   - `Stats.api_calls_necesarias` renombrar o dejar como 0

3. Eliminar `genderize_api.py` y su blueprint del app factory

4. En `import_facturas.py`:
   - Eliminar import de `HTTPError`
   - Eliminar bloque `except HTTPError`
   - Remover contador de tokens de la respuesta

5. Frontend:
   - Remover `(N tokens)` del botón Verificar
   - Remover columna "API calls" de stats o renombrar a "Sin cache"
   - Simplificar texto del botón

6. Tests:
   - `test_genderize_service.py` TestPredictGendersUndefinedOnNull: reescribir tests para que no mockeen urlopen — ahora predict_genders es local
   - Test: cache miss → gender="undefined", probability=None, count=None
   - Test: cache hit → devuelve valor cacheado
   - Test: Hijo de / Hija de → forced gender

Pros:
- Código más simple: sin red, sin retry, sin try/except
- Sin dependencia de API externa ni rate limiting
- Flujo 100% determinista y local
- Effort: **Medium** (~5 archivos + tests)

Cons:
- Cache no crece automáticamente (solo vía override_gender manual)
- Nombres nuevos siempre aparecen como "U" hasta corrección manual
- Tests existentes que mockean urlopen deben reescribirse

## Recommendation

**Combinar ambos cambios en un solo SDD. Orden de implementación: Change 2 (eliminar API) primero, luego Change 1 (export con género).**

Razones:
1. Archivos superpuestos — hacerlo por separado causa re-trabajo en `genderize_verifier.py`
2. El export sin API es más coherente cuando no hay API que consultar
3. Ambos cambios individuales son pequeños (< 100 líneas cada uno)

### Detalle de implementación recomendado

**Predict genders local-only** — reemplazar el bloque de API call con asignación directa:

```python
# genderize_service.py — predict_genders() simplificado
def predict_genders(names: list[str]) -> tuple[list[GenderResult], None]:
    """Predict gender con cache local SOLO. Sin API."""
    if not names:
        return [], None

    cache = _load_cache()
    results: list[GenderResult] = []

    for original in names:
        original, forced = _classify(original)
        normalized = _normalize(original)

        if normalized in cache:
            cached = cache[normalized]
            results.append(GenderResult(
                name=original,
                gender=forced or cached["gender"],
                probability=cached["probability"],
                count=cached["count"],
            ))
        else:
            # Cache miss → undefined (sin API call)
            results.append(GenderResult(
                name=original,
                gender=forced or "undefined",
                probability=None,
                count=None,
            ))

    return results, None
```

**Export format** — cambio en la respuesta de stats:

```json
{
  "nombres_no_cache": [
    {"nombre": "maria carmela", "sexo": "F"},
    {"nombre": "nerci beatriz", "sexo": "F"},
    {"nombre": "rosalba", "sexo": "F"}
  ]
}
```

## Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Nombres sin cache = U** | Medio — deseado, pero usuarios deben entender que no hay auto-aprendizaje. El cache solo crece con correcciones manuales. | Comunicar claramente en el cambio. El flujo "Verificar → identificar U → corregir vía dropdown" debe ser intuitivo. |
| **Breaking change response stats** | Bajo — equipo chico, frontend y backend se deployan juntos. | Coordinar deploy. Si hay versiones anteriores del frontend, se rompe el botón exportar. |
| **`genderize_api.py` eliminado** | Bajo — era solo una ruta de prueba. Nadie la usa en producción. | Simplemente eliminar. Si alguien la necesita, se puede recrear como local-only. |
| **Tests existentes de predict_genders** | Medio — 3 tests que mockean urlopen deben reescribirse. | Son tests unitarios de `test_genderize_service.py`, fáciles de actualizar. |
| **Cache actual con entries legacy null** | Bajo — `_load_cache()` ya mapea null → "undefined" en memoria. | No hay riesgo. |
| **Import rotos en `test_genderize.py` (raíz)** | Bajo — archivo suelto con `from app.services. import`. Ya está roto. | Aprovechar y arreglarlo o eliminarlo. |

## Ready for Proposal

**Sí** — exploration completa. El cambio está bien definido:

- **Archivos a modificar**: 6-7 (genderize_service.py, genderize_verifier.py, import_facturas.py, genderize_api.py, page.tsx, 2 test files)
- **Effort combinado**: Low-Medium (~150-200 líneas total)
- **Backward compatibility**: El cache existente NO se modifica. El response format de stats cambia (breaking controlado).
- **No hay nuevas dependencias** — todo es eliminar código y simplificar.

El orquestador debe informar al usuario que:
1. Los nombres sin cache pasarán a ser "U" (undefined) — no más auto-consulta a Genderize
2. El cache solo crecerá por correcciones manuales vía dropdown F/M/L/U
3. La ruta de test `/api/genderize/` será eliminada
4. El export cambiará de `nombre,nombre` a `nombre\tF,nombre\tM,...`
5. El botón "Verificar" seguirá existiendo pero sin contador de tokens (ya no hay API calls)
