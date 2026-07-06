# Design: Monitoreo de Carpetas — Config UI

## Technical Approach

**Store** (`app/utils/monitoreo_store.py`): Three-function JSON store — `get_roots()`, `save_roots()`, `reset_roots()`. Atomic writes via `tempfile.mkstemp` + `Path.replace()` (same pattern as `errores_storage.py`). Priority: JSON file > env var > empty list.

**Backend** (blueprint `app/routes/monitoreo_carpetas.py`): 3 new config endpoints on the existing blueprint — `GET /config`, `PUT /config` (requires `monitoreo_carpetas:write`), `POST /config/reset` (requires `:write`). Modify `POST /scan` to call `monitoreo_store.get_roots()` instead of `os.environ.get()` directly.

**Frontend** (`page.tsx`): Config card shown only when `can_write` prop is true. Dynamic input array with add/remove rows. Two action buttons: "Guardar" (PUT) and "Restaurar default" (POST reset). Read-only display when `can_write` is false.

**Permissions**: Add `monitoreo_carpetas` and `monitoreo_carpetas:write` to `ALLOWED_PERMISOS`, `PERMISO_MUTUAL_EXCLUSION`, `ALL_PERMISOS`, `DASHBOARD_AREAS`. Sidebar nav item with `permiso: "monitoreo_carpetas"`.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| Persistence backend | JSON file | SQLite, env var only | JSON matches errores_storage pattern; no schema/migrations; store << 1KB |
| Write strategy | Atomic tempfile+replace | Direct write, ORM | Same proven pattern used in errores_storage — no corruption on power loss |
| GET /config auth | No permission check | Require `:write` | Roots are non-sensitive paths; read access is already gated by module-level `monitoreo_carpetas` nav/sidebar visibility |
| Frontend data flow | `can_write` prop from `main.tsx` | Separate `/auth/check` endpoint | Follows established pattern from `abiertas-urgencias` — `initial_data` already carries `can_write` |
| PUT validation | Basic list-of-strings check | Reachability/UNC validation | Out of scope per proposal; scan already tolerates invalid paths gracefully |

## Data Flow

```
┌──────────┐    GET /monitoreo-carpetas/config
│  Browser │◄───────────────────────────────────────┐
│  page.tsx│                                       │
│          │    PUT /monitoreo-carpetas/config      │
│  Config  │───────────────────────────────────────►│
│  Card    │    POST /monitoreo-carpetas/config/reset│
│          │───────────────────────────────────────►│
└──────────┘                                       │
                                                   ▼
                              ┌──────────────────────────┐
                              │  monitoreo_carpetas_bp   │
                              │                          │
                              │  GET /config ──►monitoreo│
                              │  PUT /config ──►_store   │
                              │  POST /reset ──►         │
                              │  POST /scan ──► now calls│
                              │      get_roots() instead │
                              │      of os.environ       │
                              └──────────┬───────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ app/data/            │
                              │ monitoreo_carpetas_  │
                              │ config.json          │
                              └──────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/utils/monitoreo_store.py` | Create | `get_roots()`, `save_roots()`, `reset_roots()` with atomic write |
| `app/constants/base.py` | Modify | Add `monitoreo_carpetas`, `monitoreo_carpetas:write` to `ALLOWED_PERMISOS`, `PERMISO_MUTUAL_EXCLUSION`, `DASHBOARD_AREAS` |
| `app/constants/monitoreo_carpetas.py` | Modify | Add `MONITOREO_CONFIG_FILE` constant |
| `app/routes/monitoreo_carpetas.py` | Modify | +3 config endpoints; modify `POST /scan` to use `monitoreo_store.get_roots()` |
| `app/constants/__init__.py` | Modify | Export `MONITOREO_CONFIG_FILE` from monitoreo_carpetas package |
| `frontend/src/pages/monitoreo-carpetas/main.tsx` | Modify | Pass `can_write` prop to page component |
| `frontend/src/pages/monitoreo-carpetas/page.tsx` | Modify | Add config card with inputs, Guardar, Restaurar default |
| `frontend/src/components/app-sidebar.tsx` | Modify | Add "Monitoreo de Carpetas" nav item |
| `frontend/src/pages/usuarios/page.tsx` | Modify | Add `monitoreo_carpetas` entries to `ALL_PERMISOS` and `PERMISO_PAIRS` |
| `app/data/monitoreo_carpetas_config.json` | Create | Created on first `save_roots()` call |

## Interfaces / Contracts

### Python (monitoreo_store.py)

```python
def get_roots() -> list[str]:
    """Priority: JSON file → env var MONITOREO_CARPETAS_ROOTS → [].

    Env var supports JSON array or semicolon-separated (same as POST /scan)."""

def save_roots(roots: list[str]) -> None:
    """Validate roots is non-empty list of strings. Atomic write."""

def reset_roots() -> None:
    """Delete JSON file. Silent if doesn't exist."""
```

### API Contract

```json
// GET /monitoreo-carpetas/config → 200
{"status": "success", "data": {"roots": ["\\\\srv\\path1"], "fuente": "manual", "ultima_actualizacion": "2026-07-04T12:00:00"}, "errors": []}

// PUT /monitoreo-carpetas/config  → body: {"roots": ["\\\\srv\\path1"]}
// 200 success, 403 no :write, 422 validation
{"status": "success", "data": {"roots": [...], "fuente": "manual", ...}, "errors": []}

// POST /monitoreo-carpetas/config/reset → 200
{"status": "success", "data": {"roots": ["\\\\env\\path"], "fuente": "env", "ultima_actualizacion": null}, "errors": []}

// Error (422)
{"status": "error", "data": {}, "errors": ["roots debe ser una lista no vacía de strings"]}
```

### JSON Store Shape

```json
{"roots": ["\\\\server\\path1"], "fuente": "env|manual", "ultima_actualizacion": "2026-07-04T12:00:00"}
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | `monitoreo_store.py` — read/write/reset/fallback/atomicity | `tmp_path` fixture; test file created/deleted; test corrupt JSON recovery |
| Unit | `POST /scan` uses store when JSON exists | Mock `monitoreo_store.get_roots()` return value |
| Integration | Config endpoints — success/403/422 paths | Flask test client with session permisos |
| E2E | Config card shows/hides with `can_write` | Playwright — assert input field visibility |

## Migration / Rollout

No migration required. The JSON file is created on first save. Existing env-var-only deployments continue working — `get_roots()` falls back to env var when no JSON file exists.

## Open Questions

None.
