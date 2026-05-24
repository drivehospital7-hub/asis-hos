# Proposal: React + Vite Frontend Integration

## Intent

Jinja2 templates grow unwieldy (1054-line `abiertas_urgencias.html`), mixing logic, markup, and inline JS. A modern React stack gives component composition, type safety, and maintainable UI — without rewriting the whole app at once.

## Scope

### In Scope
- `frontend/` Vite + React + TypeScript project at repo root
- shadcn/ui components + Tailwind v4 (npm) + Lucide — matching the tsx reference
- Abiertas Urgencias page as first React page, visually matching `data/import/abiertas-urgencias.tsx`
- Flask shell template (`react_shell.html`) extending `base.html` with `<div id="root">`
- New Flask route serving the React shell at `/abiertas-urgencias/react`
- `window.__INITIAL_DATA__` pattern for server-to-client data
- Vite build → `app/static/react-dist/` served by Flask
- `frontend/.gitignore` excluding `node_modules/` and build output

### Out of Scope
- TanStack Router (MPA doesn't need it — Phase 1 uses manual page routing)
- Migrating other Flask pages to React (deferred)
- Full component library (only needed components per page)
- React testing setup (deferred to Phase 2)
- Hot reload proxy in dev mode (Phase 1 serves built files)

## Capabilities

### New Capabilities
- `react-frontend`: React pages served from Flask, with Vite build pipeline and shadcn/ui component library

### Modified Capabilities
- None — no existing specs change at the behavior level

## Approach

**Hybrid Flask+React (MPA per page):**
1. `base.html` stays — sidebar, header, auth remain server-rendered
2. `react_shell.html` extends `base.html`, adds `<div id="root">` and `<script>` for the React bundle
3. Flask route serves the shell template instead of the Jinja2 template for the target page
4. React page reads `window.__INITIAL_DATA__` set server-side via Jinja2 template var
5. Vite builds to `app/static/react-dist/` — Flask already serves `/static/` for free
6. No SPA router — each React page is a standalone entry point (multi-page)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/` | New | Vite project root |
| `frontend/src/pages/abiertas-urgencias/` | New | React page entry + components |
| `frontend/src/components/ui/` | New | shadcn/ui components |
| `frontend/src/lib/` | New | `cn()` utility, API helpers |
| `app/templates/react_shell.html` | New | Flask shell template for React pages |
| `app/routes/abiertas_urgencias.py` | Modified | Add route serving React shell |
| `app/__init__.py` | Modified | Register new route (if separate blueprint) |
| `app/static/react-dist/` | New | Vite build output (gitignored) |
| `.gitignore` | Modified | Add `frontend/node_modules/`, `app/static/react-dist/` |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vite project location | `frontend/` at repo root | Clean boundary; avoids Python tool confusion |
| Dev serving | Flask serves built files | Simpler than Vite proxy; no CORS issues |
| Build output | `app/static/react-dist/` | Inside Flask's static folder → free serving via `/static/react-dist/...` |
| Data injection | `window.__INITIAL_DATA__` via Jinja2 | Server sets JSON in template; React reads on mount |
| Component structure | `src/components/ui/` (shadcn) + `src/pages/` + `src/lib/` | Matches shadcn convention; flat enough for Phase 1 |
| Routing | No SPA router in Phase 1 | Each React page is standalone; Flask handles routing |
| Auth | Keep Flask session + `/auth/api/status` | Same-origin cookies work; React calls API to check auth |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tailwind v4 CDN vs npm version mismatch | Med | Pin exact version in both `package.json` and CDN `<script>` tag |
| Vite build not compatible with Flask static serving | Low | Test build output structure before wiring route |
| `base.html` sidebar JS conflicts with React | Low | React mounts inside `<div id="root">` in the content block; no global conflict |
| Node.js not available in deployment | Med | Add `node` to CI/CD; document as new dependency |

## Rollback Plan

1. Remove the React route from `abiertas_urgencias.py` — the Jinja2 template route is untouched and still works
2. Delete `react_shell.html` and the `frontend/` directory
3. Revert `.gitignore` changes
4. The existing Jinja2 template was never modified, so zero regression

## Dependencies

- Node.js 18+ (test with `node --version` before starting)
- npm packages: react, react-dom, typescript, vite, @vitejs/plugin-react, tailwindcss v4, lucide-react, shadcn/ui init, clsx, tailwind-merge (for `cn()`)

## Success Criteria

- [ ] `npm run build` in `frontend/` produces JS/CSS in `app/static/react-dist/`
- [ ] Navigating to `/abiertas-urgencias/react` renders the React page matching the tsx reference
- [ ] `window.__INITIAL_DATA__` data is accessible in React component
- [ ] All existing Jinja2 routes continue to work unchanged
- [ ] `pytest` passes with no regressions
