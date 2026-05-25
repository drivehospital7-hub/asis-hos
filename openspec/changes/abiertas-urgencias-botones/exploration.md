# Exploration: Abiertas Urgencias — Port legacy JS logic to React

## Current State

The React component at `frontend/src/pages/abiertas-urgencias/page.tsx` is a **static UI shell**:

| UI Element | State |
|---|---|
| Breadcrumbs + PageTitle | ✅ Working |
| "Asignar responsable" accordion | ⚠️ Toggle works, textarea has NO `value`/`onChange`, "Asignar" button has NO `onClick` |
| "Ver horario" accordion | ⚠️ Toggle works, table is hardcoded empty state (no data fetching) |
| "Falta cargar" warning card | ⚠️ Static warning, "Editar" and "Cargar" buttons have NO `onClick` |
| Status bar | ❌ Missing entirely (legacy has status bar) |
| Results table | ❌ Missing entirely (legacy shows `#respResultSection`) |
| Toast/feedback | ❌ Missing entirely |
| Copiar to clipboard | ❌ Missing for both schedule and results |

The legacy Jinja2 template (`app/templates/abiertas_urgencias.html`) has ALL the working JavaScript logic across ~870 lines of inline `<script>`.

## Affected Areas

| File | Role |
|---|---|
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Primary — rewrite to add all state/handlers/components |
| `frontend/src/pages/abiertas-urgencias/main.tsx` | Unchanged (entry point, still valid) |
| `app/templates/abiertas_urgencias.html` | Source of truth for JS logic (will be deprecated) |
| `app/routes/abiertas_urgencias.py` | API endpoints already exist — no changes needed |
| `app/services/abiertas_urgencias_service.py` | Service layer — no changes needed |
| `app/static/css/legacy/abiertas_urgencias.css` | Styles to replace with Tailwind (reference only) |

## What Needs to Be Ported — Logical Work Units

### Unit 1: Schedule View (load + display)
**Legacy functions**: `loadSchedule()`, `renderTable()`, `setStatusLoaded()`, `setStatusEmpty()`, `copiarHorario()`
**API calls**: `GET /abiertas-urgencias/api/schedule`
**In React**:
- `useEffect` on mount to fetch schedule
- State: `scheduleDays`, `scheduleLoading`, `scheduleStatus`
- Replace hardcoded empty table with dynamic render
- `handleCopySchedule` clipboard function

### Unit 2: Parse & Save Schedule
**Legacy functions**: `parseScheduleText()`, `parseAndSave()`, `toggleParseCard()`, `collapseParseCard()`
**API calls**: `POST /abiertas-urgencias/api/schedule`
**In React**:
- State: `scheduleInput` (textarea), `parseLoading`
- `handleInputChange` binding
- Port `parseScheduleText()` as pure TS utility
- `handleParseAndSave()` async handler
- Loading state on "Parsear y Guardar" button

### Unit 3: Delete Schedule
**Legacy functions**: `deleteSchedule()`
**API calls**: `DELETE /abiertas-urgencias/api/schedule`
**In React**:
- `handleDeleteSchedule()` with confirm dialog
- Clear state + reset UI on success

### Unit 4: Asignar Responsable — Parse & Process
**Legacy functions**: `procesarFacturas()`, `autoDetectColumns()`, `calcularResponsable()`
**API calls**: None (all pure client-side)
**In React**:
- State: `facturasInput` (textarea), `processing`, `results`
- Port `autoDetectColumns()` as pure TS utility
- Port `calcularResponsable()` as pure TS utility
  - Also port `NOMBRE_MAP` constant
- `handleProcesarFacturas()` orchestrator handler
- Row-level detection of "abierta + egreso > 4 días" → `rowClass`

### Unit 5: Results Table
**Legacy functions**: `renderRespTable()`, `showDetectedCols()`, `copiarResultados()`
**API calls**: `GET /api/control-errores` (to preload existing invoices)
**In React**:
- After processing: display results table with 9 columns
- Conditional row styling ("vencida" for >4 días)
- Show detected columns with badges
- `handleCopyResults` clipboard function
- Track sent state per invoice

### Unit 6: Send to Control (per-row action)
**Legacy functions**: `sendToControl()`, event delegation on `#respBody`
**API calls**: `POST /api/control-errores`
**In React**:
- `handleSendToControl(factura, responsable, area, egreso)` 
- Duplicate detection: preload existing invoices on mount
- Confirmation dialog before sending
- Button state: add / exists / sent (disabled)
- Track `_enviada` per result row
- Track `_envioExistentes` global set → React state

### Unit 7: Toast / Feedback Component
**Legacy**: `showToast()`, fixed-position `.toast` element
**In React**:
- Create a toast state (`{message, type}`) + auto-dismiss `useEffect`
- Or integrate with a lightweight Sonner/toast if project already has one
- Replace all `showToast()` calls with setter

### Unit 8: Auth / can_write gating
**Legacy**: `window._isAuth`, `{% if not can_write %}disabled{% endif %}`
**In React**:
- Already have `can_write` prop — use it for disabling Cargar/Editar/Eliminar buttons
- Gate schedule modification and delete behind `can_write`

