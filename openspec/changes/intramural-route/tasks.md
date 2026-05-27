# Tasks: Ruta Intramural (Scaffold)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~630 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend Core → PR 2: Wiring → PR 3: Frontend |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

```
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High
```

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Constants + Services (backend core) | PR 1 | Base branch: feature/intramural; 290 est. lines |
| 2 | Route + Exporter + App wiring | PR 2 | Depends on PR 1; 210 est. lines |
| 3 | Frontend React + Vite entry | PR 3 | Independent of PR 1/2; 140 est. lines |

## Phase 1: Foundation — Constantes + Services

- [x] 1.1 Crear `app/constants/intramural.py` con `AREA_INTRAMURAL = "intramural"` (sin reglas de negocio)
- [x] 1.2 Modificar `app/constants/base.py`: agregar `AREA_INTRAMURAL`, `"intramural"` en `ALLOWED_PERMISOS`, entry en `DASHBOARD_AREAS`
- [x] 1.3 Crear `app/services/intramural/__init__.py` (package init vacío)
- [x] 1.4 Crear `app/services/intramural/detect_all.py` con `detect_all_problems_intramural()` llamando solo transversales: `detect_decimales`, `detect_tipo_documento_edad`, `detect_codigo_entidad_vs_entidad_afiliacion`, `detect_tipo_usuario`
- [x] 1.5 Crear `app/services/intramural/normalized_rows.py` con `build_intramural_normalized_rows()` — solo secciones transversales (decimales, tipo_doc, tipo_usuario, codigo_entidad)
- [x] 1.6 Escribir `tests/services/test_intramural_detect_all.py`: mock `data_sheet` + `indices`, verificar que solo transversales se ejecutan
- [x] 1.7 Escribir `tests/services/test_intramural_normalized_rows.py`: pasar listas de transversales, verificar formato 6 columnas + filas con `numero_factura` nulo omitidas

## Phase 2: Integration — Route + Dispatcher

- [x] 2.1 Crear `app/routes/intramural.py`: blueprint `intramural_bp` con GET (render React shell + permiso) y POST (upload Excel + detección + JSON response)
- [x] 2.2 Modificar `app/services/exporter.py`: agregar `elif area == AREA_INTRAMURAL:` → `detect_all_problems_intramural()` en `_do_detect_problems()`
- [x] 2.3 Modificar `app/__init__.py`: importar e registrar `intramural_bp` con `url_prefix="/intramural"`
- [x] 2.4 Escribir `tests/services/test_intramural_routes.py`: GET retorna React shell, POST con Excel válido retorna JSON, POST sin archivo retorna 400, POST con `.pdf` retorna 400

## Phase 3: Frontend + Build

- [x] 3.1 Crear `frontend/src/pages/intramural/index.html` (React shell entry HTML)
- [x] 3.2 Crear `frontend/src/pages/intramural/main.tsx` (React bootstrap)
- [x] 3.3 Crear `frontend/src/pages/intramural/page.tsx` (página con upload + tabla de errores)
- [x] 3.4 Modificar `frontend/vite.config.ts`: agregar entry `src/pages/intramural/index.html` en `rollupOptions.input`
