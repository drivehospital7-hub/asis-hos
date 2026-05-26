# Proposal: Style Alerts & Confirm Dialogs

## Intent

Replace 40+ native `alert()`/`confirm()` calls with styled modals matching the existing `.carga-modal-overlay` design (Tailwind v4 + oklch palette).

## Scope

### In Scope
- `Modal.confirm()`/`Modal.alert()` helper for Jinja2 legacy JS
- `<ConfirmDialog>` React component
- Replace all `alert()`/`confirm()` across 7 templates + 3 React pages
- Shared modal CSS extracted from `control_errores.css`
- Genderize `alert()` → toast

### Out of Scope
- Flash messages / toasts, Carga Masiva, image modal, login modal (all already styled)
- Backend changes

## Capabilities

### New Capabilities
None — pure UI styling, no spec-level behavior changes.

### Modified Capabilities
None — no existing capability requirements change.

## Approach

**Jinja2**: `modal.js` exposing `Modal.confirm(msg)` / `Modal.alert(msg)` returning Promises, styled like `.carga-modal-overlay`. Include from `base.html`.

**React**: `<ConfirmDialog>` wrapping `shadcn/ui Dialog` + Lucide. Ref-based imperative handle so callers `await confirmRef.show(message)`.

**Async migration**: Wrap sync conditionals in async IIFE where return value is used inline.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/static/css/legacy/control_errores.css` | Modified | Extract modal CSS to shared file |
| `app/static/css/modal.css` | **New** | Shared modal overlay styles |
| `app/static/js/modal.js` | **New** | Modal.confirm()/alert() helpers |
| `app/templates/base.html` | Modified | Include new assets |
| `app/templates/control_errores.html` | Modified | ~26 calls |
| `app/templates/abiertas_urgencias.html` | Modified | 3 calls |
| `app/templates/urgencias.html` | Modified | 4 calls |
| `app/templates/usuarios.html` | Modified | 2 calls |
| `app/templates/excel_headers.html` | Modified | 4 calls |
| `app/templates/import_facturas.html` | Modified | 2 calls |
| `app/templates/ordenado_facturado.html` | Modified | 2 calls |
| `frontend/src/components/ConfirmDialog.tsx` | **New** | React component |
| `frontend/src/pages/abiertas-urgencias/page.tsx` | Modified | 3 calls |
| `frontend/src/pages/usuarios/page.tsx` | Modified | 1 call |
| `frontend/src/pages/genderize/page.tsx` | Modified | 1 alert → toast |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Async migration breaks sync conditionals | Medium | Audit each callsite; wrap in async IIFE where needed |
| Template JS scope collision | Low | Namespace under `window.Modal` |
| React confirm pattern awkward without context | Low | Ref-based imperative handle + portal |

## Rollback Plan

Revert `modal.js` from `base.html` and `ConfirmDialog` from React pages. Native `alert()`/`confirm()` still work — no functional regression.

## Dependencies

None.

## Success Criteria

- [ ] Zero `alert()` or `confirm()` calls in production templates and React pages
- [ ] `Modal.confirm()` blocking flow matches native `confirm()` behavior
- [ ] CSS matches existing overlay language (dark backdrop, rounded corners, fade-in, oklch palette)
- [ ] React `<ConfirmDialog>` works with async/await calling patterns
- [ ] Genderize `alert()` replaced with existing toast system
