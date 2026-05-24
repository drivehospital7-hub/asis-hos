## Exploration: mejora-navegacion-dashboard

### Current State

**Dashboard entry point**: `/dashboard` (route `home.home_page`, template `home.html`). Root `/` redirects to `/dashboard`. Both are registered on `home_bp` without prefix. Template renders a grid of `.area-card` links gated by `session['permisos']`.

**Shared layout**: `base.html` is extended by all area templates EXCEPT:
- `login.html` — standalone
- `import_facturas.html` — standalone
- `usuarios.html` — standalone

The header in `base.html` contains:
- "Mini.local" title linking to `home.home_page` (but JS intercepts clicks)
- Username display
- Logout link
- A login modal (easter egg: 3 clicks on title opens modal)

**No back-to-dashboard navigation exists from area pages**. The only way to return to the dashboard is:
- The "Mini.local" link in the header, which is **broken** by the easter-egg JS intercept
- Manual URL change

**Cross-area navigation**: Only `control_errores.html` ↔ `abiertas_urgencias.html` have links between each other. No other area has links to other areas.

**"Mini.local" easter egg** (`base.html` lines 183-195): The `.layout__title--clickable` element has a JS click handler that:
1. Prevents default navigation (`e.preventDefault()`)
2. Tracks tripple-clicks within 1 second
3. On 3 clicks, opens a login modal
4. If `isAuth()` is true (localStorage), it does nothing — but still prevents navigation
5. The `href` attribute on the `<a>` tag IS `home.home_page` but it never fires

**Auth/routing flow**:
- `app/__init__.py` has a `before_request` global middleware checking `ce_authenticated` in session
- Public endpoints whitelist: `auth.*`, `static`
- Unauthenticated requests → `unauthorized.html` (401)
- `permiso_requerido()` decorator checks `session['permisos']` → denied redirects to `home.home_page`
- `login_requerido()` → denied redirects to `auth.login` with `?next=`

**All areas and their route/prefix**:

| Area | Route | Template | Extends base | Permiso key |
|------|-------|----------|-------------|-------------|
| Dashboard | `/dashboard` | `home.html` | ✅ base | — (auth only) |
| Odontología | `/odontologia` | `excel_headers.html` | ✅ base | `odontologia` |
| Urgencias | `/urgencias` | `urgencias.html` | ✅ base | `urgencias` |
| Control Urgencias | `/control-errores` | `control_errores.html` | ✅ base | `control_urgencias` |
| Ordenado y Facturado | `/ordenado-facturado` | `ordenado_facturado.html` | ✅ base | `equipos_basicos` |
| Facturas Abiertas | `/abiertas-urgencias` | `abiertas_urgencias.html` | ✅ base | `facturas_abiertas` |
| Derechos | `/derechos` | `derechos.html` | ✅ base | `derechos` |
| Usuarios | `/auth/usuarios` | `usuarios.html` | ❌ standalone | admin only |
| Login | `/auth/login` | `login.html` | ❌ standalone | public |
| Import Facturas | `/api/import` | `import_facturas.html` | ❌ standalone | — (auth only via before_request) |
| Procedimientos | `/procedimientos` | — (JSON API) | — | — |

### Affected Areas

- `app/templates/base.html` — The core layout. JS easter egg intercepts Mini.local link. No sidebar/nav, no breadcrumbs.
- `app/templates/home.html` — Dashboard with area cards. Missing Derechos and Import/Genderize links.
- `app/templates/excel_headers.html` — Odontología area. No back-to-dashboard link.
- `app/templates/urgencias.html` — Urgencias area. No back-to-dashboard link.
- `app/templates/control_errores.html` — Control Urgencias. Has link to Abiertas but not to dashboard.
- `app/templates/ordenado_facturado.html` — Ordenado y Facturado. No back-to-dashboard link.
- `app/templates/abiertas_urgencias.html` — Facturas Abiertas. Has "Volver a Control" but no dashboard link.
- `app/templates/derechos.html` — Derechos. No back-to-dashboard link.
- `app/static/css/base.css` — Layout header styles.
- `app/routes/home.py` — Dashboard route.

### Approaches

1. **Fix Mini.local as proper link + add sidebar nav** — Medium effort
   - Remove the easter egg JS intercept from the Mini.local title so it becomes a real dashboard link
   - Move the login easter egg to a separate hidden gesture (e.g. Konami code, or double-click on username)
   - Add a sidebar or nav component to `base.html` with links to all accessible areas based on permissions
   - Add breadcrumb-style navigation in the header
   - Pros: Solves all three problems in one pass. Consistent navigation everywhere.
   - Cons: Changes to layout affect all templates. Need to handle permission-gating in the nav.
   - Effort: Medium

2. **Fix Mini.local only + add back-to-dashboard on each area** — Low effort
   - Fix the easter egg issue: make Mini.local always link to dashboard when authenticated
   - Move the easter egg to a different gesture
   - Add a "← Volver al Dashboard" link to each area template individually
   - Pros: Minimal changes, low risk. Can be done incrementally.
   - Cons: Doesn't solve cross-area navigation. Each new area needs manual link addition. No sidebar consistency.
   - Effort: Low

3. **Add a proper navbar to base.html with permission-aware links** — Medium-High effort
   - Create a reusable navigation component in `base.html` with:
     - Brand link (Mini.local → dashboard, always works)
     - Nav links for accessible areas (permission-gated)
     - User info and logout (already exists)
   - Move the easter egg to a keyboard shortcut or footer easter egg
   - Consider responsive collapse for mobile
   - Pros: Clean, maintainable, single source of truth for navigation. Professional UX.
   - Cons: Templates with custom headers (control_errores, abiertas_urgencias) may need layout adjustments.
   - Effort: High

### Recommendation

**Approach 1 (Fix + sidebar nav)** — The three problems are interconnected: Mini.local is broken BECAUSE it's used as an easter egg trigger, and users can't navigate back because there's no nav component. Fixing them together produces a coherent result:

1. Remove the click-count easter egg from `.layout__title--clickable` and make the link work normally
2. Move the login easter egg to a different trigger (double-click on the app version/footer, or keyboard shortcut)
3. Add a permission-aware horizontal nav to `base.html` with links to:
   - Dashboard (always)
   - Odontología (if permiso)
   - Urgencias (if permiso)
   - Control Urgencias (if permiso)
   - Ordenado y Facturado (if permiso)
   - Abiertas Urgencias (if permiso)
   - Derechos (if permiso)
   - Usuarios (admin only)
4. Use the same session context already injected by `inject_session_user()` context processor

### Risks

- The easter egg login modal serves as a secondary login path for users who use the JS auth system. Removing it needs care — the modal login still works (it calls `/auth/api/login`). Moving it must keep its functionality intact.
- Templates with their own page-specific headers (`control_errores.html`, `abiertas_urgencias.html`) have custom layout that might visually conflict with a nav bar. Need to verify spacing.
- `import_facturas.html` and `usuarios.html` don't extend `base.html` — they would remain without nav unless they're updated too.
- Permission keys in the nav must stay in sync with `app/routes/__init__.py` and the permiso decorators — a mismatch would show or hide links incorrectly.
- The Mini.local "brand" acts as the app name. Consider renaming to "Control Facturación" for clarity, since Mini.local was originally a dev codename.

### Ready for Proposal

Yes — all three problems are well-understood and the fix paths are clear. The orchestrator should tell the user there are three approaches with different effort levels, and recommend Approach 1 as the most complete solution.
