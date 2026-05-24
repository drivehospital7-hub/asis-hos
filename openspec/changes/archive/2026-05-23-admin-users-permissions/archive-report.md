# Archive Report: admin-users-permissions

**Change**: Admin — Usuarios y Permisos
**Archived**: 2026-05-23
**Verdict**: PASS WITH WARNINGS

---

## Summary

Completed the CRUD of the authentication user store: added `update_user()` with atomic write, added edit/delete endpoints for users, created inline edit modal, fixed duplicate checkbox bug, added admin-link to home, refactored legacy `auth.js` to event-driven, and added 40 new tests (22 unit + 18 integration). All 304 tests pass with zero regression.

### Files Changed (Implementation)

| File | Action | Change |
|------|--------|--------|
| `app/utils/users_store.py` | **MODIFIED** | Added `update_user()`, atomic write (`_save_users()` via tmp + `os.replace()`), admin protection in `delete_user()` |
| `app/routes/auth.py` | **MODIFIED** | Added `POST /auth/usuarios/<username>/editar` and `POST /auth/usuarios/<username>/eliminar` |
| `app/templates/usuarios.html` | **MODIFIED** | Inline edit modal, delete buttons, checkbox fix (`cruce_facturas` vs `equipos_basicos`), self-edit guard |
| `app/templates/home.html` | **MODIFIED** | Conditional admin link to `/auth/usuarios` when `'*' in permisos` |
| `app/static/js/auth.js` | **REFACTORED** | Event-driven via `ce-auth-change`, removed localStorage `admin_authenticated` |
| `app/constants/base.py` | **MODIFIED** | Added `ALLOWED_PERMISOS` as `frozenset` |
| `tests/utils/test_users_store.py` | **NEW** | 22 unit tests for `update_user()`, `delete_user()`, atomic write, edge cases |
| `tests/services/test_auth_routes.py` | **NEW** | 18 integration tests for login, CRUD, admin protection, auth guards |

**Lines added**: ~500 | **Lines removed**: ~65 | **Net**: ~+435

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Modal via data-attributes** (no extra endpoint) | Data serialized in Jinja2 `tojson` on `<tr>` — no roundtrip, simpler |
| **3-layer self-protection**: Route (session check) + Store (block any `*` removal) + Frontend (JS confirm) | Defense in depth for admin self-desactivation |
| **POST for delete** (not HTTP DELETE) | HTML forms don't support DELETE; POST works universally |
| **Password optional** in edit | Empty password field → skip hash update; no forced password reset |
| **Atomic write**: tmp file + `os.replace()` | Prevents JSON corruption on crash |
| **NO SQLAlchemy / Flask-Login migration** | JSON store works for ~1-2 admins; DB migration requires separate SDD |
| **`auth.js` refactored to event-driven** | Removes dependency on conflicting localStorage key; uses `ce-auth-change` from `base.html` |

---

## Test Results

**Full suite**: 304 passed, 0 failed, 0 errors, 0 skipped in 37.30s

### Auth-specific tests: 40/40 ✅

| Test File | Tests | Result |
|-----------|-------|--------|
| `tests/utils/test_users_store.py` | 22 | ✅ All pass |
| `tests/services/test_auth_routes.py` | 18 | ✅ All pass |

### Regression: 264/264 ✅

All existing tests pass — zero regression.

---

## Delta Spec Update Notes

The spec at `openspec/specs/admin-users-permissions/spec.md` is the **source of truth** (no delta spec existed — the spec was written directly to main specs). Two documentation mismatches identified in verification remain in the spec:

### W1: Event Contract Mismatch (R8 — `auth.js`)

- **Spec says**: `e.detail.authenticated` (lines 299-321)
- **Actual `base.html` fires**: `e.detail.auth`
- **Implementation**: Correctly reads `e.detail.auth` matching actual codebase
- **Action**: Spec lines 299-321 should change `authenticated` to `auth` in the event contract pseudo-code

### W2: Self-`*` Removal Validation Rules (R1)

- **Spec says**: Store-level check uses `session["username"] == username`
- **Actual**: Store blocks `*` removal from **any** user (not just self). Route adds the session-scoped check.
- **Implementation**: Stricter (defense in depth) — matches design decision that store is pure persistence without session awareness
- **Action**: Spec validation rules table should reflect the actual 2-layer design: (1) Store: block any `*` removal; (2) Route: block self-session `*` removal

### S1: Missing Logout Integration Test

- Logout route has no explicit integration test — minor gap, no functional impact

---

## Known Issues / Warnings

- ⚠️ **Spec documentation mismatches** (W1, W2 above) — no functional impact, only doc inaccuracies
- ⚠️ `auth.js` no longer reads `localStorage('admin_authenticated')` — cross-tab sync via `storage` event is removed. This is intentional; the modern event model handles in-page updates
- ℹ️ **Concurrency**: JSON store (last-writer-wins) is accepted for ~1-2 concurrent admins

---

## Archived Artifacts

| Artifact | Status |
|----------|--------|
| `exploration.md` | ✅ Archived |
| `proposal.md` | ✅ Archived |
| `spec.md` | ℹ️ Already at main spec path — NOT moved (source of truth) |
| `design.md` | ✅ Archived |
| `tasks.md` | ✅ Archived (7/7 tasks [x]) |
| `verify-report.md` | ✅ Archived |

## Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `admin-users-permissions` | Already at main path | No delta spec to merge. Main spec at `openspec/specs/admin-users-permissions/spec.md` is the source of truth. |

## SDD Cycle Complete

All phases: Exploration → Proposal → Spec → Design → Tasks → Apply → Verify → **Archive** ✅
