# Design: Limpia los HTML Jinja huérfanos

## Technical Approach

Eliminación pura de 7 templates Jinja que ninguna ruta renderiza + conversión de 2 semi-activos a responses JSON + limpieza transitiva de 3 CSS legacy. El frontend React ya es el único cliente — los fallbacks Jinja nunca llegan al navegador.

## Architecture Decisions

### Decision: Replace render_template fallback with jsonify

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| Mantener Jinja fallback | Código muerto, confunde cambios futuros | ❌ |
| Redirigir a GET | Pérdida del contexto de error | ❌ |
| **jsonify + 400** | Coincide con el resto de POST; React fetch() ya parsea JSON en error | ✅ |

Los fallbacks POST en `urgencias.py` (L78, L90) y `excel_headers.py` (L97, L109) construyen el mismo `ctx` que el éxito pero devuelven HTML que el frontend React nunca espera. Convertir a `jsonify({"status":"error", ...}), 400` unifica el contrato.

### Decision: Orphaned CSS cleanup

| Archivo | Origen | Acción |
|---------|--------|--------|
| `legacy/abiertas_urgencias.css` | Solo referenciado desde `abiertas_urgencias.html` (borrado) | Delete |
| `legacy/derechos.css` | Solo referenciado desde `derechos.html` (borrado) | Delete |
| `legacy/urgencias.css` | Solo referenciado desde `urgencias.html` (fallback → JSON) | Delete |
| `legacy/control_errores.css` | Referenciado desde `control_errores.html` (KEEP) | Sin cambios |

## Data Flow

```
POST /urgencias (file missing / save error)
  ┌─ Antes:  build ctx → render_template("urgencias.html") → HTML (nadie lo parsea)
  └─ Ahora:  jsonify(error) → 400 → React fetch().catch() lo maneja

POST /odontologia (file missing / save error) — idéntico patrón
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/templates/home.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/login.html` | Delete | Orphan — route usa `react_standalone.html` |
| `app/templates/usuarios.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/import_facturas.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/derechos.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/abiertas_urgencias.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/ordenado_facturado.html` | Delete | Orphan — route usa `react_shell.html` |
| `app/templates/urgencias.html` | Delete | Semi-active — fallbacks migrados a JSON |
| `app/templates/excel_headers.html` | Delete | Semi-active — fallbacks migrados a JSON |
| `app/static/css/legacy/abiertas_urgencias.css` | Delete | Transitivo — solo referenciado desde template borrado |
| `app/static/css/legacy/derechos.css` | Delete | Transitivo — solo referenciado desde template borrado |
| `app/static/css/legacy/urgencias.css` | Delete | Transitivo — solo referenciado desde template borrado |
| `app/routes/urgencias.py` | Modify | L78, L90: `render_template` → `jsonify`, 400 |
| `app/routes/excel_headers.py` | Modify | L97, L109: `render_template` → `jsonify`, 400 |
| `app/__init__.py` | Modify | L15: remove `"auth.login_legacy"` from PUBLIC_ENDPOINTS |
| `tests/services/test_favicon_titles.py` | Modify | Remove `login.html`, `import_facturas.html`, `usuarios.html` from TEMPLATES; remove `TITLE_TEMPLATES` entries; remove `test_login_html_title` |
| `tests/services/test_visual_redesign.py` | Modify | Remove `TestHomeTemplate` class (home.html tests); remove `TestAbiertasUrgenciasTemplate`; remove `ordenado_facturado.html` and `derechos.html` from parametrize; remove `test_standalone_templates_have_tailwind`; remove `test_legacy_abiertas_urgencias_css_exists` |

## Code Changes (non-obvious)

Los 4 fallbacks siguen el mismo patrón:

```python
# Antes (urgencias.py L78, L90 / excel_headers.py L97, L109):
ctx["upload_error"] = "..."
return render_template("urgencias.html" or "excel_headers.html", **ctx)
# Después:
return jsonify({"status": "error", "data": {}, "errors": ["..."]}), 400
```

Ninguno de estos bloques es alcanzable desde el frontend React — las rutas POST son llamadas vía `fetch()` que espera JSON. Los fallbacks HTML son código muerto desde la migración al shell React.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | `test_favicon_titles.py` | Remove orphan entries from TEMPLATES/TITLE_TEMPLATES; delete `test_login_html_title` |
| Unit | `test_visual_redesign.py` | Remove `TestHomeTemplate` (4 tests), `TestAbiertasUrgenciasTemplate` (2 tests), `TestUrgenciasTemplate` (2 tests); shrink `test_template_extends_base` to `["unauthorized.html"]`; remove `test_standalone_templates_have_tailwind`, `test_legacy_abiertas_urgencias_css_exists` |
| Manual | POST sin archivo | `/urgencias/` y `/odontologia/` retornan `{"status":"error",...}` 400, no HTML |
| CI | `pytest -v` | Pasa sin errores |

## Migration / Rollout

No migration required. Commits progresivos:

1. **Código**: urgencias.py + excel_headers.py + __init__.py
2. **Archivos**: eliminar 12 archivos (templates + CSS)
3. **Tests**: actualizar assertions

Rollback: `git revert` por capa. Templates eliminados se recuperan del historial git.

## Edge Cases & Risks

| Risk | Mitigation |
|------|------------|
| Template referenciado por otro BP | Bajo — grep confirmó solo las rutas listadas |
| `render_template` import sobre | Se conserva — GET routes aún lo usan |
| `build_excel_headers_form_context` en fallbacks | **Riesgo medio** — esas llamadas se vuelven inútiles; evaluar si eliminarlas (están en urgencias.py L70-76, L82-88 y excel_headers.py L89-94, L101-106) |

## Open Questions

- [ ] `build_excel_headers_form_context` en los fallbacks: ¿eliminar las 4 llamadas muertas? Propongo no hacerlo en este cambio para mantener el diff mínimo, pero dejar `TODO` comment.
