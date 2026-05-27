# Design: Ruta Intramural (Scaffold)

## Technical Approach

Copiar la estructura completa de `urgencias` (`routes`, `services`, frontend, constants) y simplificarla eliminando todo lo específico de urgencias. El orquestador intramural solo invoca detectores transversales existentes (decimales, tipo_documento_edad, codigo_entidad, tipo_usuario). Sin reglas de negocio propias.

El cambio es puro scaffold — archivos nuevos y modificaciones mínimas a archivos existentes. Todo en rama feature sin tocar `main`.

## Architecture Decisions

### Decision: Copiar vs abstraer base compartida

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Crear `base_route.py` compartido | Reduce duplicación, pero cada área tiene frontend y constantes distintas → abstracción prematura | ❌ |
| Copiar urgencias y simplificar | Duplicación controlada, cero riesgo de romper urgencias, cada área evoluciona independientemente | ✅ |

**Rationale**: El patrón se repite intencionalmente. Una abstracción hoy sería prematura — si aparece una tercera área con el mismo patrón, se puede extraer. Por ahora, copiar es más seguro y rápido.

### Decision: Nombre del permiso

**Choice**: `"intramural"` (singular, sin prefijo, consistente con `"odontologia"`, `"urgencias"`, `"derechos"`).
**Alternatives**: `"intramurales"`, `"intramural:read"` — rompen la convención existente.
**Rationale**: `ALLOWED_PERMISOS` usa nombres singulares para permisos base. El sufijo `:write` no aplica porque intramural solo tiene detección.

### Decision: Manejo de columnas faltantes

**Choice**: Mismo patrón que urgencias — `get_column_indices()` retorna `missing_columns`, se verifica ANTES de procesar, y se retorna error 200 con lista de columnas faltantes.
**Rationale**: Los detectores transversales ya manejan columnas faltantes retornando `[]`, pero el early-exit da mejor UX.

## Data Flow

```
Browser                          Flask                         Services
  │                                │                              │
  ├─ GET /intramural/ ─────────────┤                              │
  │                                ├─ render_template(            │
  │                                │   react_shell.html,          │
  │                                │   entry_js, entry_css,       │
  │                                │   initial_data)              │
  │  ◄───── React shell ───────────┤                              │
  │                                │                              │
  ├─ POST /intramural/ ────────────┤                              │
  │   (file_upload)                │                              │
  │                                ├─ detect_problems_only(       │
  │                                │   file, area=AREA_INTRAMURAL)│
  │                                │                              ├─ Polars: read_excel
  │                                │                              ├─ _SimpleSheet
  │                                │                              ├─ get_column_indices
  │                                │                              ├─ detect_all_problems_intramural
  │                                │                              │   ├─ detect_decimales
  │                                │                              │   ├─ detect_tipo_documento_edad
  │                                │                              │   ├─ detect_codigo_entidad...
  │                                │                              │   ├─ detect_tipo_usuario
  │                                │                              │   └─ build_intramural_normalized_rows
  │                                │                              └─ JSON response
  │  ◄── JSON {errores, totales} ──┤                              │
```

## File Changes

### New Files

| File | Description |
|------|-------------|
| `app/constants/intramural.py` | `AREA_INTRAMURAL` y constantes del dominio (inicialmente vacío de reglas) |
| `app/routes/intramural.py` | Blueprint `/intramural/` con GET (React shell) y POST (upload + detección) |
| `app/services/intramural/__init__.py` | Package init |
| `app/services/intramural/detect_all.py` | Orquestador — solo llama detectores transversales |
| `app/services/intramural/normalized_rows.py` | Normalizador simplificado (solo transversales) |
| `frontend/src/pages/intramural/index.html` | React shell entry HTML |
| `frontend/src/pages/intramural/main.tsx` | React bootstrap |
| `frontend/src/pages/intramural/page.tsx` | Página React con upload + tabla de errores |

### Modified Files

| File | Change |
|------|--------|
| `app/constants/base.py` | +`AREA_INTRAMURAL`, +`"intramural"` en `ALLOWED_PERMISOS`, +entry en `DASHBOARD_AREAS` |
| `app/services/exporter.py` | +`elif area == AREA_INTRAMURAL:` → `detect_all_problems_intramural` |
| `app/__init__.py` | Import + register `intramural_bp` con `url_prefix="/intramural"` |
| `frontend/vite.config.ts` | +entry `src/pages/intramural/index.html` en `rollupOptions.input` |

## Interfaces / Contracts

### Orquestador

```python
def detect_all_problems_intramural(
    data_sheet: Worksheet,
    indices: dict[str, int | None],
) -> tuple[dict[str, Any], dict[str, str]]:
```

Retorna mismo formato que `detect_all_problems_urgencias`: `(resultado_dict, responsables_map)`. El `resultado_dict["problemas"]` solo contiene claves de transversales: `normalizados`, `decimales`, `tipo_identificacion_edad`, `codigo_entidad_vs_afiliacion`, `tipo_usuario`.

### Normalizador

```python
def build_intramural_normalized_rows(
    responsables_map: dict[str, str],
    decimales: list | None = None,
    tipo_identificacion_edad: list[dict] | None = None,
    tipo_usuario: list[dict] | None = None,
    entidad_afiliacion_comparison: list[dict] | None = None,
    fec_factura_map: dict[str, str] | None = None,
) -> list[dict[str, str]]:
```

Retorna mismo formato de 6 columnas que urgencias: `tipo_error`, `factura`, `responsable_cierra`, `descripcion`, `procedimiento`, `detalle`.

## Testing Strategy

| Layer | Approach |
|-------|----------|
| Unit — detect_all | Mock `data_sheet` + `indices` con datos de intramural; verificar que solo transversales se ejecutan |
| Unit — normalized_rows | Pasar listas de transversales y verificar formato de salida 6 columnas |
| Integration — route POST | Subir Excel real de intramural a `/intramural/`; verificar JSON con `status: "success"` y errores de transversales |
| Integration — route GET | Verificar que renderiza React shell sin errores |
| E2E — permissions | Verificar que `@permiso_requerido("intramural")` da 403 sin el permiso y 200 con él |

## Migration / Rollout

No migration required. El cambio es puramente aditivo:
1. Crear constantes y servicios nuevos
2. Agregar permiso + dashboard (para que el 403 nunca ocurra)
3. Registrar blueprint
4. Agregar entry Vite
5. Build frontend + deploy

Rollback: revertir commits en orden inverso. Al ser rama feature, `main` nunca se ve afectado.

## Open Questions

- Ninguna. El scaffold es directo — copiar urgencias, simplificar, conectar.
