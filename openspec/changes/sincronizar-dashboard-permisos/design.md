# Design: Sincronizar Dashboard con Permisos

## Technical Approach

Additive refactor — no data migration, no new dependencies. Extract the hardcoded area list from `home.py` into a centralized `DASHBOARD_AREAS` constant in `app/constants/base.py`, then filter by `session["permisos"]` before passing to the React shell. Add the missing `@permiso_requerido("derechos")` guard to match the established pattern in `urgencias.py` / `odontologia.py`. Remove the frontend fallback so areas come exclusively from the backend.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Location of DASHBOARD_AREAS | (a) `app/constants/base.py` (b) new `app/constants/areas.py` | (a) Follows existing pattern — ALLOWED_PERMISOS, DEFAULT_TEMPLATES in the same file — one import path (b) Cleaner separation but adds a module | **(a)** — `base.py` is already the canonical file for shared constants |
| Filter logic location | (a) Backend `home.py` (b) Frontend `page.tsx` | (a) Single source of truth, no area data leaks to unauthorized users, consistent with sidebar server-render (b) Simpler but exposes all areas in HTML | **(a)** — security + consistency. Areas in `initial_data` are already server-controlled |
| Structure of area entries | (a) Flat dict with all fields incl. description (b) Two-tier: metadata in DASHBOARD_AREAS, dynamic data merged at render | (a) Simple, one structure, `_filter_areas` returns usable items directly (b) More flexible for future dynamic pending counts | **(a)** — `description` is static content, `pending` stays 0 (removes hardcoded fake counts) |
| Route guard on derechos | (a) `@permiso_requerido("derechos")` between route and view (b) Inline `if` check inside view | (a) Matches existing pattern in urgencias.py — declarative, testable, reusable (b) Adds branch noise to view function | **(a)** — exactly the same pattern. `from app.utils.auth import permiso_requerido` already imported? No, derechos.py doesn't import it |

## Data Flow

```
Login → session["permisos"] → home_react()
                                  │
                                  ├── _filter_areas(permisos)
                                  │       ├── "*" in permisos → DASHBOARD_AREAS (full)
                                  │       └── filter by a["permiso"] in permisos
                                  │       └── merge pending_counts
                                  │
                                  └── initial_data["areas"] → React IndexPage
                                                                            │
                                                                            └── initialData.areas ?? []

/derechos → @permiso_requerido("derechos") → derechos_react()
                │
                ├── permisos has "derechos" or "*" → OK
                └── denied → redirect to /dashboard (403 for JSON)
```

## Data Structures

### `DASHBOARD_AREAS` in `app/constants/base.py`

```python
DASHBOARD_AREAS = [
    {
        "title": "Urgencias", "slug": "urgencias",
        "permiso": "urgencias", "href": "/urgencias",
        "tone": "danger", "pending_label": "errores",
        "description": "Procesamiento y validación de facturas del servicio de urgencias.",
    },
    # ... 5 more entries as per proposal
]
```

Each entry: `title: str`, `slug: str`, `permiso: str`, `href: str`, `tone: str`, `pending_label: str`, `description: str`.

### Filter function in `home.py`

```python
def _filter_areas(permisos: list[str]) -> list[dict]:
    """Filter DASHBOARD_AREAS by user permissions."""
    if "*" in permisos:
        areas = list(DASHBOARD_AREAS)
    else:
        areas = [a for a in DASHBOARD_AREAS if a["permiso"] in permisos]
    return [{**a, "pending": 0} for a in areas]  # add pending count
```

## Interfaces / Contracts

### `home.py` — `_filter_areas` signature

```
Input:  permisos: list[str] (from session)
Output: list[dict] with keys: title, slug, permiso, href, tone, pending_label, description, pending (int)
```

### `derechos.py` — decorator placement

```python
@derechos_bp.get("/derechos")
@permiso_requerido("derechos")
def derechos_react():
    ...
```

### Frontend `IndexArea` type (unchanged — already has all fields)

```typescript
interface IndexArea {
  title: string; description: string; href: string;
  pending: number; pending_label: string;
  tone: "danger" | "warning" | "success" | "info" | "neutral";
}
```

### `initial_data` shape (unchanged — `areas` already present)

```typescript
interface IndexData {
  can_write: boolean; username: string;
  kpis: IndexKpi[]; areas: IndexArea[];
}
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/constants/base.py` | Modify | Add `DASHBOARD_AREAS` list with 6 area entries |
| `app/routes/home.py` | Modify | Replace hardcoded `areas` with `_filter_areas(session["permisos"])` |
| `app/routes/derechos.py` | Modify | Add `@permiso_requerido("derechos")` and import |
| `frontend/src/pages/index/page.tsx` | Modify | Replace `initialData?.areas ?? [...]` with `initialData?.areas ?? []` |
| `tests/services/test_react_frontend.py` | Modify | Add tests: dashboard filters by permisos, derechos rejects without permiso |

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit — filter | `_filter_areas` with `["odontologia"]` returns 1 area, with `["*"]` returns 6, with `[]` returns 0 | Patch `DASHBOARD_AREAS` or use app context; test function directly |
| Integration — dashboard | Admin sees all 6 areas, user with only `odontologia` sees 1 area | Flask test client; login with different users; assert area count in HTML |
| Integration — rights | User without `derechos` gets 403 on `/derechos` | Login as `test_user` (no `derechos`), GET `/derechos`, assert 403 |
| Unit — frontend | `areas` fallback is `[]` when `initialData` is undefined | Already trivially safe — `initialData?.areas ?? []` |

## Migration / Rollout

**No data migration required.** Pure view-layer refactor:

1. Commit 1: `base.py` — add `DASHBOARD_AREAS` (backward compatible, nothing consumes it yet)
2. Commit 2: `home.py` — use `_filter_areas` (dashboard now filtered)
3. Commit 3: `derechos.py` — add route guard (new behavior)
4. Commit 4: `page.tsx` — remove frontend fallback
5. Commit 5: tests

**Rollback**: revert commits in reverse order. Each commit is independently revertible.

## Open Questions

- [x] `description` was not in proposal's DASHBOARD_AREAS — added here because the frontend `IndexArea` interface requires it. Without it the React type errors.
- [x] `pending` count set to `0` for all areas — removes hardcoded fake counts (31, 9, 0) from current code. Future work should make pending counts dynamic.
- [ ] Does `odontologia.py` / `equipos_basicos.py` already have `@permiso_requerido`? Confirm during apply — if missing, they should get guards too but that's out of scope per proposal.
