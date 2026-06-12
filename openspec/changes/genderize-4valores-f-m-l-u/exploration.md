# Exploration: Genderize 4 valores (F/M/L/U)

## Current State

### Flujo general

1. **Extracción** (`genderize_extractor.py`): Lee Excel, extrae `(numero_factura, primer_nombre, sexo)`.
   - `sexo` del Excel es `"M"` o `"F"` (mayúscula, tipado en `ExtractResult.sexo: str`)
   - El `nombre_normalizado` es solo `primer_nombre + segundo_nombre` (sin apellidos)

2. **Cache** (`genderize_service.py`): JSON en `app/data/genderize_cache.json`
   - **Estructura actual**: `{"nombre_normalizado": {"gender": "male"|"female"|null, "probability": float|null, "count": int|null}}`
   - `_load_cache()` → dict, `_save_cache()` → escribe JSON
   - `predict_genders()`: llama Genderize API. API retorna `"male"`, `"female"`, o `null`.
   - **Si API retorna `null`**, se guarda `null` en cache (`"gender": null`). **No se convierte a "undefined"**.
   - `override_gender(normalized_name, new_gender)`: Solo acepta `"male"` o `"female"`.
   - "Hijo de"/"Hija de": fuerza gender sin API call.

3. **Verificación** (`genderize_verifier.py`):
   - `verificar_y_comparar()`: Compara `sexo_excel` (M/F) vs `sexo_api` (male/female/null).
   - **Mapeo actual**: `"male"` → `"M"`, `"female"` → `"F"`, cualquier otro → `"?"`.
   - **Comportamiento crítico**: si `sexo_api_code == "?"` → `continue` (salta la discrepancia).
   - `Discrepancia.sexo_api: str` — actualmente solo `"M"` o `"F"`.
   - **No llegan discrepancias con null/undefined al frontend.**

4. **Endpoint `/api/import/cache-corregir`** (`import_facturas.py:178`):
   - Recibe `{nombre_normalizado, genero}`.
   - **Validación actual**: `new_gender` debe estar en `("m", "male", "f", "female")`.
   - Normaliza a `"male"` o `"female"`.

5. **Frontend** (`frontend/src/pages/genderize/page.tsx`):
   - **Tabla de discrepancias**: Número Factura, Nombre Completo, Sexo Excel, Sexo API, Acción.
   - **UI de corrección**: Botón único "Corregir → {sexo_excel}". NO hay dropdown/select.
   - `corrigeGenero(nombreNormalizado, sexoExcel)` envía `sexo_excel` directamente como corrección.
   - No hay opción para elegir un valor diferente al del Excel.

### Resumen de limitaciones actuales

| Aspecto | Hoy | Necesitado |
|---------|-----|------------|
| Valores válidos | male/female | female/male/lastname/undefined |
| Discrepancias null | Saltadas | Mostradas como "U" |
| UI corrección | Botón único (usa sexo Excel) | Dropdown con F/M/L/U |
| Cache null | Guarda null | Debería guardar "undefined" |
| API `override_gender` | Solo male/female | Todos 4 valores |

---

## Affected Areas

| Archivo | Rol | Cambio necesario |
|---------|-----|------------------|
| `app/constants/base.py` | Constantes | Añadir `GENDER_*` constants — cortas y largas |
| `app/services/genderize_service.py` | Cache + API | `predict_genders`: guardar null como "undefined". `override_gender`: aceptar últimos 2. |
| `app/services/genderize_verifier.py` | Comparación | Dejar de saltar "?". Mapear 4 valores. Sexo API en Discrepancia debe mostrar F/M/L/U. |
| `app/routes/import_facturas.py` | Endpoint | Validar 4 valores en `cache-corregir`. |
| `frontend/src/pages/genderize/page.tsx` | UI | Botón → dropdown con F/M/L/U. Mostrar todas las discrepancias. |
| `tests/services/test_genderize_verifier.py` | Tests | Actualizar tests existentes + nuevos escenarios |
| `test_genderize.py` | Test manual | Actualizar imports rotos (tiene `from app.services. import`) |

---

## Approaches

### Approach 1: Cambio mínimo — solo backpressure en cache

Agregar "lastname" y "undefined" como valores válidos en cache/endpoint sin cambiar la UI significativamente. El frontend solo agrega los 2 valores extra al dropdown existente.

- **Pros**: Rápido de implementar. Mínimo riesgo de regresión.
- **Cons**: La UI de corrección sigue siendo primitiva (usar sexo_excel como default puede ser incorrecto para undefined). No se gana mucho sin una UI mejorada.
- **Effort**: Medium

### Approach 2: Cambio completo — UI de corrección con dropdown + 4 valores (RECOMENDADO)

Implementar todo el cambio:
1. Constantes + validación backend para 4 valores
2. `verificar_y_comparar()`: incluir null/undefined como discrepancias (con valor "U")
3. `cache-corregir`: aceptar F/M/L/U + long forms
4. Frontend: dropdown con 4 opciones en vez de botón único
5. Cache: guardar null como "undefined" (migración transparente en `_load_cache`)

