# Design: Perfiles de Usuarios — Plantillas

## Technical Approach

Additive migration: `instance/templates.json` alongside users.json. DEFAULT_USERS untouched (preserve real accounts + sessions). Three new parts: templates store (mirrors users_store.py patterns), API endpoint for templates, and UI dropdowns that pre-fill permission checkboxes.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|----------|---------|-----------|--------|
| Store pattern | (a) Module-level fns (match users_store) (b) TemplateStore class | (a) Consistent with existing code, simpler mocking via `patch(templates_store, "list_templates")` (b) Encapsulation but diverges from project convention | **(a)** — match existing pattern, no reason to diverge |
| templates.json location | (a) `instance/templates.json` (b) Same file with `type` field | (a) Complete schema separation, no migration of users.json, cleaner CRUD (b) One file but mixed schemas, harder to reason about | **(a)** — schema is fundamentally different (no password), separation avoids "is this a user or template?" confusion |
| Template-to-user link | (a) Copy permisos at creation time (b) Store template FK reference | (a) Snapshot — editing template doesn't retroactively change users (b) Live link — harder, needs explicit "apply template update" UX | **(a)** — simpler, proposal-specified "pre-rellena checkboxes (editables)", no inheritance |
| CRUD endpoints | (a) Full REST (b) Minimal: GET /api/templates only | (a) Needed for future template management UI (b) Less code now but incomplete | **(a)** — but implement full CRUD in store layer now, expose only GET in API layer. POST/PUT/DELETE endpoints deferred until UI exists but store is ready. |
| Concurrency | (a) No lock (same as users.json) (b) File lock | (a) Same risk profile as existing code (b) Overengineering — single-admin scenario, writes are atomic (temp + replace) | **(a)** — match existing pattern; atomic write via `os.replace()` is sufficient |

## Data Flow

```
React/Jinja2 UI
    │
    ├── GET /auth/api/templates ──→ templates_store.list_templates() ──→ instance/templates.json
    │
    └── User selects template ──→ permisos copied to form state ──→ POST /auth/usuarios/crear (unchanged)
                                                                        │
                                                                        └── users_store.create_user() ──→ instance/users.json
```

First run flow (no templates.json exists):
```
templates_store._load_templates()
    → file missing → _ensure_default_templates()
        → write DEFAULT_TEMPLATES to instance/templates.json
        → return list
```

## Data Structures

### `instance/templates.json` schema

```python
# Each entry (list of dicts):
{
    "nombre": "Odontología",              # str, unique key
    "descripcion": "Solo /odontologia",   # str
    "permisos": ["odontologia"],          # list[str], subset of ALLOWED_PERMISOS
}
```

### `app/constants/base.py` addition

```python
DEFAULT_TEMPLATES = [
    {
        "nombre": "Odontología",
        "descripcion": "Solo módulo de odontología",
        "permisos": ["odontologia"],
    },
    {
        "nombre": "Urgencias",
        "descripcion": "Urgencias + control + facturas abiertas (solo lectura)",
        "permisos": ["urgencias", "control_urgencias", "facturas_abiertas"],
    },
    {
        "nombre": "Auditor",
        "descripcion": "Control urgencias + facturas abiertas + equipos básicos (con modificación)",
        "permisos": [
            "control_urgencias",
            "control_urgencias:write",
            "facturas_abiertas",
            "facturas_abiertas:write",
            "equipos_basicos",
        ],
    },
]
```

## Interfaces / Contracts

### `app/utils/templates_store.py` — API surface (matches users_store.py module-level pattern)

```python
TEMPLATES_FILE: Path = Path("instance") / "templates.json"

def list_templates() -> list[dict]:
    """Returns all templates (copy of each, no internal state leak)."""

def get_template(nombre: str) -> dict | None:
    """Returns template dict or None if not found."""

def create_template(nombre: str, descripcion: str, permisos: list) -> tuple[bool, str]:
    """Creates template. Returns (True, msg) or (False, msg) if duplicate."""

def update_template(nombre: str, updates: dict) -> tuple[bool, str]:
    """Partial update. `updates` can have descripcion and/or permisos keys."""

def delete_template(nombre: str) -> tuple[bool, str]:
    """Deletes template. Returns (False, msg) if name is a protected default."""

# Internal (same pattern as users_store)
def _load_templates() -> list[dict]: ...
def _save_templates(templates: list[dict]) -> None: ...   # atomic write
def _ensure_default_templates() -> None: ...               # called by _load_templates if file missing
```

