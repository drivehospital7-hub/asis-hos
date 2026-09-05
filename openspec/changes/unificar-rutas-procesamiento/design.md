# Design: Unificar rutas POST en `/procesar/`

## Technical Approach

Eliminar los 3 POST handlers duplicados (`/urgencias/`, `/odontologia/`, `/odontologia-equipos-basicos/`) y reescribir `POST /procesar/` para que retorne JSON en lugar de HTML. El nuevo handler acepta todos los parámetros de los 3 frontends, llama a `detect_problems_only(area=AREA_UNIFICADA, ...)` y retorna errores agrupados por `tipo_error` con el mismo formato JSON existente.

Los GET handlers (React shell) se mantienen intactos — solo se eliminan los POST de cada blueprint.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Área de detección | `AREA_UNIFICADA` siempre | Enviar `area` como form field | `AREA_UNIFICADA` auto-detecta los tipos de factura (Urgencias, Odontología, etc.) y despacha al orquestador correcto. Unifica sin requerir cambios en los frontends. |
| Respuesta del handler | JSON puro | HTML (como hoy) | Los 3 frontends React esperan JSON. El GET `/` sigue sirviendo el template HTML para debugging. |
| Parámetros aceptados | Todos los de los 3 handlers | Solo los necesarios por área | Pasarlos todos a `detect_problems_only`; los no relevantes se ignoran internamente. Evita if/else en la ruta. |
| Cleanup temp file | `finally` implícito (antes de cada return) | Bloque try/finally | Los 3 handlers actuales hacen cleanup antes de cada return. Consistente con el patrón existente. |
| Template `procesar.html` | Mantener | Eliminar | El GET `/` aún lo renderiza para debugging. No duele tenerlo. |

## Data Flow

```
Frontend (React)                     Flask Route                         Services
─────────────────                    ──────────────────                  ───────────────────
                                                                          
Urgencias POST /procesar/      →    procesar_bp.post("/")          →    detect_problems_only(
  file_upload                          @rate_limit(1,120)                    area=AREA_UNIFICADA,
  (sin parámetros extra)               @permiso_requerido(                   profesional="",
                                       "urgencias",                          dias=[],
Odontología POST /procesar/            "odontologia",                        ...)
  file_upload                          "odontologia_equipos_basicos")
  profesional                                                          →    _do_detect_problems()
  dias_seleccionados                                                        →    process_unified()
  todos_profesionales_dias                                                       → detect_all (por tipo)
  validar_centro_costo                                                          → normaliza filas
                                                                          ←    {status, data, errors}
Equipos Básicos POST /procesar/    cleanup_temp_excel(temp_path)
  file_upload                                                                
  (sin parámetros extra)          ←    jsonify({errores agrupados})
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/routes/procesar.py` | Modify | Reemplazar POST handler HTML → JSON. Agregar `@rate_limit`, `@permiso_requerido` con 3 permisos. Aceptar todos los form fields. Retornar JSON grouped. |
| `app/routes/urgencias.py` | Modify | Eliminar POST handler `export_urgencias` (líneas 63-206). Mantener GET + `_get_manifest_asset`. Remover imports no usados. |
| `app/routes/excel_headers.py` | Modify | Eliminar POST handler `export_cruce_facturas` (líneas 64-211). Mantener GET. Remover imports no usados. |
| `app/routes/odontologia_equipos_basicos.py` | Modify | Eliminar POST handler `export_cruce_eb` (líneas 64-168). Mantener GET. Remover imports no usados. |
| `frontend/src/pages/urgencias/page.tsx` | Modify | L61: cambiar `fetch("/urgencias/", ...)` → `fetch("/procesar/", ...)` |
| `frontend/src/pages/odontologia/page.tsx` | Modify | L69: cambiar `fetch("/odontologia/", ...)` → `fetch("/procesar/", ...)` |
| `frontend/src/pages/odontologia-equipos-basicos/page.tsx` | Modify | L64: cambiar `fetch("/odontologia-equipos-basicos/", ...)` → `fetch("/procesar/", ...)` |
| `tests/services/test_urgencias_routes.py` | Modify | Cambiar URLs de POST de `/urgencias/` a `/procesar/` |
| `tests/services/test_excel_headers_routes.py` | Modify | Cambiar URLs de POST de `/odontologia/` a `/procesar/` |
| `app/templates/procesar.html` | Keep | Sin cambios. GET `/` lo usa para debugging. |

