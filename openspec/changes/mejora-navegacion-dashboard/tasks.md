# Tasks: Mejora de Experiencia de Navegación entre Dashboard y Áreas

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 70-100 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: CSS Foundation (`app/static/css/base.css`)

- [x] 1.1 Add `.layout__nav` — horizontal flexbox, items inline, hover highlight, no wrapping
- [x] 1.2 Add `.layout__footer--clickable` — cursor pointer for dblclick easter-egg target

## Phase 2: Core Template (`app/templates/base.html`)

- [x] 2.1 Remove easter-egg JS from `.layout__title--clickable`: delete `addEventListener` that intercepts click (~lines 184-195), keep `<a>` tag with existing `href`
- [x] 2.2 Add `<footer class="layout__footer layout__footer--clickable">` with version text + `dblclick` listener calling `openModal()`
- [x] 2.3 Add `<nav class="layout__nav">` with `{% set nav_items = {...} %}` permission-to-route mapping and loop filtering against `session_permisos`

## Phase 3: Dashboard (`app/templates/home.html`)

- [ ] 3.1 Add `{% if 'derechos' in permisos %}` card for Derechos — endpoint `derechos.derechos_page`
- [ ] 3.2 Add `{% if permisos %}` card for Import/Genderize — endpoint `import_facturas.import_facturas_page`

## Phase 4: Verification (Manual)

- [ ] 4.1 Click "Mini.local" from any child template → navigates to `/dashboard`
- [ ] 4.2 Double-click on footer version text → login modal opens
- [ ] 4.3 Nav shows only permission-filtered links per user role (admin vs. restricted)
- [ ] 4.4 `control_errores.html` and `abiertas_urgencias.html` render correctly with nav bar
- [ ] 4.5 Dashboard cards include Derechos and Import/Genderize for authorized users
