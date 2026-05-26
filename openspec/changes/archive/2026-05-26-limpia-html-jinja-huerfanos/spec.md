# Delta Spec — Limpieza de Templates Jinja Huérfanos

## Purpose

Remover 7 templates Jinja que ninguna ruta renderiza, convertir 2 fallbacks Jinja a JSON error responses, y actualizar tests + config para reflejar el estado actual donde React es el único frontend.

---

## ADDED Requirements

### R1: Eliminar templates huérfanos

Los siguientes 7 archivos SHALL ser eliminados de `app/templates/`:

`home.html`, `login.html`, `usuarios.html`, `import_facturas.html`, `derechos.html`, `abiertas_urgencias.html`, `ordenado_facturado.html`

| Scenario | Dado | Cuando | Entonces |
|----------|------|--------|----------|
| Archivos no existen | repo actualizado | listar `app/templates/` | 7 archivos no aparecen |
| Ninguna ruta falla | archivos eliminados | `pytest -v` | todos los tests pasan |
| Sidebar funcional | archivos eliminados | navegar sidebar | control_errores y demás páginas funcionan |

### R2: Fallbacks Jinja → JSON error response

Los fallbacks POST en `app/routes/urgencias.py` (líneas 78, 90) y `app/routes/excel_headers.py` (líneas 97, 109) SHALL retornar `jsonify(error), 400` en lugar de `render_template("urgencias.html")` / `render_template("excel_headers.html")`.

| Scenario | Dado | Cuando | Entonces |
|----------|------|--------|----------|
| POST sin archivo | request POST sin `file_upload` | llegar a fallback | response JSON con `status: "error"`, status 400 |
| POST con error de archivo | request POST con archivo inválido | llegar a fallback | response JSON con `status: "error"`, status 400 |
| POST exitoso | request POST válido | procesar | response JSON existente (sin cambios) |

### R3: Remover `auth.login_legacy` de PUBLIC_ENDPOINTS

El endpoint `"auth.login_legacy"` SHALL ser eliminado de `PUBLIC_ENDPOINTS` en `app/__init__.py`.

| Scenario | Dado | Cuando | Entonces |
|----------|------|--------|----------|
| Endpoint eliminado | `app/__init__.py` actualizado | inspeccionar `PUBLIC_ENDPOINTS` | `auth.login_legacy` no está en el frozenset |
| Sin efecto colateral | endpoint eliminado | `pytest -v` | tests existentes pasan |

---

## MODIFIED Requirements

### R4: Lista de TEMPLATES en test_favicon_titles.py

`TEMPLATES` SHALL excluir `login.html`, `import_facturas.html`, `usuarios.html`.
`TITLE_TEMPLATES` SHALL excluir `login.html`.
*(Previously: lista incluía los 3 huérfanos)*

| Scenario | Dado | Cuando | Entonces |
|----------|------|--------|----------|
| TEMPLATES actualizada | archivo modificado | test `test_all_templates_have_favicon_link` | solo templates existentes son verificados |
| TITLE_TEMPLATES actualizada | archivo modificado | test `test_login_html_title` | eliminado (no corre sobre archivo inexistente) |

### R5: Tests de templates en test_visual_redesign.py

Tests que referencian templates eliminados SHALL ser removidos o actualizados para no fallar por archivos faltantes.

| Scenario | Dado | Cuando | Entonces |
|----------|------|--------|----------|
| home tests removidos | `TestHomeTemplate` | ejecutar clase | clase eliminada o tests refactorizados |
| abiertas extends base | `TestAbiertasUrgenciasTemplate` | ejecutar test | test eliminado (template eliminado) |
| RemainingTemplates actualizada | `TestRemainingTemplates` | `test_template_extends_base` | parámetros `ordenado_facturado.html`, `derechos.html` removidos |
| Standalone templates check | `test_standalone_templates_have_tailwind` | ejecutar test | `login.html`, `usuarios.html`, `import_facturas.html` removidos del loop |
| urgencias test | `TestUrgenciasTemplate` | ejecutar clase | opcional: mantener test si urgencias.html sobrevive como fallback |

---

## REMOVED Requirements

### R6: Template `login.html` — test de título específico

La función `test_login_html_title()` en `test_favicon_titles.py` SHALL ser eliminada.
*(Reason: `login.html` es eliminado; el login ahora usa `react_standalone.html`)*

### R7: Dependencia en urgencias.html / excel_headers.html como templates renderizadas

Los templates `urgencias.html` y `excel_headers.html` ya no SHALL ser renderizados por ninguna ruta. Si se eliminan, las rutas POST fallarán con JSON en lugar de HTML.
*(Reason: React es el único frontend; fallbacks POST retornan JSON a `fetch()`, nunca esperan HTML)*

---

## Non-Functional Requirements

- **Sin regresión**: Las páginas preservadas (`base.html`, `control_errores.html`, `unauthorized.html`, `react_shell.html`, `react_standalone.html`) SHALL renderizar sin cambios.
- **Tests verdes**: `pytest -v` SHALL pasar con 0 fallos después del cambio.
- **Sin cambios de ruta**: Los GET endpoints (`/dashboard`, `/odontologia`, `/urgencias`, etc.) SHALL seguir sirviendo `react_shell.html` — sin cambios.