## Interfaces / Contracts

### POST /procesar/ — Request

Form-data (multipart):

| Field | Type | Required | Origin |
|-------|------|----------|--------|
| `file_upload` | File | Sí | Todos |
| `sheet_name` | str | No | (reservado) |
| `profesional` | str | No | Odontología |
| `dias_seleccionados` | str (csv) | No | Odontología |
| `todos_profesionales_dias` | str (JSON) | No | Odontología |
| `validar_centro_costo` | str ("on") | No | Odontología |

### POST /procesar/ — Response (success)

```json
{
  "status": "success",
  "data": {
    "errores": [
      {
        "tipo": "Decimales",
        "tipo_key": "norm_decimales",
        "cantidad": 10,
        "cantidad_mostradas": 10,
        "facturas": [
          {"factura": "...", "fec_factura": "...", "responsable_cierra": "...",
           "descripcion": "...", "procedimiento": "...", "detalle": "..."}
        ]
      }
    ],
    "total_errores": 10,
    "columnas": ["Fec. Factura", "Tipo de error", "Número Factura",
                 "Responsable Cierra", "Descripción", "Procedimiento", "Detalle"]
  },
  "errors": []
}
```

### POST /procesar/ — Response (missing columns)

```json
{
  "status": "error",
  "data": {},
  "errors": ["Columnas no encontradas en el Excel: ..."],
  "missing_columns": ["Nº Identificación", ...]
}
```

### POST /procesar/ — Response (rate limited)

```json
{
  "status": "error",
  "data": {},
  "errors": ["Demasiadas solicitudes. Espere 45 segundos."]
}
```

## Decorator Stack

```python
@procesar_bp.post("/")
@rate_limit(1, 120, admin_exempt=True)       # Rate limiting por sesión
@permiso_requerido("urgencias", "odontologia", "odontologia_equipos_basicos")
def procesar_json():
```

El orden importa: `rate_limit` es el decorator más externo (se ejecuta primero), chequea antes de verificar permisos. Consistente con los handlers actuales.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Integration | POST /procesar/ sin archivo | 400 JSON error |
| Integration | POST /procesar/ con extensión inválida | 400 JSON error |
| Integration | POST /procesar/ con permiso urgencias | 200 success |
| Integration | POST /procesar/ con permiso odontologia | 200 success |
| Integration | POST /procesar/ con permiso odontologia_equipos_basicos | 200 success |
| Integration | POST /procesar/ sin permiso | 403 JSON error |
| Integration | Semaphore timeout mock → 503 | Mock acquire_semaphore |
| Integration | Missing columns → JSON error + missing_columns array | Excel sin columnas |

Tests existentes (`test_urgencias_routes.py`, `test_excel_headers_routes.py`) se actualizan para apuntar a `/procesar/` y usar `urgencias`/`odontologia` permisos respectivamente. Usar `pytest` parametrized para cubrir los 3 permisos.

## Migration / Rollout

No migration required. Es un cambio server-side + 3 URLs de frontend. Rollback: restaurar los 3 POST handlers y revertir las URLs del frontend. Los GET handlers nunca se tocan.

## Open Questions

- [ ] `process_unified()` no recibe `profesional_dias` — las validaciones de centro de costo por profesional no se aplican en modo unificado. ¿Se necesita modificar `process_unified()` para aceptarlos? (No blocking para esta PR — comportamiento actual sin cambios.)
