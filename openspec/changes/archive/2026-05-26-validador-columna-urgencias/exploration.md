## Exploration: Validador column in Control de Novedades

### Current State

**What is "Control de Novedades"?**
It's a sub-module of Urgencias for tracking invoice issues ("novedades"). It's served at `/control-errores` through a legacy **Jinja2 template** (`app/templates/control_errores.html`, 2248 lines of inline HTML+JS). A **React page** exists at `frontend/src/pages/control-novedades/page.tsx` and is in the Vite manifest, but the backend route has NOT been switched to the React shell yet — the Jinja2 template is what users see today.

**Data storage:**
- JSON file at `app/data/control_errores.json`
- Fields per novedad: `id`, `tipo_error`, `factura`, `observacion`, `observacion_facturador`, `estado`, `responsable`, `creado_en`, `actualizado_en`
- REST API at `/api/control-errores` (GET, POST, PUT, DELETE)

**How "Creado" (fecha) auto-fill works today:**
- In `crear_error()` (`errores_storage.py:131`): `"creado_en": datetime.now().isoformat()`
- The timestamp is set **server-side**, invisible to the client until the novedad is returned in the API response
- In the Jinja2 template, the column is rendered as read-only (`<td class="fecha-creado">`) — no inline editor
- The React page renders it the same way: `<td>{n.creado}</td>` with no edit controls

**User session data available:**
- `auth_session.do_login()` stores: `primer_nombre`, `segundo_nombre`, `apellido_1`, `apellido_2` (from `users_store.py`)
- The Jinja2 template has `window._canWrite` checked from `session.get("permisos")`
- `control_errores_service.py` already imports `from flask import session`

**Current table columns (Jinja2):** Factura, Creado, Categoría, Descripción, Facturador Cierra, Pendiente, Acciones
**Current table columns (React):** Factura, Creado, Categoría, Descripción, Facturador cierre, Estado, Acciones

### Affected Areas

- `app/utils/errores_storage.py` — `crear_error()` needs a `validador` parameter; the JSON model needs a `validador` field
- `app/services/control_errores_service.py` — `add_error()` needs to read `primer_nombre` + `apellido_1` from Flask session and pass them to `crear_error()`
- `app/templates/control_errores.html` — Jinja2 table `<thead>` needs a new `<th>`, each row `<tr>` needs a new `<td>` for validador (read-only, auto-populated), `colspan` updates for "Cargando..." and empty state, `addNewRow()` template needs validador cell
- `frontend/src/pages/control-novedades/page.tsx` — `Novedad` interface needs `validador: string`; table needs Validador `<th>` as first column; `__INITIAL_DATA__` and hardcoded mock data need updating
- `app/routes/control_errores.py` — MAY need a React shell route (if switching from Jinja2); alternatively, keep as-is

### Approaches

1. **Backend-only (JSON + service) + Jinja2 template** — Add `validador` storage to the JSON model, populate it from session in the service, and add the read-only column to the Jinja2 template. Do NOT update the React page (it's not live).
   - Pros: Smallest change, works immediately for all current users
   - Cons: React page (when eventually connected) will need this change again; leaves a gap between the live template and the React page
   - Effort: Low

2. **Full backend + both frontends** — Same as approach 1, PLUS update the React `page.tsx` to include the column. The React page entry point already exists in the manifest, so when it's wired up later, Validador will be ready.
   - Pros: Complete coverage — no technical debt left on the React side
   - Cons: Extra work on a page that's not yet served (might bitrot if the wiring changes)
   - Effort: Medium

3. **Switch to React shell + add Validador** — Change the `/control-errores` route to serve the React shell (like `/urgencias` and `/dashboard` already do), then add Validador to the React page. This would also require building a proper add/edit modal since the React page currently has no modal form.
   - Pros: Future-proof; aligns with the rest of the app's architecture
   - Cons: Scope creep — adds route switching, modal implementation, and data-fetching logic beyond just the Validador column
   - Effort: High

### Recommendation

**Approach 1** — the simplest, most focused change.

Reasoning:
- The user's request is specific: add the Validador column to the existing table. Don't rewrite the page.
- The Jinja2 template is what users interact with right now — that's where the change should be visible.
- The backend change (adding a `validador` field to `crear_error()`) is trivial and safe — it doesn't break backward compatibility for existing entries (they'll just have an empty/null validador).
- The React page is built but not wired; updating it now is premature until the route switch is prioritized separately.

**What needs to happen on the backend:**
1. `errores_storage.py` — `crear_error()`: add `validador: str = ""` parameter, store it in the JSON dict
2. `control_errores_service.py` — `add_error()`: read `session.get("primer_nombre", "")` and `session.get("apellido_1", "")`, compose `validador = f"{primer_nombre} {apellido_1}".strip()`, pass to `crear_error()`
3. `control_errores.html` (Jinja2):
   - Add `<th>Validador</th>` as the first `<th>` in `<thead>`
   - Add a read-only `<td>` for validador in each row (no `editable-cell` class, no click handler)
   - Update the `addNewRow()` template to include a `-` for validador (auto-populated server-side)
   - Update `colspan` values from 7 to 8 throughout

**What does NOT need to change:**
- No DB migration (it's JSON storage — new field is additive)
- No new API fields (validador is set server-side, not client-provided)
- No permission changes (validador is read-only, auto-populated)

### Risks

- **Risk: Backward compatibility** — Existing novedades won't have `validador`. The frontend should handle this gracefully (show `-` or empty). Low risk since JSON access via `e.validador || '-'`.
- **Risk: React page gap** — When the switch to React shell eventually happens, Validador won't be in the React page unless separately updated. Mitigation: the exploration recommends the React update be done at that time, not now.
- **Risk: `creado_en` pattern re-implementation** — The user says "al igual que fecha que se autocompleta y no es editable". The validador must NOT be user-editable in any form. The current `addNewRow()` template in the Jinja2 creates inline editable cells — the validador for the new row should show a placeholder or the current user's name in read-only mode.

### Ready for Proposal

**Yes** — the scope is well-understood, the approach is clear, and there are no blockers. 

The orchestrator should tell the user:
- The Validador column will be added as the FIRST column of the table, exactly like the "Creado" field: auto-populated server-side and read-only on the UI
- It will contain the current user's `primer_nombre` + `apellido_1` (from their login session)
- It's a backend + frontend (Jinja2) change only — no new DB, no new API client fields
- The React page (already built but not yet connected) will need the same change when routed to the React shell, but that's a separate task