- **Pros**: Solución completa. UX correcta. Permite "alimentar la db" como pide el usuario. Backward compatible (cache existente con "male"/"female" sigue funcionando).
- **Cons**: Más cambios, toca frontend y backend.
- **Effort**: Medium (2-3 archivos backend, 1 archivo frontend, tests)

### Approach 3: Migrar cache a códigos cortos (F/M/L/U)

Almacenar en cache directamente los short codes "F"/"M"/"L"/"U" en vez de los full words.

- **Pros**: Consistente con lo que ve el usuario. Simplifica frontend.
- **Cons**: **Rompe cache existente** — migración forzada. Genderize API retorna "male"/"female", habría que mapear en cada lectura.
- **Effort**: High (migración, más complejidad)
- **Riesgo**: Alto — datos existentes podrían perderse si la migración falla.

---

## Recommendation

**Approach 2** — Cambio completo con backward compatibility.

### Detalle técnico

**Valores canónicos en cache** (seguir el patrón existente de full words):

| Código corto | Valor en cache | Origen |
|:---:|---|---|
| F | `"female"` | API Genderize / Manual |
| M | `"male"` | API Genderize / Manual |
| L | `"lastname"` | Manual override (es apellido, no nombre) |
| U | `"undefined"` | API retornó null / Manual override |

**Mapeo bidireccional**:
- `display: "F"` ↔ `cache: "female"`
- `display: "M"` ↔ `cache: "male"`
- `display: "L"` ↔ `cache: "lastname"`
- `display: "U"` ↔ `cache: "undefined"`

**Cambios específicos**:

1. **`app/constants/base.py`** — añadir:
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

2. **`genderize_service.py`**:
   - `predict_genders()`: cuando API retorna `null`, guardar `"undefined"` en cache
   - `override_gender()`: aceptar short o long, normalizar a long
   - `_load_cache()`: mapear `null` legacy a `"undefined"`

3. **`genderize_verifier.py`**:
   - `verificar_y_comparar()`: mapear `"male"`→`"M"`, `"female"`→`"F"`, `"lastname"`→`"L"`, `"undefined"`→`"U"`
   - Eliminar el `continue` para `"?"` — ahora "U" es un valor válido y se muestra
   - `Discrepancia.sexo_api`: documentar que ahora puede ser F/M/L/U

4. **`import_facturas.py`**:
   - `cache-corregir`: validar los 4 valores (short o long), normalizar a long

5. **`frontend/src/pages/genderize/page.tsx`**:
   - Reemplazar el botón "Corregir → {sexo_excel}" con un dropdown que tenga F/M/L/U
   - Pre-seleccionar el valor actual (sexo_excel) en el dropdown
   - Para "U" (API no pudo clasificar), mostrar el dropdown sin preselección o con "U" como default
   - El dropdown debe permitir al usuario elegir y luego aplicar la corrección

### Secuencia de UI esperada:

```
[Discrepancia]                    [Acción]
FAC-001  Juan Pérez   Excel: M   API: F  →  [Select: F ▼] [Aplicar]
FAC-002  María López  Excel: F   API: M  →  [Select: F ▼] [Aplicar]
FAC-003  José García  Excel: M   API: U  →  [Select: M ▼] [Aplicar]
```

### Secuencia de Events/Commands:

```
Frontend Select [M ▼]
  → fetch POST /api/import/cache-corregir {nombre_normalizado, genero: "M"}
  → Backend valida: "M" → normalize → "male" 
  → override_gender(nombre, "male") → cache[nombre]["gender"] = "male"
  → Frontend refresca resultados
```

---

## Risks

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Backward compatibility cache existente** | Medio — cache con "male"/"female" sigue funcionando. Cache con `null` legacy se mapea en `_load_cache`. | El mapeo `null`→`"undefined"` debe hacerse en `_load_cache` para que migre automáticamente. |
| **API Genderize sigue retornando null** | Bajo — ahora se mapea a "U" en vez de saltarse. Es el comportamiento deseado. | N/A |
| **Frontend: dropdown en vez de botón** | Medio — hay que decidir diseño del dropdown. ¿Select nativo o componente shadcn? | Usar `<select>` nativo o `<Select>` de shadcn/ui si ya está disponible. |
| **"L" no tiene origen API** | Bajo — "lastname" es solo manual override. La API nunca retorna este valor. | Documentar en el dropdown que "L" es para casos donde el "nombre" es realmente un apellido. |
| **Tests existentes** | Bajo — `test_genderize_verifier.py` usa `sexo="M"` hardcodeado en fixtures. Los tests de `predict_genders` no existen en el repo actual. | Actualizar fixtures y añadir nuevos tests para los 4 valores. |

---

## Ready for Proposal

**Sí** — listo para pasar a `sdd-propose`.

La exploración es clara:
- Hay 5-6 archivos que tocar (contando constants y tests)
- El cambio es **backward compatible** — el cache existente con "male"/"female" NO se rompe
- El frontend requiere el cambio más visible (botón → dropdown) pero es código React estándar
- No hay dependencias externas nuevas
- No hay cambios de API externa (Genderize API no cambia)
- El effort total estimado: **Medium** (unas horas de implementación)
