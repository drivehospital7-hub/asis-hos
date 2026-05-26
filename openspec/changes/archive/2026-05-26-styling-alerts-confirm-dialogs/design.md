# Design: Style Alerts & Confirm Dialogs

## Technical Approach

Replace 40+ native `alert()`/`confirm()` calls with styled modals. Two independent implementations mirroring the stack split:
- **Jinja2** (7 templates): `window.Modal` helper in vanilla JS, returning Promises, DOM-created overlay.
- **React** (3 pages): `<ConfirmDialog>` component wrapping Radix Dialog + Lucide, exposed via imperative ref.
- **Shared CSS**: Extract overlay tokens from `.carga-modal-overlay` into `modal.css`. Both stacks reference the same design language.

## Architecture Decisions

### Decision: Modal.js Promise API for Jinja2

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Callback-based (`confirm(msg, onYes, onNo)`) | Cleaner for sync callers, but breaks Promise chaining | ❌ |
| **Promise-based** (`Modal.confirm(msg)` returns `Promise<boolean>`) | Async in sync context needs IIFE; uniform with React pattern | ✅ |

**Rationale**: All 26 Jinja2 callsites are inside event handlers. Wrapping in `(async () => { if (!await Modal.confirm(...)) return; ... })()` is mechanical. Promise API lets us `await` across both stacks.

### Decision: Imperative Ref for React ConfirmDialog

| Option | Tradeoff | Decision |
|--------|----------|----------|
| State-driven (`open` prop + callback) | Caller must manage `open` state — awkward for `if (!confirm(...))` pattern | ❌ |
| **Imperative ref** (`ref.show(msg) → Promise<boolean>`) | Clean migration — replace `confirm(...)` with `await confirmRef.show(...)` | ✅ |

**Rationale**: Migration cost is zero — every React callsite already uses `if (!confirm(...))`. Just import the ref, call `.show()`, keep the same `if` pattern.

### Decision: Add `@radix-ui/react-dialog` Dependency

The project has `@radix-ui/react-slot` but not `@radix-ui/react-dialog`. The shadcn Dialog pattern requires it. `npm install @radix-ui/react-dialog`. No version risk — it's a stable Radix package at 1.x.

### Decision: Shared `modal.css` — Extract, Don't Duplicate

Extract overlay/animation tokens from `control_errores.css` (`.carga-modal-overlay`, `@keyframes carga-fade-in`) into `app/static/css/modal.css`. The React shell (`react_shell.html`) already loads `main.css` — add `modal.css` there too. Jinja2 `base.html` loads it globally.

### Decision: Toast Extraction for Genderize

The genderize `alert()` becomes a toast. The existing `Toast` component in `abiertas-urgencias/page.tsx` is page-local. Rather than extracting a shared component (out of scope per proposal), use `window.Modal.alert()` styled as a toast-adjacent notification (auto-dismiss, positioned).

## Data Flow

```
Modal.confirm(msg)
  → creates .modal-overlay <div> in document.body
  → appends .modal-box with message + [Cancelar] [Aceptar] buttons
  → returns Promise<boolean>
  → user clicks Aceptar → resolve(true), remove overlay
  → user clicks Cancelar / Escape → resolve(false), remove overlay

ConfirmDialog (React)
  → wrapped in <Dialog.Root> (Radix) + portal
  → ref.show(msg) → sets state, opens Dialog, returns Promise<boolean>
  → onConfirm → resolve(true)
  → onCancel / Escape → resolve(false)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/static/css/modal.css` | **Create** | Shared modal overlay tokens extracted from `control_errores.css` |
| `app/static/js/modal.js` | **Create** | `window.Modal = { confirm(msg), alert(msg) }` Promise-based helper |
| `frontend/src/components/ConfirmDialog.tsx` | **Create** | React imperative-ref dialog wrapping Radix Dialog + Lucide icons |
| `app/templates/base.html` | Modify | Add `<script src="modal.js">` + `<link href="modal.css">` before `{% block scripts %}` |
| `app/templates/react_shell.html` | Modify | Add `<link href="modal.css">` |
| `app/static/css/legacy/control_errores.css` | Modify | Remove `.carga-modal-overlay`, `.carga-modal`, `@keyframes carga-fade-in` (now in `modal.css`) |
| 7 Jinja2 templates | Modify | Replace `confirm()` → `Modal.confirm()`, `alert()` → `Modal.alert()` |
| 3 React pages | Modify | Import `ConfirmDialog`, replace `confirm()` → `ref.show()`, `alert()` → `showToast()` |
| `frontend/package.json` | Modify | Add `@radix-ui/react-dialog` dependency |

## Interfaces / Contracts

```typescript
// modal.js — Jinja2
window.Modal = {
  confirm(message: string): Promise<boolean>,
  alert(message: string): Promise<void>,  // resolves on dismiss
}

// ConfirmDialog.tsx — React
interface ConfirmDialogHandle {
  show(message: string): Promise<boolean>;
}
interface ConfirmDialogProps {
  title?: string;  // default: "Confirmar"
  onConfirm?: () => void;
  onCancel?: () => void;
}
```

## Async Migration Pattern

Each sync callsite follows one of two patterns:

**Pattern A — early return** (most cases):
```javascript
// Before
if (!confirm('¿Eliminar?')) return;

// After
(async () => {
  if (!await Modal.confirm('¿Eliminar?')) return;
  // ... rest of handler
})();
```

**Pattern B — conditional branch**:
```javascript
// Before
if (dup.length && !confirm('...')) { closeEditor(); return; }

// After
(async () => {
  if (dup.length && !await Modal.confirm('...')) { closeEditor(); return; }
})();
```

For React, the migration is simpler because handlers are already `async`:
```typescript
// Before
if (!confirm("¿Eliminar?")) return;

// After
if (!await confirmRef.show("¿Eliminar?")) return;
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| JS DOM unit | `Modal.confirm()` creates overlay, resolves true/false on button click, Escape dismisses | Vitest + jsdom in `frontend/` or plain test in Flask test suite |
| JS DOM unit | `Modal.alert()` shows single "Aceptar" button, resolves on click | Same |
| React unit | `<ConfirmDialog>` renders via ref.show(), resolves promise on confirm/cancel | Vitest + @testing-library/react |
| Integration | React pages still function after migration | Manual smoke test each page |
| CSS visual | Overlay matches existing `.carga-modal-overlay` design (dark backdrop, 16px radius, fade-in) | Visual inspection |

No backend test changes — this is purely frontend UI.

## Migration / Rollout

No migration required. Changes are additive:
1. Create `modal.css`, `modal.js`, `ConfirmDialog.tsx` (safe — no existing references to break)
2. Install `@radix-ui/react-dialog`
3. Add includes to `base.html` and `react_shell.html`
4. Migrate Jinja2 templates one-by-one (control_errores.html is the largest — 26 calls)
5. Migrate React pages (3 pages, 5 calls total)
6. Remove extracted CSS from `control_errores.css`
7. Verify no `alert()` or `confirm()` remains via grep

Rollback: revert includes and re-add native calls. No functional regression risk.

## Open Questions

- [ ] Genderize `alert()` → toast: should we extract a shared Toast component, or use `Modal.alert()` styled as toast? Proposal says "Genderize alert() → toast notification (already exists)" but the toast is page-local.