### `app/routes/auth.py` — new endpoint

```python
@auth_bp.route("/api/templates")
@admin_requerido
def api_list_templates():
    """Returns JSON list of all templates (React + Jinja2 both consume this)."""
    templates = templates_store.list_templates()
    return jsonify({
        "status": "success",
        "data": {"templates": templates},
        "errors": [],
    })
```

### React state additions (`page.tsx`)

```typescript
interface Template {
  nombre: string;
  descripcion: string;
  permisos: string[];
}

// New state
const [templates, setTemplates] = useState<Template[]>([]);
const [selectedTemplate, setSelectedTemplate] = useState<string>("");

// On mount: fetch /auth/api/templates → setTemplates
// On dropdown change: find template by nombre → setFormPermisos(template.permisos)
// Dropdown rendered above checkboxes, hidden when formRol === "admin"
// Dropdown followed by "Pre-ferenced from template" helper text when selected
```

### Jinja2 JS addition (`usuarios.html`)

```javascript
// On DOMContentLoaded: fetch /auth/api/templates → populate <select id="template-select">
// On template-select change: check/uncheck checkboxes matching template.permisos
// Dropdown hidden when rol === "admin" (same togglePermisos pattern)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/utils/templates_store.py` | Create | Template CRUD, atomic save, default seeding |
| `app/constants/base.py` | Modify | Add `DEFAULT_TEMPLATES` constant |
| `app/routes/auth.py` | Modify | Add `GET /auth/api/templates` endpoint |
| `app/utils/users_store.py` | Modify | None required (DEFAULT_USERS untouched) |
| `frontend/src/pages/usuarios/page.tsx` | Modify | Add dropdown + pre-fill logic + fetch on mount |
| `app/templates/usuarios.html` | Modify | Add dropdown + JS pre-fill (fetch + checkbox toggle) |
| `instance/templates.json` | Create | Auto-generated on first load by `_ensure_default_templates()` |
| `tests/utils/test_templates_store.py` | Create | Unit tests for all template CRUD operations |

## Migration / Rollout

**First-run behavior**: `_load_templates()` checks `instance/templates.json`. If missing, calls `_ensure_default_templates()` which writes DEFAULT_TEMPLATES. `_load_users()` unchanged — all 4 default users still created as real accounts. Users log in with same credentials. Sessions untouched.

**Existing deployments**: No migration needed. `instance/templates.json` doesn't exist → gets created with defaults on first access. `instance/users.json` stays intact.

**Rollback per commit**:

1. Revert `app/templates/usuarios.html` → Jinja2 dropdown removed
2. Revert `frontend/src/pages/usuarios/page.tsx` → React dropdown removed
3. Revert `app/routes/auth.py` → `/api/templates` endpoint removed
4. Delete `app/utils/templates_store.py` + `instance/templates.json` (if exists) → feature fully removed
5. Users.json untouched throughout — zero data loss at each step

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit — store | `list_templates`, `get_template`, `create_template`, `update_template`, `delete_template`, `_ensure_default_templates` | Patch `TEMPLATES_FILE` with temp dir. Same pattern as `test_users_store.py` — mock `_save_templates` for mutation tests, real temp file for default seeding. |
| Unit — migration | Default templates created on first `_load_templates()` call | Create temp dir, confirm file does NOT exist, call `_load_templates()`, assert 3 templates returned and file now exists |
| Integration — API | `GET /auth/api/templates` returns 200 with 3 templates | Flask test client with app fixture |
| Integration — UI pre-fill | React: dropdown + checkbox state | Not automated (Vite-only, no test runner). Manual: create user dropdown select → checkboxes checked. |
| Integration — Jinja2 pre-fill | JS fetch + checkbox toggle | Manual: legacy usuarios page, same flow |
| Regression | Creating a user with template pre-fill works | Existing `test_users_store.test_create_user_success` still passes — permissions from template are just a list, same as manual checkbox selection |

## Open Questions

- [ ] Should `delete_template()` protect default templates (odontologia, urgencias, auditor) from deletion? Proposal doesn't mention, but accidentally deleting a default template could confuse admins.
