# Tasks: Style Alerts & Confirm Dialogs

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~250–300 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | ask-on-risk |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

**Rationale**: 16 confirm + 27 alert callsites across 7 Jinja2 + 3 React files. Most containing functions are already `async`, making 2/3 of confirm migrations a simple `await` addition. Alert calls are 1:1 `Modal.alert()` replacement. Only 5 sync functions need `async` keyword added (no IIFEs needed). New files: modal.css (~40), modal.js (~70), ConfirmDialog.tsx (~55). CSS extraction avoids modifying `control_errores.css` — keeps Carga Masiva out-of-scope.

---

## Phase 1: Infrastructure — Shared Assets

- [x] 1.1 Create `app/static/css/modal.css` — overlay/animation tokens for confirm/alert (`.confirm-overlay`, `.confirm-modal`, `@keyframes confirm-fade-in`) matching `.carga-modal-overlay` design language
- [x] 1.2 Create `app/static/js/modal.js` — `window.Modal = { confirm(msg): Promise<boolean>, alert(msg): Promise<void> }` with DOM overlay creation, Escape/click-outside dismiss, Promise resolution on button click
- [x] 1.3 Create `frontend/src/components/ConfirmDialog.tsx` — imperative ref component wrapping Radix `Dialog.Root` + Lucide icons + portal; `ref.show(msg): Promise<boolean>`
- [x] 1.4 Install `@radix-ui/react-dialog` in `frontend/package.json`

## Phase 2: Wiring — Include Assets in Templates

- [x] 2.1 Add `<link href="modal.css">` + `<script src="modal.js">` to `app/templates/base.html` before `{% block scripts %}`
- [x] 2.2 Add `<link href="modal.css">` to `app/templates/react_shell.html`
- [x] 2.3 Add `ConfirmDialog` component to React app shell (import + mount as child of `<div id="root">` or top-level layout); expose `window.__showConfirm(msg)` for all React pages

## Phase 3: Jinja2 Migration — control_errores.html (largest, 26 callsites)

- [x] 3.1 Make `saveFromEditor()` and `saveFromEditorWithCallback()` async; replace their 4 `confirm()` → `await Modal.confirm()`
- [x] 3.2 `deleteError()` + `deleteImage()` are already async — add `await` to their 2 `confirm()` calls; replace their 2 `alert()` → `Modal.alert()`
- [x] 3.3 `saveNewRow()` is already async — add `await` to its `confirm()` call; replace remaining alert/confirm calls in `deleteCargaImage()` + `parseCargaMasiva()` (make both async, 3 confirm + 9 alert → Modal.alert)
- [x] 3.4 Replace remaining alert() calls (lines ~1211, ~1354, ~1367, ~1767, ~1872–1891, ~1917, ~2040, ~2101) with `Modal.alert()`

## Phase 4: Jinja2 Migration — Remaining 6 Templates

- [x] 4.1 `abiertas_urgencias.html` — 3 confirm calls already in async functions; add `await` to each
- [x] 4.2 `urgencias.html` — replace 4 `alert()` → `Modal.alert()`
- [x] 4.3 `usuarios.html` — add `async` to 2 event handlers, replace `confirm()` → `await Modal.confirm()`
- [x] 4.4 `excel_headers.html` — replace 4 `alert()` → `Modal.alert()`
- [x] 4.5 `import_facturas.html` — replace 2 `alert()` → `Modal.alert()`
- [x] 4.6 `ordenado_facturado.html` — replace 2 `alert()` → `Modal.alert()`

## Phase 5: React Migration — 3 Pages

- [x] 5.1 `abiertas-urgencias/page.tsx` — replace 3 `confirm()` → `await window.__showConfirm()`
- [x] 5.2 `usuarios/page.tsx` — replace 1 `confirm()` → `await window.__showConfirm()`
- [x] 5.3 `genderize/page.tsx` — replace `alert()` with `Modal.alert()` (global helper via modal.js loaded in react_shell.html)

## Phase 6: Verify

- [x] 6.1 Zero legacy `confirm()` in app/templates and frontend/src — VERIFIED
- [x] 6.2 Zero legacy `alert()` in app/templates and frontend/src (excluding Modal.alert) — VERIFIED
- [ ] 6.3 Smoke test (manual — browser-based, cannot automate)
- [x] 6.4 Run `pytest -v` — 483 passed, 1 pre-existing failure (unrelated count check)