---

## Summary Table: State Variables Needed

| State | Type | Default | Trigger |
|---|---|---|---|
| `scheduleDays` | `Array<{dia, manana, tarde, noche}>` | `[]` | `useEffect` on mount |
| `scheduleLoading` | `boolean` | `true` | fetch start/end |
| `scheduleStatus` | `'loading' \| 'loaded' \| 'empty'` | `'loading'` | after fetch |
| `scheduleInput` | `string` | `''` | textarea onChange |
| `parseLoading` | `boolean` | `false` | parse btn click |
| `facturasInput` | `string` | `''` | textarea onChange |
| `processing` | `boolean` | `false` | procesar btn click |
| `results` | `Array<ResultRow>` | `[]` | after procesar |
| `envioExistentes` | `Set<string>` | `new Set()` | `useEffect` preload |
| `envioEnviadas` | `Set<string>` | `new Set()` | after each POST |
| `toast` | `{message: string, visible: boolean}` | ... | any action |

## Recommended Component Architecture

```
AbiertasUrgenciasPage
├── Breadcrumbs + PageTitle (existing)
├── StatusBar (NEW — replaces warning card)
│   ├── Icon + status text
│   └── Actions: Modificar | Cargar | Eliminar (gated by can_write)
├── AsignarResponsableCard (REWRITE)
│   ├── Accordion header
│   ├── Textarea (value=facturasInput, onChange=...)
│   ├── "Procesar y Asignar" button (onClick=handleProcesar)
│   └── Detected columns badges (conditional)
├── ResultsTable (NEW — shown when results.length > 0)
│   ├── Results header with count + "Copiar a Excel"
│   └── Results rows with conditional styling + Envío buttons
├── VerHorarioCard (REWRITE)
│   ├── Accordion header with hint
│   ├── Schedule table (dynamic from scheduleDays)
│   └── "Copiar Horario" button
├── ParseScheduleCard (NEW — hidden by default)
│   ├── Textarea (value=scheduleInput)
│   └── "Parsear y Guardar" + "Cancelar" buttons
└── Toast (NEW — fixed position, auto-dismiss)
```

**Key architectural decisions**:

1. **Keep pure logic as utility functions** — `parseScheduleText()`, `autoDetectColumns()`, `calcularResponsable()` are pure TS functions with zero React dependency. Put them in `frontend/src/pages/abiertas-urgencias/utils.ts`.

2. **Constants in a separate file** — `NOMBRE_MAP` and column label classes go in `frontend/src/pages/abiertas-urgencias/constants.ts`.

3. **All state in one component** — keep everything in `page.tsx` for now. The page is a single-purpose orchestration view. Extract sub-components only if the file exceeds ~400 lines.

4. **API calls inline via `fetch`** — consistent with `OdontologiaPage` pattern (no axios, no react-query). Use `try/catch` and `setToast()` for error feedback.

5. **Replace the "Falta cargar" warning card with a `<StatusBar>` component** — the legacy template's status bar is richer (icon changes, shows loaded days count, actions + delete). The current React shell has a simplified warning card that misses this functionality. Merge the warning card INTO the status bar.

## Risks & Gotchas

1. **`parseScheduleText()` handles multi-line quoted CSV fields** — complex logic with quote counting. Port carefully with tests or at least known input vs. output.

2. **`autoDetectColumns()` has ~85 lines of pattern matching** — the most complex pure JS function. It uses regex patterns for dates, factura prefixes (CAP/FEV), statuses, areas, etc. Test with real pasted data.

3. **`calcularResponsable()` implements business rules** — 30-minute reception shift ("el turno entrante se hace cargo 30 minutos antes"), midnight crossover for night shift. These are DOMAIN RULES, not arbitrary code. Must match exactly.

4. **Row-level "vencida" detection** — uses `hoyInicio - egresoInicio` comparison, NOT a 24h calculation. Simplifies to calendar-day difference. Important to replicate exactly because it affects visual highlighting of overdue invoices.

5. **Envío button has 3 states: add / exists / sent** — each with different visual treatment. The "exists" button uses `confirm()` to ask for duplicate permission. Must preserve this UX.

6. **`window._envioExistentes` is preloaded on every processing** — `renderRespTable()` calls `GET /api/control-errores` to know which invoices already exist. In React, this should be a one-time preload on mount or on process, not re-fetch on every render.

7. **Row `_enviada` flag is mutable** — tracked both in `window.lastResults` and `window._envioEnviadas` set. In React, this should be in `results` state with an `_enviada` property per row.

8. **The legacy template has NO error boundary or loading skeletons** — just loading spinners on buttons. The React version could improve UX but should be careful not to create a different user flow that confuses operators.

9. **CSS is all legacy `.btn`, `.parse-card`, `.status-bar` classes** — the React version already uses Tailwind. The exploration must ensure the Tailwind layout matches the original visual hierarchy (compact tables, card styling, status bar, action buttons).

## Ready for Proposal

Yes. This exploration covers all legacy JS logic, all API endpoints, state shape, component architecture, and risks. Move to `sdd-propose` to formalize the approach and get validation.
