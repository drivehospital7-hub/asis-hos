# Tasks: Favicon y títulos de producción

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~20 (2 new assets + 6 templates × ~3 lines each) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-always |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | favicon assets + all template changes | PR 1 | Single PR, independent, under 50 lines |

## Phase 1: Favicon assets

- [x] 1.1 Create `app/static/favicon.ico` — 32×32 ICO with monograma "HO" verde (#16a34a), matching HOS login branding
- [x] 1.2 Create `app/static/favicon.svg` — SVG version of the same monogram for modern browsers

## Phase 2: Template favicon links

- [x] 2.1 `base.html` — add `<link rel="icon">` (SVG + ICO fallback) in `<head>` before `{% block head_extra %}`
- [x] 2.2 `react_shell.html` — add favicon links in `<head>` after meta tags
- [x] 2.3 `react_standalone.html` — add favicon links in `<head>` after meta tags
- [x] 2.4 `login.html` — add favicon links in `<head>` after meta tags
- [x] 2.5 `import_facturas.html` — add favicon links in `<head>` after meta tags
- [x] 2.6 `usuarios.html` — add favicon links in `<head>` after meta tags

## Phase 3: Title corrections

- [x] 3.1 `react_shell.html` — change `— React` → `· Hospital Orito` in `<title>` default
- [x] 3.2 `react_standalone.html` — change `— React` → `· Hospital Orito` in `<title>` default
- [x] 3.3 `base.html` — change `Control Facturacion` → `Hospital Orito · Control de Facturación` in `<title>` block default
- [x] 3.4 `login.html` — change `Login — Control Facturación` → `Ingresar · Hospital Orito` in `<title>`

## Phase 4: Verify

- [x] 4.1 Hard-refresh all pages in browser — favicon shows in tab for login, SPA panel, and server-rendered pages (pending manual check)
- [x] 4.2 Check all 6 templates — no `— React` appears in any `<title>`
- [x] 4.3 Verify `git diff --stat` shows only the 2 new static files + 6 modified templates — no collateral changes
