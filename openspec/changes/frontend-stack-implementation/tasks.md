# Tasks: React + Vite Frontend Integration

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

## Phase 1: Foundation — Frontend Scaffold

- [x] 1.1 `frontend/` scaffolding: `.gitignore`, `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`
- [x] 1.2 Run `npm install` in `frontend/`

## Phase 2: Core Implementation — Components & Page

- [x] 2.1 `src/styles/globals.css` — `@import "tailwindcss"` + `@theme` oklch tokens
- [x] 2.2 `src/lib/utils.ts` — `cn()` utility
- [x] 2.3 `src/components/ui/` — shadcn button + card (`npx shadcn@latest add button card`)
- [x] 2.4 `src/components/breadcrumbs.tsx` — `Breadcrumbs` with ChevronRight separator
- [x] 2.5 `src/components/page-title.tsx` — `PageTitle` (eyebrow + h1 + description + actions)
- [x] 2.6 `src/pages/abiertas-urgencias/` — `main.tsx` entry + `page.tsx` component (3 cards, collapsible, empty schedule)

## Phase 3: Flask Integration — Shell Template & Route

- [x] 3.1 `src/main.tsx` — Shared entry reading `window.__INITIAL_DATA__`, renders page by registry
- [x] 3.2 `app/templates/react_shell.html` — Extends `base.html`, `<div id="root">`, `__INITIAL_DATA__`, `<noscript>`
- [x] 3.3 `app/routes/abiertas_urgencias.py` — `GET /react` with `_get_manifest_asset()` + `initial_data`
- [x] 3.4 Run `npm run build`, verify `manifest.json` + `react-dist/assets/`

## Phase 4: Integration Testing

- [x] 4.1 `/abiertas-urgencias/react` returns 200 with `__INITIAL_DATA__`
- [x] 4.2 `/abiertas-urgencias/` (Jinja2) still serves original template
- [x] 4.3 `pytest` passes — no regressions

## Phase 5: New Shared Components

- [x] 5.1 `src/components/status-badge.tsx` — `StatusBadge` with `tone` (danger/warning/success/info/neutral) + optional `dot`
- [x] 5.2 Run `npx shadcn@latest add input` for shadcn Input
- [x] 5.3 Fix imports: `PageTitle` from `@/components/page-title`, not `@/components/status-badge` (already correct in existing page.tsx)

## Phase 6: 3 New Pages — Entry + Component

- [x] 6.1 `src/pages/index/` — `index.html` + `main.tsx` + `page.tsx` (3 KPICards, 3 AreaCards via `<a href>`, StatusBadge, footer) — matches `data/import/index.tsx`
- [x] 6.2 `src/pages/control-novedades/` — `index.html` + `main.tsx` + `page.tsx` (month tabs, 3 KPI cards, filter bar w/ native `<select>` + Input, error table Eye/Pencil/Trash2, StatusBadge per row) — matches `data/import/control-novedades.tsx`
- [x] 6.3 `src/pages/urgencias/` — `index.html` + `main.tsx` + `page.tsx` (upload card: dashed drop-zone, Info alert, Procesar; error card: AlertTriangle, total, StatusBadge, table Controlar) — matches `data/import/urgencias.tsx`

## Phase 7: Vite Config + Flask Routes

- [x] 7.1 `frontend/vite.config.ts` — Add `src/pages/index/index.html`, `control-novedades/index.html`, `urgencias/index.html` to `rollupOptions.input`
- [x] 7.2 `app/templates/react_shell.html` — Dynamic `<title>` via `{{ page_title | default("Control de Facturación") }}`
- [x] 7.3 `app/routes/home.py` — `GET /dashboard/react` with `_get_manifest_asset("src/pages/index/index.html")`, `initial_data` w/ `kpis` + `areas`
- [x] 7.4 `app/routes/control_errores.py` — `GET /control-errores/react` with `_get_manifest_asset("src/pages/control-novedades/index.html")`, `initial_data` w/ `meses` + `novedades`
- [x] 7.5 `app/routes/urgencias.py` — `GET /urgencias/react` with `_get_manifest_asset("src/pages/urgencias/index.html")`, `initial_data` w/ empty `errores[]`
- [x] 7.6 Run `npm run build` + verify 4 HTML entries in `manifest.json`

## Phase 8: Tests

- [x] 8.1 `/dashboard/react` returns 200 with `__INITIAL_DATA__` containing `kpis` + `areas` (test_dashboard_react_has_kpis_and_areas ✅)
- [x] 8.2 `/control-errores/react` returns 200 with `__INITIAL_DATA__` containing `meses` + `novedades` (test_control_errores_react_has_meses_and_novedades ✅)
- [x] 8.3 `/urgencias/react` returns 200 with `__INITIAL_DATA__` containing `errores` (test_urgencias_react_has_errores ✅)
- [x] 8.4 Existing Jinja2 routes (`/dashboard`, `/control-errores`, `/urgencias/`) still serve original templates (3 tests ✅)
- [x] 8.5 `pytest` passes — 364/364 passing, no regressions
- [x] 8.6 `npm run build` passes — production build succeeds (4 HTML entries + 6 shared chunks)
